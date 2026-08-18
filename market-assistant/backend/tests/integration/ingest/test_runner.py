import asyncio
import copy
import json
import sys
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.ingest import runner
from app.models.candle import CandleRow
from app.models.instrument import Instrument
from tests.fixtures.binance_klines import VALID_CLOSED_KLINE


def _kline(ts_ms: int) -> dict:
    msg = copy.deepcopy(VALID_CLOSED_KLINE)
    msg["k"]["t"] = ts_ms
    msg["k"]["T"] = ts_ms + 59999
    return msg


class _FakeWS:
    """Async CM + async iterator: yields the given messages, then cancels."""

    def __init__(self, messages: list[dict]) -> None:
        self._messages = messages

    async def __aenter__(self) -> "_FakeWS":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._messages:
            yield json.dumps(m)
        raise asyncio.CancelledError()


class _BlockingWS:
    """Async CM + iterator: yields messages, signals ready, then parks open
    (like a live socket) until the surrounding task is externally cancelled."""

    def __init__(self, messages: list[dict], ready: asyncio.Event) -> None:
        self._messages = messages
        self._ready = ready

    async def __aenter__(self) -> "_BlockingWS":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._messages:
            yield json.dumps(m)
        self._ready.set()
        await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_run_ingest_wires_universe_instruments_and_candles(
    monkeypatch, session_factory
):
    # Fake exchange: two USDT pairs (kept, volume-sorted) + one non-USDT (dropped).
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(
        return_value={
            "BTC/USDT": {"quoteVolume": 1000},
            "ETH/USDT": {"quoteVolume": 500},
            "DOGE/BTC": {"quoteVolume": 9999},
        }
    )

    # Two distinct closed klines for BTC/USDT (distinct ts -> two rows).
    kline1 = _kline(1700000000000)
    kline2 = _kline(1700000060000)

    def connect_fn(url: str) -> _FakeWS:
        return _FakeWS([kline1, kline2])

    # Bind the pipeline to the test's shared-connection factory + a fake redis
    # so it is fully hermetic (no real DB session pool, no real redis).
    monkeypatch.setattr(runner, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(runner, "get_redis", lambda: AsyncMock())

    modules_before = set(sys.modules)

    with pytest.raises(asyncio.CancelledError):
        await runner.run_ingest(connect_fn=connect_fn, exchange=exchange)

    # Lazy defaults were skipped because both args were injected.
    new_modules = set(sys.modules) - modules_before
    assert not any(m == "ccxt" or m.startswith("ccxt.") for m in new_modules)
    assert "websockets" not in new_modules

    # Universe selected -> Instrument rows created (get-or-create).
    async with session_factory() as session:
        symbols = set(
            (await session.execute(select(Instrument.symbol))).scalars().all()
        )
        candle_count = await session.scalar(
            select(func.count()).select_from(CandleRow)
        )
    assert symbols == {"BTC/USDT", "ETH/USDT"}
    # Parsed candles were buffered and the shutdown drain persisted them.
    assert candle_count == 2


@pytest.mark.asyncio
async def test_run_ingest_get_or_create_is_idempotent(monkeypatch, session_factory):
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(
        return_value={"BTC/USDT": {"quoteVolume": 1000}}
    )

    def connect_fn(url: str) -> _FakeWS:
        return _FakeWS([])  # no candles, cancels immediately

    monkeypatch.setattr(runner, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(runner, "get_redis", lambda: AsyncMock())

    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await runner.run_ingest(connect_fn=connect_fn, exchange=exchange)

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Instrument)
            .where(Instrument.symbol == "BTC/USDT")
        )
    assert count == 1


@pytest.mark.asyncio
async def test_run_ingest_external_cancel_drains_buffered_candles(
    monkeypatch, session_factory
):
    # Real deploy shutdown path: the pipeline is a long-running task the
    # supervisor stops via task.cancel() (not the WS raising from inside).
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(
        return_value={"BTC/USDT": {"quoteVolume": 1000}}
    )

    ready = asyncio.Event()
    kline1 = _kline(1700000000000)
    kline2 = _kline(1700000060000)

    def connect_fn(url: str) -> _BlockingWS:
        return _BlockingWS([kline1, kline2], ready)

    monkeypatch.setattr(runner, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(runner, "get_redis", lambda: AsyncMock())

    task = asyncio.create_task(
        runner.run_ingest(connect_fn=connect_fn, exchange=exchange)
    )
    # Wait until both candles are buffered and the socket is parked open.
    await asyncio.wait_for(ready.wait(), timeout=5)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Clean cancellation still best-effort drained the buffered candles.
    async with session_factory() as session:
        candle_count = await session.scalar(
            select(func.count()).select_from(CandleRow)
        )
    assert candle_count == 2
