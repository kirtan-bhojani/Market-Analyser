from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.ingest.backfill import backfill_gaps, find_gaps
from app.models.candle import CandleRow
from app.models.instrument import Instrument


def test_find_gaps_detects_synthetic_30min_hole():
    start = datetime(2024, 4, 1, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)
    # candles present for minutes 0-9 and 40-59, missing 10-39 (30-min hole)
    existing = [start + timedelta(minutes=i) for i in range(0, 10)]
    existing += [start + timedelta(minutes=i) for i in range(40, 60)]

    gaps = find_gaps(existing, tf="1m", start=start, end=end)

    assert gaps == [(start + timedelta(minutes=10), start + timedelta(minutes=39))]


@pytest.mark.asyncio
async def test_backfill_gaps_fills_synthetic_hole_via_ccxt_fixture(db_session, session_factory):
    inst = Instrument(symbol="BNB/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.commit()

    start = datetime(2024, 4, 1, tzinfo=UTC)
    # Pre-seed minutes 0-9 and 40-59 directly, leaving a 30-min hole at 10-39.
    present_minutes = list(range(0, 10)) + list(range(40, 60))
    for m in present_minutes:
        db_session.add(
            CandleRow(
                instrument_id=inst.id,
                tf="1m",
                ts=start + timedelta(minutes=m),
                o=Decimal("300"),
                h=Decimal("301"),
                l=Decimal("299"),
                c=Decimal("300.5"),
                v=Decimal("10"),
            )
        )
    await db_session.commit()

    # CCXT fixture: fetch_ohlcv returns rows for the full requested range,
    # the backfill job only needs to write the missing 30 rows.
    def fake_fetch_ohlcv(symbol, timeframe, since, limit):
        rows = []
        since_dt = datetime.fromtimestamp(since / 1000, tz=UTC)
        for i in range(limit):
            ts = since_dt + timedelta(minutes=i)
            if ts >= start + timedelta(hours=1):
                break
            rows.append([int(ts.timestamp() * 1000), 300.0, 301.0, 299.0, 300.5, 10.0])
        return rows

    exchange = AsyncMock()
    exchange.fetch_ohlcv = AsyncMock(side_effect=fake_fetch_ohlcv)

    class Ctx(dict):
        pass

    ctx = Ctx(redis=AsyncMock(), session_factory=session_factory, exchange=exchange)

    written = await backfill_gaps(
        ctx,
        instrument_id=inst.id,
        symbol="BNB/USDT",
        tf="1m",
        start_ts=start,
        end_ts=start + timedelta(hours=1),
    )

    assert written == 30
    async with session_factory() as verify_session:
        count = await verify_session.scalar(
            select(func.count())
            .select_from(CandleRow)
            .where(CandleRow.instrument_id == inst.id)
        )
    assert count == 60  # 30 pre-seeded + 30 backfilled = full hour, zero gaps
