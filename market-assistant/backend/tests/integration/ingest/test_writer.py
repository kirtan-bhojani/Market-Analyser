from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.ingest.candle import Candle
from app.ingest.writer import upsert_candles
from app.models.candle import CandleRow
from app.models.instrument import Instrument


@pytest.mark.asyncio
async def test_batch_of_n_candles_writes_n_rows(db_session):
    inst = Instrument(symbol="SOL/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.flush()

    start = datetime(2024, 2, 1, tzinfo=UTC)
    candles = [
        Candle(
            symbol="SOL/USDT", tf="1m", ts=start + timedelta(minutes=i),
            o=Decimal("100"), h=Decimal("101"), l=Decimal("99"), c=Decimal("100.5"),
            v=Decimal("10"),
        )
        for i in range(20)
    ]

    written = await upsert_candles(db_session, inst.id, candles)
    await db_session.commit()

    assert written == 20
    count = await db_session.scalar(
        select(func.count()).select_from(CandleRow).where(CandleRow.instrument_id == inst.id)
    )
    assert count == 20


@pytest.mark.asyncio
async def test_duplicate_key_upsert_is_idempotent_and_updates_close(db_session):
    inst = Instrument(symbol="ADA/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.flush()

    ts = datetime(2024, 2, 1, tzinfo=UTC)
    first = Candle(
        symbol="ADA/USDT", tf="1m", ts=ts,
        o=Decimal("1"), h=Decimal("1.1"), l=Decimal("0.9"), c=Decimal("1.05"), v=Decimal("5"),
    )
    await upsert_candles(db_session, inst.id, [first])
    await db_session.commit()

    revised = Candle(
        symbol="ADA/USDT", tf="1m", ts=ts,
        o=Decimal("1"), h=Decimal("1.2"), l=Decimal("0.9"), c=Decimal("1.15"), v=Decimal("8"),
    )
    written = await upsert_candles(db_session, inst.id, [revised])
    await db_session.commit()

    assert written == 1
    count = await db_session.scalar(
        select(func.count()).select_from(CandleRow).where(CandleRow.instrument_id == inst.id)
    )
    assert count == 1
    row = await db_session.scalar(
        select(CandleRow).where(CandleRow.instrument_id == inst.id, CandleRow.ts == ts)
    )
    assert row.c == Decimal("1.15")
    assert row.v == Decimal("8")
