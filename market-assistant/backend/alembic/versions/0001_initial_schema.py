"""initial schema"""
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("""
        CREATE TABLE instruments (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            exchange TEXT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            UNIQUE (symbol, exchange)
        )
    """)

    op.execute("""
        CREATE TABLE candles (
            instrument_id INT REFERENCES instruments(id),
            tf TEXT NOT NULL,
            ts TIMESTAMPTZ NOT NULL,
            o NUMERIC, h NUMERIC, l NUMERIC, c NUMERIC, v NUMERIC,
            PRIMARY KEY (instrument_id, tf, ts)
        ) PARTITION BY RANGE (ts)
    """)
    op.execute("""
        CREATE TABLE candles_default PARTITION OF candles DEFAULT
    """)

    op.execute("""
        CREATE TABLE scan_rules (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            name TEXT NOT NULL,
            definition JSONB NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE scan_hits (
            id BIGSERIAL PRIMARY KEY,
            rule_id INT REFERENCES scan_rules(id),
            instrument_id INT REFERENCES instruments(id),
            ts TIMESTAMPTZ NOT NULL,
            payload JSONB
        )
    """)

    op.execute("""
        CREATE TABLE signals (
            id BIGSERIAL PRIMARY KEY,
            instrument_id INT REFERENCES instruments(id),
            strategy TEXT NOT NULL,
            direction TEXT NOT NULL,
            ts TIMESTAMPTZ NOT NULL,
            confidence NUMERIC,
            ref_entry NUMERIC, ref_sl NUMERIC, ref_tp NUMERIC,
            backtest_ref UUID,
            meta JSONB
        )
    """)

    op.execute("""
        CREATE TABLE backtests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strategy TEXT, params JSONB, universe JSONB,
            start_ts TIMESTAMPTZ, end_ts TIMESTAMPTZ,
            fees_bps NUMERIC NOT NULL,
            slippage_bps NUMERIC NOT NULL,
            stats JSONB,
            equity_curve JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE market_regimes (
            instrument_id INT, tf TEXT, ts TIMESTAMPTZ,
            regime TEXT,
            adx NUMERIC, atr_pct NUMERIC,
            PRIMARY KEY (instrument_id, tf, ts)
        )
    """)

    op.execute("""
        CREATE TABLE news_items (
            id BIGSERIAL PRIMARY KEY,
            source TEXT, title TEXT, url TEXT UNIQUE, published_at TIMESTAMPTZ,
            sentiment NUMERIC,
            tickers TEXT[]
        )
    """)

    op.execute("""
        CREATE TABLE kb_chunks (
            id BIGSERIAL PRIMARY KEY,
            doc TEXT NOT NULL,
            chunk TEXT NOT NULL,
            embedding VECTOR(384)
        )
    """)

    op.execute("""
        CREATE TABLE chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE chat_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id UUID REFERENCES chat_sessions(id),
            role TEXT NOT NULL,
            content TEXT,
            tool_calls JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE alert_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id UUID, rule_id INT,
            channel TEXT, target TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS alert_subscriptions")
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TABLE IF EXISTS chat_sessions")
    op.execute("DROP TABLE IF EXISTS kb_chunks")
    op.execute("DROP TABLE IF EXISTS news_items")
    op.execute("DROP TABLE IF EXISTS market_regimes")
    op.execute("DROP TABLE IF EXISTS backtests")
    op.execute("DROP TABLE IF EXISTS signals")
    op.execute("DROP TABLE IF EXISTS scan_hits")
    op.execute("DROP TABLE IF EXISTS scan_rules")
    op.execute("DROP TABLE IF EXISTS candles_default")
    op.execute("DROP TABLE IF EXISTS candles")
    op.execute("DROP TABLE IF EXISTS instruments")
