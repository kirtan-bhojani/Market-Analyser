from app.core.config import Settings, get_settings
from app.core.deps import get_engine


def test_default_db_schema_is_public() -> None:
    settings = get_settings()
    assert settings.db_schema == "public"
    assert settings.jwt_audience == "authenticated"


def test_phase11_fields_load_from_constructor() -> None:
    settings = Settings(
        db_schema="market_assistant",
        cors_allowed_origins="https://a.com, https://b.com",
    )
    assert settings.db_schema == "market_assistant"
    assert settings.cors_origins_list == ["https://a.com", "https://b.com"]


def test_get_engine_builds_engine_for_non_public_schema(monkeypatch) -> None:
    from app.core import deps

    def _fake_settings() -> Settings:
        return Settings(db_schema="market_assistant")

    monkeypatch.setattr(deps, "get_settings", _fake_settings)
    get_engine.cache_clear()
    try:
        engine = get_engine()
        assert engine is not None
        from sqlalchemy.ext.asyncio import AsyncEngine

        assert isinstance(engine, AsyncEngine)
    finally:
        get_engine.cache_clear()
