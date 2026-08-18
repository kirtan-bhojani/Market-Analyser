from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.candle import CandleRow
from app.models.instrument import Instrument


@pytest.mark.asyncio
async def test_instrument_round_trips(db_session):
    inst = Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.commit()

    result = await db_session.execute(
        select(Instrument).where(Instrument.symbol == "BTC/USDT")
    )
    row = result.scalar_one()
    assert row.asset_class == "crypto"
    assert row.exchange == "binance"
    assert row.active is True


@pytest.mark.asyncio
async def test_candle_row_round_trips(db_session):
    inst = Instrument(symbol="ETH/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.flush()

    candle = CandleRow(
        instrument_id=inst.id,
        tf="1m",
        ts=datetime(2024, 1, 1, tzinfo=UTC),
        o=Decimal("2000.0"),
        h=Decimal("2010.0"),
        l=Decimal("1990.0"),
        c=Decimal("2005.0"),
        v=Decimal("100.0"),
    )
    db_session.add(candle)
    await db_session.commit()

    result = await db_session.execute(
        select(CandleRow).where(CandleRow.instrument_id == inst.id, CandleRow.tf == "1m")
    )
    row = result.scalar_one()
    assert row.c == Decimal("2005.0")
