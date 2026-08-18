import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.candle import Candle
from app.ingest.metrics import SupportsRedisKV
from app.ingest.writer import upsert_candles
from app.models.candle import CandleRow

_TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}


class SupportsFetchOHLCV(Protocol):
    async def fetch_ohlcv(
        self, symbol: str, timeframe: str, since: int, limit: int
    ) -> list[list[float]]: ...


def find_gaps(
    existing_ts: list[datetime], tf: str, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """Return (gap_start, gap_end) inclusive pairs of missing bar timestamps."""
    step = timedelta(minutes=_TF_MINUTES[tf])
    existing = set(existing_ts)
    gaps: list[tuple[datetime, datetime]] = []
    gap_start: datetime | None = None
    ts = start
    while ts < end:
        if ts not in existing:
            if gap_start is None:
                gap_start = ts
        else:
            if gap_start is not None:
                gaps.append((gap_start, ts - step))
                gap_start = None
        ts += step
    if gap_start is not None:
        gaps.append((gap_start, end - step))
    return gaps


async def backfill_gaps(
    ctx: dict[str, Any],
    instrument_id: int,
    symbol: str,
    tf: str,
    start_ts: datetime,
    end_ts: datetime,
) -> int:
    """arq task: detect gaps for (instrument_id, tf) in [start_ts, end_ts) and fill via CCXT."""
    redis: SupportsRedisKV = ctx["redis"]
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] = ctx[
        "session_factory"
    ]
    exchange: SupportsFetchOHLCV = ctx["exchange"]
    rate_limit_ms: int = ctx.get("backfill_rate_limit_ms", 250)

    async with session_factory() as session:
        result = await session.execute(
            select(CandleRow.ts).where(
                CandleRow.instrument_id == instrument_id,
                CandleRow.tf == tf,
                CandleRow.ts >= start_ts,
                CandleRow.ts < end_ts,
            )
        )
        existing_ts = [row[0] for row in result.all()]

    gaps = find_gaps(existing_ts, tf, start_ts, end_ts)
    total_written = 0

    for gap_start, gap_end in gaps:
        # Number of bars in the gap is the span divided by the timeframe's
        # length, not a hardcoded per-minute count — otherwise 5m/15m/1h gaps
        # over-request by the tf-minute factor.
        limit = int((gap_end - gap_start).total_seconds() // (60 * _TF_MINUTES[tf])) + 1
        since_ms = int(gap_start.timestamp() * 1000)
        raw_rows = await exchange.fetch_ohlcv(symbol, timeframe=tf, since=since_ms, limit=limit)
        candles = [
            Candle(
                symbol=symbol,
                tf=tf,
                ts=datetime.fromtimestamp(row[0] / 1000, tz=UTC),
                o=Decimal(str(row[1])),
                h=Decimal(str(row[2])),
                l=Decimal(str(row[3])),
                c=Decimal(str(row[4])),
                v=Decimal(str(row[5])),
            )
            for row in raw_rows
            if gap_start <= datetime.fromtimestamp(row[0] / 1000, tz=UTC) <= gap_end
        ]
        async with session_factory() as session:
            written = await upsert_candles(session, instrument_id, candles)
            await session.commit()
        total_written += written
        await asyncio.sleep(rate_limit_ms / 1000)

    await redis.set(
        f"ingest:backfill:{symbol}:{tf}:last_run",
        str(datetime.now(UTC).timestamp()),
    )
    return total_written
