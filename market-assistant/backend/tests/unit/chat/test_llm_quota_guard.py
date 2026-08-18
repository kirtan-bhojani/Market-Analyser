"""Phase 12 Task 5: global daily LLM quota guard."""

from datetime import date

from app.chat.quota import LlmQuotaGuard


class FakeRedis:
    def __init__(self):
        self.store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int, nx: bool = False) -> None:
        pass


async def test_allows_up_to_daily_quota_then_blocks(monkeypatch):
    monkeypatch.setattr("app.chat.quota._today", lambda: date(2026, 7, 10))
    guard = LlmQuotaGuard(redis_client=FakeRedis(), daily_quota=3)

    assert await guard.check_and_increment("groq") is True
    assert await guard.check_and_increment("groq") is True
    assert await guard.check_and_increment("groq") is True
    assert await guard.check_and_increment("groq") is False  # 4th exceeds cap of 3


async def test_quota_resets_on_new_utc_date(monkeypatch):
    guard = LlmQuotaGuard(redis_client=FakeRedis(), daily_quota=1)

    monkeypatch.setattr("app.chat.quota._today", lambda: date(2026, 7, 10))
    assert await guard.check_and_increment("groq") is True
    assert await guard.check_and_increment("groq") is False

    monkeypatch.setattr("app.chat.quota._today", lambda: date(2026, 7, 11))
    assert await guard.check_and_increment("groq") is True  # new day, counter reset


async def test_counts_are_per_provider(monkeypatch):
    monkeypatch.setattr("app.chat.quota._today", lambda: date(2026, 7, 10))
    guard = LlmQuotaGuard(redis_client=FakeRedis(), daily_quota=1)

    assert await guard.check_and_increment("groq") is True
    assert await guard.check_and_increment("gemini") is True  # separate counter
    assert await guard.check_and_increment("groq") is False
