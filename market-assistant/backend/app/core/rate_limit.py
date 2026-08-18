from __future__ import annotations

import redis.asyncio as redis


class RateLimitExceeded(Exception):
    def __init__(self, key: str, limit: int, window_seconds: int) -> None:
        self.key = key
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit exceeded for {key}: {limit}/{window_seconds}s")


async def check_rate_limit(
    client: redis.Redis, key: str, limit: int, window_seconds: int
) -> bool:
    """Fixed-window counter. Increments ratelimit:{key} and ensures it carries a
    TTL. Returns True if allowed (count <= limit), False if over the limit.

    H6: EXPIRE is issued with NX (set only when no TTL exists) on EVERY call
    rather than only when count == 1. A crash between INCR and EXPIRE would
    otherwise leave a TTL-less counter that never resets; the NX form both keeps
    the window fixed (later hits don't extend it) and self-heals a leaked key on
    the next request."""
    redis_key = f"ratelimit:{key}"
    count = await client.incr(redis_key)
    await client.expire(redis_key, window_seconds, nx=True)
    return bool(count <= limit)


async def enforce_rate_limit(
    client: redis.Redis, key: str, limit: int, window_seconds: int
) -> None:
    if not await check_rate_limit(client, key, limit, window_seconds):
        raise RateLimitExceeded(key, limit, window_seconds)
