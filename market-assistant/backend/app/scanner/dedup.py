"""Same-bar hit dedup via a Redis SET NX key.

A rule/instrument/timeframe/bar tuple should produce at most one ``scan_hit``
even if the candle-close event is replayed (arq retry, duplicate publish). The
first writer atomically claims the key with ``SET key 1 NX EX``; any later
attempt for the same tuple sees the key already set and is treated as a
duplicate. The TTL comfortably exceeds the largest timeframe's same-bar replay
window (the DSL's largest tf is ``1d``, so 48h leaves ample margin), then
expires so the key set stays bounded.
"""

from __future__ import annotations

from redis.asyncio import Redis

DEDUP_TTL_SECONDS = 48 * 3600


def dedup_key(rule_id: int, instrument_id: int, tf: str, bar_ts: str) -> str:
    return f"scan_hit_dedup:{rule_id}:{instrument_id}:{tf}:{bar_ts}"


async def hit_already_claimed(
    redis: Redis, rule_id: int, instrument_id: int, tf: str, bar_ts: str
) -> bool:
    """Read-only fast-path check: has this bar's hit already been written?

    The authoritative dedup is the DB UNIQUE(rule_id, instrument_id, ts); this
    only lets the worker skip re-evaluation cheaply. It must NOT claim the key —
    claiming before the row is committed would suppress a genuine retry if that
    commit later failed. See ``claim_hit``, called only after a durable commit.
    """
    return bool(await redis.exists(dedup_key(rule_id, instrument_id, tf, bar_ts)))


async def claim_hit(
    redis: Redis, rule_id: int, instrument_id: int, tf: str, bar_ts: str
) -> None:
    """Set the fast-path key AFTER the hit row is durably committed."""
    key = dedup_key(rule_id, instrument_id, tf, bar_ts)
    await redis.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
