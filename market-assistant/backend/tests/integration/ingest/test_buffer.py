import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.ingest.buffer import CandleBuffer
from app.ingest.candle import Candle
from app.models.candle import CandleRow
from app.models.instrument import Instrument


@pytest.mark.asyncio
async def test_flush_writes_buffered_candles_and_clears_buffer(db_session):
    inst = Instrument(symbol="XRP/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.flush()

    buffer = CandleBuffer(symbol_to_instrument_id={"XRP/USDT": inst.id})
    buffer.add(Candle(
        symbol="XRP/USDT", tf="1m", ts=datetime(2024, 3, 1, tzinfo=UTC),
        o=Decimal("0.5"), h=Decimal("0.52"), l=Decimal("0.49"),
        c=Decimal("0.51"), v=Decimal("1000"),
    ))

    written = await buffer.flush(db_session)
    await db_session.commit()

    assert written == 1
    assert buffer.pending_count == 0
    count = await db_session.scalar(select(func.count()).select_from(CandleRow))
    assert count == 1


@pytest.mark.asyncio
async def test_run_flush_loop_flushes_every_interval(db_session, session_factory):
    inst = Instrument(symbol="DOT/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.commit()

    buffer = CandleBuffer(symbol_to_instrument_id={"DOT/USDT": inst.id})
    buffer.add(Candle(
        symbol="DOT/USDT", tf="1m", ts=datetime(2024, 3, 1, tzinfo=UTC),
        o=Decimal("5"), h=Decimal("5.1"), l=Decimal("4.9"),
        c=Decimal("5.05"), v=Decimal("50"),
    ))

    task = asyncio.create_task(buffer.run_flush_loop(session_factory, interval_s=0.05))
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    async with session_factory() as verify_session:
        count = await verify_session.scalar(select(func.count()).select_from(CandleRow))
    assert count == 1
    assert buffer.pending_count == 0


@pytest.mark.asyncio
async def test_run_flush_loop_requeues_failed_batch(db_session, session_factory, monkeypatch):
    # A transient write failure must NOT silently drop the swapped-out batch:
    # the candles have to be re-queued so a later tick retries them, and the
    # idempotent upsert must guarantee no duplicates on re-delivery.
    import app.ingest.buffer as buffer_module

    inst = Instrument(symbol="LTC/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.commit()

    buffer = CandleBuffer(symbol_to_instrument_id={"LTC/USDT": inst.id})
    buffer.add(Candle(
        symbol="LTC/USDT", tf="1m", ts=datetime(2024, 3, 1, tzinfo=UTC),
        o=Decimal("100"), h=Decimal("101"), l=Decimal("99"),
        c=Decimal("100.5"), v=Decimal("10"),
    ))

    async def boom(*args, **kwargs):
        raise RuntimeError("transient DB error")

    monkeypatch.setattr(buffer_module, "upsert_candles", boom)

    task = asyncio.create_task(buffer.run_flush_loop(session_factory, interval_s=0.05))
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Failed write must have re-queued the candle, not lost it, and written nothing.
    assert buffer.pending_count == 1
    async with session_factory() as verify_session:
        count = await verify_session.scalar(select(func.count()).select_from(CandleRow))
    assert count == 0

    # Restore the real writer; the next loop must persist the re-queued candle
    # exactly once (idempotent upsert => no duplicate).
    monkeypatch.undo()

    task = asyncio.create_task(buffer.run_flush_loop(session_factory, interval_s=0.05))
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert buffer.pending_count == 0
    async with session_factory() as verify_session:
        count = await verify_session.scalar(select(func.count()).select_from(CandleRow))
    assert count == 1
