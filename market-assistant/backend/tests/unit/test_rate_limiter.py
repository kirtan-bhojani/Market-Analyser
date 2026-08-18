from __future__ import annotations

import fakeredis.aioredis
import pytest

from app.core.rate_limit import RateLimitExceeded, check_rate_limit, enforce_rate_limit


@pytest.fixture
def redis_client() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis()


async def test_check_rate_limit_allows_up_to_limit_then_blocks(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    key = "user:1"
    results = [
        await check_rate_limit(redis_client, key, limit=3, window_seconds=60)
        for _ in range(4)
    ]
    assert results == [True, True, True, False]


async def test_enforce_rate_limit_raises_on_exceeding_call(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    key = "user:2"
    for _ in range(3):
        await enforce_rate_limit(redis_client, key, limit=3, window_seconds=60)

    with pytest.raises(RateLimitExceeded):
        await enforce_rate_limit(redis_client, key, limit=3, window_seconds=60)


async def test_independent_keys_have_independent_counters(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    assert await check_rate_limit(redis_client, "user:a", limit=1, window_seconds=60)
    assert await check_rate_limit(redis_client, "user:b", limit=1, window_seconds=60)
