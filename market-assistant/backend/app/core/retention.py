"""Phase 12 Task 4: candle retention.

Free-tier survival guard — drop old fine-grained (1m) candles so the managed
Postgres stays inside its storage quota. Coarser timeframes are retained.
"""

from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candle import CandleRow


async def drop_old_candles(
    session: AsyncSession,
    tf: str,
    older_than_days: int,
    now: datetime,
) -> int:
    """Delete ``candles`` rows of the given ``tf`` older than the retention window.

    Returns the number of rows deleted.
    """
    cutoff = now - timedelta(days=older_than_days)
    stmt = delete(CandleRow).where(CandleRow.tf == tf, CandleRow.ts < cutoff)
    result = await session.execute(stmt)
    await session.commit()
    return int(result.rowcount)  # type: ignore[attr-defined]
