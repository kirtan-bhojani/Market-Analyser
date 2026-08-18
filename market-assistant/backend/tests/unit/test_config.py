from app.core.config import get_settings


def test_settings_loads_database_and_redis_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://market:market@localhost:5434/market_assistant")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == "postgresql+asyncpg://market:market@localhost:5434/market_assistant"
    assert settings.redis_url == "redis://localhost:6379/0"
