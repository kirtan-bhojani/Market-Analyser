"""Phase 12 Task 5: global (all-users) daily LLM quota guard.

Protects the free-tier provider budget: a single Redis counter per provider per
UTC date is incremented on every LLM call; once the configured daily cap is hit,
``check_and_increment`` returns ``False`` (it never raises) so the orchestrator
can fall back gracefully instead of hammering the provider.

The app's Redis client is async (``redis.asyncio``), so the guard is async too.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import redis.asyncio as redis


def _today() -> date:
    # UTC date, matching the documented per-UTC-date counter — date.today()
    # is the host-local date and would roll the quota over at the wrong instant.
    return datetime.now(UTC).date()


# Slightly over 24h so a counter survives clock drift before its date rolls over.
_TTL_SECONDS = 60 * 60 * 26


class LlmQuotaGuard:
    def __init__(self, redis_client: redis.Redis, daily_quota: int):
        self._redis = redis_client
        self._daily_quota = daily_quota

    def _key(self, provider: str) -> str:
        return f"llm_quota:{provider}:{_today().isoformat()}"

    async def check_and_increment(self, provider: str) -> bool:
        key = self._key(provider)
        count = int(await self._redis.incr(key))
        # H6: EXPIRE NX on every call rather than only when count == 1 — a crash
        # between INCR and EXPIRE would otherwise leave the daily counter with no
        # TTL so it never rolls over. NX keeps the once-set TTL and self-heals.
        await self._redis.expire(key, _TTL_SECONDS, nx=True)
        return count <= self._daily_quota
