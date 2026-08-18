import pytest
from sqlalchemy import select

from app.ingest.universe_equity import NIFTY50_SYMBOLS, ensure_equity_instruments
from app.models.instrument import Instrument


@pytest.mark.asyncio
async def test_ensure_equity_instruments_creates_all_symbols(db_session):
    instruments = await ensure_equity_instruments(db_session)
    await db_session.commit()

    assert len(instruments) == len(NIFTY50_SYMBOLS)
    assert all(i.asset_class == "equity" for i in instruments)
    assert all(i.exchange == "NSE" for i in instruments)
    assert {i.symbol for i in instruments} == {f"{s}.NS" for s in NIFTY50_SYMBOLS}


@pytest.mark.asyncio
async def test_ensure_equity_instruments_idempotent(db_session):
    await ensure_equity_instruments(db_session)
    await db_session.commit()
    await ensure_equity_instruments(db_session)
    await db_session.commit()

    result = await db_session.execute(select(Instrument).where(Instrument.asset_class == "equity"))
    rows = result.scalars().all()
    assert len(rows) == len(NIFTY50_SYMBOLS)
