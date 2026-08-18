import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.aggregator import LiveAggregator
from app.ingest.candle import Candle
from app.ingest.dispatch import SupportsEnqueue, dispatch_close_jobs
from app.ingest.writer import publish_candles, upsert_candles

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class CandleBuffer:
    def __init__(
        self,
        symbol_to_instrument_id: dict[str, int],
        redis: Redis | None = None,
        arq_pool: SupportsEnqueue | None = None,
        aggregator: LiveAggregator | None = None,
    ) -> None:
        self._symbol_to_instrument_id = symbol_to_instrument_id
        self._redis = redis
        self._arq_pool = arq_pool
        self._aggregator = aggregator
        self._pending: dict[str, list[Candle]] = defaultdict(list)
        self._lock = asyncio.Lock()

    @property
    def pending_count(self) -> int:
        return sum(len(v) for v in self._pending.values())

    def add(self, candle: Candle) -> None:
        self._pending[candle.symbol].append(candle)

    async def _take_batch(self) -> dict[str, list[Candle]]:
        # Atomically swap the pending batch out under the lock.
        async with self._lock:
            batch, self._pending = self._pending, defaultdict(list)
        return batch

    async def _requeue(self, batch: dict[str, list[Candle]]) -> None:
        # Merge a failed batch back into _pending under the lock so the next
        # tick retries it. Prepend the failed candles ahead of any that arrived
        # while the batch was in flight; the (instrument_id, tf, ts) upsert is
        # idempotent, so re-delivery of partially-written rows is safe.
        async with self._lock:
            for symbol, candles in batch.items():
                self._pending[symbol] = candles + self._pending[symbol]

    async def _write_batch(
        self, session: AsyncSession, batch: dict[str, list[Candle]]
    ) -> int:
        total_written = 0
        for symbol, candles in batch.items():
            instrument_id = self._symbol_to_instrument_id.get(symbol)
            if instrument_id is None:
                logger.warning(
                    "flush: unknown symbol %s, dropping %d candles", symbol, len(candles)
                )
                continue
            total_written += await upsert_candles(session, instrument_id, candles)
        return total_written

    async def flush(self, session: AsyncSession) -> int:
        batch = await self._take_batch()
        return await self._write_batch(session, batch)

    async def _flush_once(self, session_factory: SessionFactory) -> int:
        batch = await self._take_batch()
        if not batch:
            return 0
        async with session_factory() as session:
            try:
                written = await self._write_batch(session, batch)
                await session.commit()
            except asyncio.CancelledError:
                # A cancel between the batch swap and a durable commit would
                # otherwise drop the in-flight batch. Merge it back
                # synchronously (no await -> atomic against a concurrent add())
                # and re-raise to honor the cancellation.
                for symbol, candles in batch.items():
                    self._pending[symbol] = candles + self._pending[symbol]
                raise
            except Exception:
                await session.rollback()
                await self._requeue(batch)
                logger.exception(
                    "buffer flush failed; re-queued %d candles for retry",
                    sum(len(v) for v in batch.values()),
                )
                return 0
            if written:
                logger.info("buffer flush wrote %d candles", written)
            # Fan out to the WS feed only AFTER the durable commit, so a
            # subscriber never sees a candle a rollback would have discarded.
            # Publish only known symbols (unknown ones were dropped, not
            # written) and never let a publish error abort the flush cycle.
            if self._redis is not None:
                for symbol, candles in batch.items():
                    if self._symbol_to_instrument_id.get(symbol) is None:
                        continue
                    try:
                        await publish_candles(self._redis, candles)
                    except Exception:
                        logger.exception(
                            "publish of %d candles for %s failed", len(candles), symbol
                        )
            # Fan out candle-close compute jobs only AFTER the candles are
            # durably committed. A dispatch failure must never re-queue the
            # batch (the rows are already written; re-flushing would re-run the
            # upsert harmlessly but the point is fan-out is best-effort): log and
            # move on so a transient arq/redis hiccup can't stall ingestion.
            if self._arq_pool is not None:
                try:
                    await dispatch_close_jobs(
                        self._arq_pool,
                        session,
                        batch,
                        self._symbol_to_instrument_id,
                    )
                except Exception:
                    logger.exception("dispatch of candle-close jobs failed")
            if self._aggregator is not None:
                await self._roll_up_higher_tfs(session, batch)
        return written

    async def _roll_up_higher_tfs(
        self, session: AsyncSession, batch: dict[str, list[Candle]]
    ) -> None:
        """Produce, persist and dispatch any higher-tf candles the just-flushed
        1m closes complete. Best-effort: a failure here never rolls back the 1m
        write (already committed) — the window is simply retried next flush."""
        assert self._aggregator is not None
        try:
            emissions = await self._aggregator.produce(
                session, self._symbol_to_instrument_id, batch
            )
            if not emissions:
                return
            higher: dict[str, list[Candle]] = defaultdict(list)
            for e in emissions:
                higher[e.symbol].append(e.candle)
            for symbol, candles in higher.items():
                instrument_id = self._symbol_to_instrument_id.get(symbol)
                if instrument_id is None:
                    continue
                await upsert_candles(session, instrument_id, candles)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("higher-tf aggregation failed")
            return
        # Publish the higher-tf candles only after the commit above succeeded.
        # Known-symbols only, and never let a publish error abort the cycle.
        if self._redis is not None:
            for symbol, candles in higher.items():
                if self._symbol_to_instrument_id.get(symbol) is None:
                    continue
                try:
                    await publish_candles(self._redis, candles)
                except Exception:
                    logger.exception("publish of higher-tf candles for %s failed", symbol)
        # Only advance the aggregator high-water mark after a durable commit.
        self._aggregator.confirm(emissions)
        if self._arq_pool is not None:
            try:
                await dispatch_close_jobs(
                    self._arq_pool, session, higher, self._symbol_to_instrument_id
                )
            except Exception:
                logger.exception("dispatch of higher-tf candle-close jobs failed")

    async def run_flush_loop(
        self, session_factory: SessionFactory, interval_s: float = 5.0
    ) -> None:
        while True:
            await asyncio.sleep(interval_s)
            if self.pending_count == 0:
                continue
            await self._flush_once(session_factory)
