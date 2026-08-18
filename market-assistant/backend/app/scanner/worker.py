"""Rule engine worker: on candle close, evaluate enabled rules and fan out hits.

For each closed candle the worker warm-starts a fresh indicator cache from the
instrument's recent history (read via the SAME session as ``ctx["db"]`` so it
sees seeded/committed rows), computes an indicator snapshot including the new
bar, then evaluates every enabled ``ScanRule``. Rules that fire persist a
``ScanHit`` row and publish a JSON event to ``scan_hits:{user_id}`` for the
websocket fan-out. Dedup is authoritative via the DB
UNIQUE(rule_id, instrument_id, ts); a Redis SET-NX key is a best-effort
fast path claimed only after a durable commit.

Indicators are keyed by period-suffixed names ("rsi:14", "vwap") end to end:
the cache emits them, the evaluator looks them up via ``Condition.key``, and
the worker requests each rule's keys per timeframe — so a custom period is
honored and cross-tf legs resolve.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.ingest.nse_calendar import is_in_session
from app.models.instrument import Instrument
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule
from app.scanner.cache import WARM_START_BARS, CandleLike, IndicatorCache, LoadHistory
from app.scanner.dedup import claim_hit, hit_already_claimed
from app.scanner.dsl import parse_rule_definition
from app.scanner.evaluator import compile_rule
from app.scanner.history import load_recent_candles

# Period-suffixed keys the cache's recompute parser expects (it splits on ":"
# and int()-casts the period, so bare names would IndexError).
REQUESTED: list[str] = [
    "rsi:14",
    "ema:21",
    "sma:20",
    "vwap",
    "atr:14",
    "adx:14",
    "rel_volume:20",
    "gap_pct",
    "bollinger_mid:20:2.0",
    "bollinger_upper:20:2.0",
    "bollinger_lower:20:2.0",
]


class _CandleView:
    """Adapts a candle dict to the cache's positional OHLCV attribute contract."""

    def __init__(self, candle: dict[str, Any]) -> None:
        self.ts = candle["ts"]
        self.o = float(candle["o"])
        self.h = float(candle["h"])
        self.l = float(candle["l"])  # noqa: E741
        self.c = float(candle["c"])
        self.v = float(candle["v"])


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to tz-aware UTC for cross-source equality."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _json_safe(snapshot: dict[str, float]) -> dict[str, float | None]:
    # Postgres JSONB rejects NaN, and NaN is not valid JSON: map NaN -> None so
    # both the persisted payload and the published event serialize cleanly.
    return {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in snapshot.items()
    }


async def on_candle_close(
    ctx: dict[str, Any], instrument_id: int, tf: str, candle: dict[str, Any]
) -> int:
    db = ctx["db"]
    redis = ctx["redis"]

    result = await db.execute(select(ScanRule).where(ScanRule.enabled.is_(True)))
    enabled_rules = list(result.scalars().all())
    if not enabled_rules:
        return 0

    # Market-hours guard: equity instruments must never be evaluated on a candle
    # whose close falls outside the NSE session (stale/off-hours data). Crypto
    # trades 24/7 and is unaffected; in-session equity passes through. Runs
    # after the enabled_rules early-return so a crypto/no-rules candle-close
    # never pays for an unnecessary Instrument fetch.
    instrument = await db.get(Instrument, instrument_id)
    if instrument is not None and instrument.asset_class == "equity":
        bar_ts = datetime.fromisoformat(str(candle["ts"]).replace("Z", "+00:00"))
        if not is_in_session(bar_ts):
            return 0

    hit_ts = datetime.fromisoformat(str(candle["ts"]).replace("Z", "+00:00"))

    # Compile every enabled rule once, then request — PER TIMEFRAME — the union of
    # each rule's period-suffixed keys, so a custom period (rsi:5) is honored
    # instead of collapsing to the default. The closing tf also gets the base
    # REQUESTED set so the stored payload is a stable, informative snapshot.
    compiled_rules = [
        (rule, compile_rule(parse_rule_definition(rule.definition))) for rule in enabled_rules
    ]
    requested_by_tf: dict[str, list[str]] = {tf: list(REQUESTED)}
    for _, compiled in compiled_rules:
        for key, key_tf in compiled.required_indicators():
            keys = requested_by_tf.setdefault(key_tf, [])
            if key not in keys:
                keys.append(key)

    # Warm-start the closing tf from the loaded rows.
    history = await load_recent_candles(db, instrument_id, tf, WARM_START_BARS)

    # Build a snapshot for EVERY tf the rules reference (not just the closing tf),
    # so cross-tf `all` legs can resolve. A referenced tf with no history yields
    # an empty snapshot -> its conditions evaluate False (never raises).
    snapshot_by_tf: dict[str, dict[str, float]] = {}
    for cur_tf, keys in requested_by_tf.items():
        rows = history if cur_tf == tf else await load_recent_candles(
            db, instrument_id, cur_tf, WARM_START_BARS
        )
        if not rows:
            snapshot_by_tf[cur_tf] = {}
            continue
        inst = IndicatorCache(
            load_history=cast(LoadHistory, lambda *_, r=rows: r),
            requested_indicators=keys,
        ).get_or_create(instrument_id, cur_tf)
        if cur_tf == tf and _as_utc(rows[-1].ts) != hit_ts:
            # Closing tf, replay/backfill path: the candle is not yet persisted,
            # so append it (else it is already the last row -> recompute as-is,
            # avoiding a doubled last bar).
            snapshot_by_tf[cur_tf] = inst.update(cast(CandleLike, _CandleView(candle)))
        else:
            snapshot_by_tf[cur_tf] = inst.recompute_from_history()

    safe_payload = _json_safe(snapshot_by_tf.get(tf, {}))

    bar_ts_str = str(candle["ts"])
    hits_written = 0
    for rule, compiled in compiled_rules:
        if not any(t == tf for _, t in compiled.required_indicators()):
            continue
        if not compiled.evaluate(snapshot_by_tf):
            continue
        # Capture rule fields up front: a rollback (benign-dup path) expires the
        # ORM instance, and re-reading rule.id afterwards would trigger lazy IO
        # outside the async greenlet.
        rule_id, rule_user_id, rule_name = rule.id, rule.user_id, rule.name

        # Fast path: skip re-eval if this bar's hit was already written. This is
        # a best-effort cache — the DB UNIQUE(rule_id, instrument_id, ts) is the
        # authoritative dedup below.
        if await hit_already_claimed(redis, rule_id, instrument_id, tf, bar_ts_str):
            continue

        hit = ScanHit(
            rule_id=rule_id,
            instrument_id=instrument_id,
            ts=hit_ts,
            payload=safe_payload,
        )
        db.add(hit)
        try:
            await db.commit()
        except IntegrityError:
            # A concurrent worker / replay already wrote this exact hit: benign
            # duplicate. Roll back and move on (claim the fast-path key so future
            # replays short-circuit before touching the DB).
            await db.rollback()
            await claim_hit(redis, rule_id, instrument_id, tf, bar_ts_str)
            continue
        # Claim the Redis fast-path key only AFTER the row is durably committed,
        # so a failed commit never suppresses a genuine retry.
        await claim_hit(redis, rule_id, instrument_id, tf, bar_ts_str)
        # expire_on_commit=False keeps the identity-mapped instance usable, but
        # the DB-assigned PK may not be loaded until refreshed; ensure hit.id.
        if hit.id is None:
            await db.refresh(hit)

        await redis.publish(
            f"scan_hits:{rule_user_id}",
            json.dumps(
                {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "instrument_id": instrument_id,
                    "tf": tf,
                    "ts": candle["ts"],
                    "payload": safe_payload,
                }
            ),
        )

        # Fan out Telegram alerts only when a live arq pool is present in ctx.
        # Scanner unit/integration tests pass ctx without a pool, so this stays
        # a no-op there; the live worker (app/worker.py) injects "arq_pool".
        pool = ctx.get("arq_pool")
        if pool is not None:
            await pool.enqueue_job("send_telegram_alert_job", hit.id)

        hits_written += 1

    return hits_written


async def scan_on_candle_close_job(
    ctx: dict[str, Any], instrument_id: int, tf: str, candle: dict[str, Any]
) -> int:
    """Thin live arq entrypoint. arq calls functions as ``func(ctx, *args)``.

    Opens a session from the live ``ctx["session_factory"]`` and adapts it to the
    ``ctx["db"]`` contract ``on_candle_close`` expects (which commits internally,
    so no outer commit is needed). Passes through the arq pool so hits fan out.
    """
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        sub_ctx: dict[str, Any] = {
            "db": session,
            "redis": ctx["redis"],
            "arq_pool": ctx.get("arq_pool"),
        }
        return await on_candle_close(sub_ctx, instrument_id, tf, candle)
