from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.ingest.candle import Candle
from app.ingest.equity_poller import poll_equity_universe
from app.models.candle import CandleRow

IST = ZoneInfo("Asia/Kolkata")
IN_SESSION_NOW = datetime(2025, 6, 9, 10, 0, tzinfo=IST)


def _fake_fetch_candles(symbol, tf, start, end, client=None):
    return [
        Candle(
            symbol=f"{symbol}.NS" if "." not in symbol else symbol,
            tf=tf,
            ts=IN_SESSION_NOW,
            o=Decimal("2900"),
            h=Decimal("2910"),
            l=Decimal("2895"),
            c=Decimal("2905"),
            v=Decimal("120000"),
        )
    ]


@pytest.mark.asyncio
async def test_poll_equity_universe_idempotent_on_rerun(db_session, redis_client):
    ctx = {"session_factory": lambda: db_session, "redis": redis_client}

    with (
        patch(
            "app.ingest.equity_poller.fetch_candles",
            side_effect=_fake_fetch_candles,
        ),
        patch("app.ingest.equity_poller.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = IN_SESSION_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        first_count = await poll_equity_universe(ctx)
        second_count = await poll_equity_universe(ctx)

    result = await db_session.execute(select(CandleRow))
    rows = result.scalars().all()

    assert first_count > 0
    assert second_count == first_count  # same candles re-fetched, no duplicates
    assert len(rows) == first_count  # idempotent upsert, not doubled


@pytest.mark.asyncio
async def test_poll_equity_universe_skips_outside_session(db_session, redis_client):
    ctx = {"session_factory": lambda: db_session, "redis": redis_client}
    outside_session = datetime(2025, 6, 9, 20, 0, tzinfo=IST)  # 8pm, after close

    with (
        patch(
            "app.ingest.equity_poller.fetch_candles",
            side_effect=_fake_fetch_candles,
        ),
        patch("app.ingest.equity_poller.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = outside_session

        count = await poll_equity_universe(ctx)

    assert count == 0
