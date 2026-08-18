import pytest
from alembic.config import Config
from sqlalchemy import text

from alembic import command
from app.core.deps import get_engine

EXPECTED_TABLES = {
    "instruments", "candles", "scan_rules", "scan_hits", "signals",
    "backtests", "market_regimes", "news_items", "kb_chunks",
    "chat_sessions", "chat_messages", "alert_subscriptions",
}


@pytest.mark.asyncio
async def test_migrations_apply_cleanly():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    async with engine.connect() as conn:
        ext_result = await conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        assert ext_result.scalar() == "vector"

        table_result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        tables = {row[0] for row in table_result}
        assert EXPECTED_TABLES.issubset(tables)
