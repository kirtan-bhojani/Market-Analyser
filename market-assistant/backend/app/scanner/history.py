"""Async candle-history loader for scanner warm-start.

The Task-4 indicator cache warms up from a synchronous ``load_history``
callback, but reading candles is an async DB query. The worker pre-fetches the
recent history with this coroutine and hands the cache a closure that returns
the already-loaded rows, keeping the cache's sync contract intact.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candle import CandleRow


async def load_recent_candles(
    session: AsyncSession, instrument_id: int, tf: str, limit: int
) -> list[CandleRow]:
    """Return up to ``limit`` most-recent candles for (instrument, tf), oldest first."""
    result = await session.execute(
        select(CandleRow)
        .where(CandleRow.instrument_id == instrument_id, CandleRow.tf == tf)
        .order_by(CandleRow.ts.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    rows.reverse()  # SELECT was DESC; return ascending ts for indicator series
    return rows
