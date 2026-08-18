"""Alert worker: fan out a scanner hit to every Telegram subscriber, rate-limited.

Enqueued by the scanner (``app/scanner/worker.py``) after each ``ScanHit`` insert.
Loads the hit and its rule/instrument, finds every ``AlertSubscription`` on that
rule with ``channel="telegram"``, and sends a formatted message per subscriber.
Sends are per-user fixed-window rate-limited; a user over their limit is skipped
(never crashes the job). If no bot token is configured the job is a no-op.
"""

from __future__ import annotations

import logging
from typing import Any

from arq import Retry
from sqlalchemy import select

from app.alerts.telegram import format_hit_message, send_telegram_message
from app.core.config import get_settings
from app.core.deps import get_sessionmaker
from app.core.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.models.alert_subscription import AlertSubscription
from app.models.instrument import Instrument
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule

logger = logging.getLogger(__name__)

# A per-(hit, subscriber) delivery marker so an arq retry of the whole job does
# not re-send to subscribers already delivered. Set only AFTER a confirmed ok
# send, so a failed send leaves no marker and the retry can try again.
_DELIVERY_MARK_TTL_SECONDS = 60 * 60 * 24


async def send_telegram_alert_job(ctx: dict[str, Any], hit_id: int) -> int:
    """Send a Telegram alert to every subscriber of the hit's rule.

    Returns the number of messages actually sent (skipping rate-limited users).
    """
    settings = get_settings()
    if not settings.telegram_bot_token:
        return 0

    session_factory = ctx.get("session_factory") or get_sessionmaker()
    redis = ctx["redis"]

    async with session_factory() as session:
        hit = await session.get(ScanHit, hit_id)
        if hit is None:
            return 0

        rule = await session.get(ScanRule, hit.rule_id)
        instrument = await session.get(Instrument, hit.instrument_id)
        if rule is None or instrument is None:
            return 0
        # Re-check enabled at send time: the user may have disabled the rule
        # between the hit insert and this (possibly retried/delayed) job.
        if not rule.enabled:
            return 0

        subs = (
            (
                await session.execute(
                    select(AlertSubscription).where(
                        AlertSubscription.rule_id == hit.rule_id,
                        AlertSubscription.channel == "telegram",
                    )
                )
            )
            .scalars()
            .all()
        )
        if not subs:
            return 0

        text = format_hit_message(
            {
                "symbol": instrument.symbol,
                "rule_name": rule.name,
                "ts": hit.ts,
                "payload": hit.payload,
            }
        )

    sent = 0
    had_failure = False
    for sub in subs:
        # Skip a subscriber already delivered in a prior run of this job.
        delivery_key = f"alert_sent:{hit_id}:{sub.id}"
        if await redis.exists(delivery_key):
            continue
        try:
            await enforce_rate_limit(
                redis,
                key=f"telegram_alert:{sub.user_id}",
                limit=settings.telegram_rate_limit_per_min,
                window_seconds=60,
            )
        except RateLimitExceeded:
            continue
        # Per-subscriber isolation: one send raising must not abort the fan-out.
        try:
            result = await send_telegram_message(
                settings.telegram_bot_token, sub.target, text
            )
        except Exception:
            logger.warning(
                "telegram send raised for sub %s (hit %s); continuing", sub.id, hit_id,
                exc_info=True,
            )
            had_failure = True
            continue
        if not result.ok:
            logger.warning(
                "telegram send not ok for sub %s (hit %s): %s %s",
                sub.id, hit_id, result.status_code, result.description,
            )
            had_failure = True
            continue
        # Mark delivered only after a confirmed ok send.
        await redis.set(delivery_key, "1", ex=_DELIVERY_MARK_TTL_SECONDS)
        sent += 1

    # T1-7: if any send failed, ask arq to retry the whole job. Delivered
    # subscribers are guarded by their per-(hit, sub) delivery marker, so a
    # retry re-attempts only the ones that did not go through.
    if had_failure:
        raise Retry()

    return sent
