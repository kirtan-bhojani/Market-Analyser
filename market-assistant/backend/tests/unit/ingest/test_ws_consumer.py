import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ingest.buffer import CandleBuffer
from app.ingest.ws_consumer import BinanceWSConsumer, compute_backoff_delay
from tests.fixtures.binance_klines import VALID_CLOSED_KLINE


def test_backoff_delay_grows_exponentially_and_caps():
    assert compute_backoff_delay(attempt=0, max_backoff_s=60.0) == 1.0
    assert compute_backoff_delay(attempt=1, max_backoff_s=60.0) == 2.0
    assert compute_backoff_delay(attempt=2, max_backoff_s=60.0) == 4.0
    assert compute_backoff_delay(attempt=10, max_backoff_s=60.0) == 60.0


class _StreamEnded(Exception):
    pass


class _FakeWSMessages:
    """Async context manager + async iterator yielding one message then raising."""
    def __init__(self, messages, then_raise=None):
        self._messages = messages
        self._then_raise = then_raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._messages:
            yield json.dumps(m)
        if self._then_raise:
            raise self._then_raise


@pytest.mark.asyncio
async def test_valid_message_is_parsed_and_added_to_buffer():
    buffer = CandleBuffer(symbol_to_instrument_id={"BTC/USDT": 1})
    redis = AsyncMock()

    connect_fn = MagicMock(
        return_value=_FakeWSMessages([VALID_CLOSED_KLINE], then_raise=_StreamEnded())
    )
    consumer = BinanceWSConsumer(
        symbols=["BTC/USDT"],
        buffer=buffer,
        redis=redis,
        connect_fn=connect_fn,
        max_backoff_s=1.0,
    )

    with pytest.raises(_StreamEnded):
        await consumer._consume_once()

    assert buffer.pending_count == 1
    redis.set.assert_called()  # heartbeat recorded


class _RawWSMessages:
    """Yields raw strings verbatim (no json.dumps), then raises."""
    def __init__(self, raws, then_raise=None):
        self._raws = raws
        self._then_raise = then_raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for r in self._raws:
            yield r
        if self._then_raise:
            raise self._then_raise


@pytest.mark.asyncio
async def test_malformed_frame_is_skipped_not_dropping_the_socket():
    buffer = CandleBuffer(symbol_to_instrument_id={"BTC/USDT": 1})
    redis = AsyncMock()

    raws = ["{not valid json", json.dumps(VALID_CLOSED_KLINE)]
    connect_fn = MagicMock(return_value=_RawWSMessages(raws, then_raise=_StreamEnded()))
    consumer = BinanceWSConsumer(
        symbols=["BTC/USDT"], buffer=buffer, redis=redis, connect_fn=connect_fn, max_backoff_s=1.0,
    )

    # The malformed frame must NOT surface as a connection error (which would
    # tear down the socket) — the loop skips it and still consumes the next.
    with pytest.raises(_StreamEnded):
        await consumer._consume_once()

    assert buffer.pending_count == 1


@pytest.mark.asyncio
async def test_reconnects_with_backoff_after_connection_drop(monkeypatch):
    buffer = CandleBuffer(symbol_to_instrument_id={"BTC/USDT": 1})
    redis = AsyncMock()

    attempts = {"count": 0}

    def connect_fn(url):
        attempts["count"] += 1
        if attempts["count"] < 3:
            return _FakeWSMessages([], then_raise=ConnectionError("dropped"))
        raise asyncio.CancelledError()  # stop the test after 3rd attempt

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.ingest.ws_consumer.asyncio.sleep", fake_sleep)

    consumer = BinanceWSConsumer(
        symbols=["BTC/USDT"], buffer=buffer, redis=redis, connect_fn=connect_fn, max_backoff_s=60.0,
    )

    with pytest.raises(asyncio.CancelledError):
        await consumer.run()

    assert sleep_calls == [1.0, 2.0]
    assert attempts["count"] == 3
