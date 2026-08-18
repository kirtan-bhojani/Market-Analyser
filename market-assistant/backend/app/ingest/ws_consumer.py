import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from types import TracebackType
from typing import Protocol

from app.ingest.buffer import CandleBuffer
from app.ingest.metrics import SupportsRedisKV, record_heartbeat
from app.ingest.parser import parse_binance_kline

logger = logging.getLogger(__name__)


class WSConnection(Protocol):
    async def __aenter__(self) -> "WSConnection": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    def __aiter__(self) -> AsyncIterator[str]: ...


def compute_backoff_delay(attempt: int, max_backoff_s: float) -> float:
    return min(2.0**attempt, max_backoff_s)


class BinanceWSConsumer:
    def __init__(
        self,
        symbols: list[str],
        buffer: CandleBuffer,
        redis: SupportsRedisKV,
        connect_fn: Callable[[str], WSConnection],
        max_backoff_s: float = 60.0,
        base_url: str = "wss://stream.binance.com:9443",
    ):
        self._symbols = symbols
        self._buffer = buffer
        self._redis = redis
        self._connect_fn = connect_fn
        self._max_backoff_s = max_backoff_s
        self._base_url = base_url
        self._attempt = 0

    def _stream_url(self) -> str:
        streams = "/".join(f"{s.replace('/', '').lower()}@kline_1m" for s in self._symbols)
        return f"{self._base_url}/stream?streams={streams}"

    async def _consume_once(self) -> None:
        async with self._connect_fn(self._stream_url()) as ws:
            async for raw in ws:
                self._attempt = 0  # reset backoff on any successful message
                await record_heartbeat(self._redis, "binance_ws")
                # A single malformed / non-object frame must not tear down the
                # socket (which would trigger a backoff reconnect). Skip it.
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("skipping malformed ws frame")
                    continue
                if not isinstance(payload, dict):
                    continue
                msg = payload.get("data", payload)
                candle = parse_binance_kline(msg)
                if candle is not None:
                    self._buffer.add(candle)

    async def run(self) -> None:
        while True:
            try:
                await self._consume_once()
            except (asyncio.CancelledError,):
                raise
            except Exception as exc:
                delay = compute_backoff_delay(self._attempt, self._max_backoff_s)
                logger.warning("ws connection error (%s), reconnecting in %.1fs", exc, delay)
                self._attempt += 1
                await asyncio.sleep(delay)
