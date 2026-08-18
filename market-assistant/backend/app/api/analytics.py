import uuid
from collections import defaultdict
from typing import Any, Literal

import pandas as pd
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.correlation import CorrelationMatrix, compute_correlation_matrix
from app.analytics.seasonality import Seasonality, compute_seasonality
from app.core.auth import get_current_user_id
from app.core.deps import get_redis, get_session
from app.core.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.models.candle import CandleRow
from app.models.instrument import Instrument

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Per-user analytics budget: these endpoints run correlation/seasonality math
# over potentially many candles, so cap request volume per user.
_ANALYTICS_RATE_LIMIT = 60
_ANALYTICS_RATE_WINDOW = 60


async def _analytics_guard(
    user_id: uuid.UUID = Depends(get_current_user_id),
    r: redis.Redis = Depends(get_redis),
) -> uuid.UUID:
    """Require auth and enforce a per-user rate limit for analytics endpoints."""
    try:
        await enforce_rate_limit(
            r, f"analytics:{user_id}", _ANALYTICS_RATE_LIMIT, _ANALYTICS_RATE_WINDOW
        )
    except RateLimitExceeded:
        raise HTTPException(status_code=429, detail="Rate limit exceeded") from None
    return user_id


async def _load_closes(
    session: AsyncSession, instrument_id: int, tf: str, limit: int
) -> pd.DataFrame:
    query = (
        select(CandleRow.ts, CandleRow.c)
        .where(CandleRow.instrument_id == instrument_id, CandleRow.tf == tf)
        .order_by(CandleRow.ts.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = list(reversed(result.all()))
    return pd.DataFrame(
        {"ts": [r.ts for r in rows], "c": [float(r.c) for r in rows]}
    )


async def _load_closes_by_instrument(
    session: AsyncSession, instrument_ids: list[int], tf: str, limit: int
) -> dict[int, pd.DataFrame]:
    """Load the most-recent `limit` closes for EVERY instrument in one query
    (window function), avoiding the per-instrument N+1 of `_load_closes`."""
    if not instrument_ids:
        return {}
    rn = (
        func.row_number()
        .over(partition_by=CandleRow.instrument_id, order_by=CandleRow.ts.desc())
        .label("rn")
    )
    subq = (
        select(CandleRow.instrument_id, CandleRow.ts, CandleRow.c, rn)
        .where(CandleRow.instrument_id.in_(instrument_ids), CandleRow.tf == tf)
        .subquery()
    )
    query = (
        select(subq.c.instrument_id, subq.c.ts, subq.c.c)
        .where(subq.c.rn <= limit)
        .order_by(subq.c.instrument_id, subq.c.ts)
    )
    result = await session.execute(query)
    by_id: dict[int, list[tuple[Any, float]]] = defaultdict(list)
    for iid, ts, c in result.all():
        by_id[iid].append((ts, float(c)))
    return {
        iid: pd.DataFrame({"ts": [t for t, _ in rows], "c": [v for _, v in rows]})
        for iid, rows in by_id.items()
    }


@router.get("/correlation", response_model=CorrelationMatrix)
async def correlation(
    asset_class: str = Query(...),
    tf: str = "1h",
    # Bounded: need >=2 closes per instrument for pct_change; cap matches the
    # seasonality read ceiling so one caller can't request unbounded rows.
    limit: int = Query(200, ge=2, le=5000),
    session: AsyncSession = Depends(get_session),
    _user_id: uuid.UUID = Depends(_analytics_guard),
) -> CorrelationMatrix:
    query = (
        select(Instrument)
        .where(Instrument.asset_class == asset_class, Instrument.active.is_(True))
        .order_by(Instrument.symbol)
    )
    result = await session.execute(query)
    instruments = result.scalars().all()

    closes_by_id = await _load_closes_by_instrument(
        session, [i.id for i in instruments], tf, limit
    )
    returns_by_symbol: dict[str, pd.Series] = {}
    for instrument in instruments:
        closes = closes_by_id.get(instrument.id)
        if closes is None or len(closes) < 2:
            continue
        # Index returns by timestamp so compute_correlation_matrix aligns
        # instruments on the SAME bars, not by position.
        closes_ts = closes.set_index("ts")["c"]
        returns_by_symbol[instrument.symbol] = closes_ts.pct_change().dropna()

    if not returns_by_symbol:
        raise HTTPException(status_code=404, detail="no data for asset_class")

    return compute_correlation_matrix(returns_by_symbol)


@router.get("/seasonality", response_model=Seasonality)
async def seasonality(
    symbol: str = Query(...),
    tf: str = "1h",
    bucket: Literal["dow", "month", "hour"] = "dow",
    session: AsyncSession = Depends(get_session),
    _user_id: uuid.UUID = Depends(_analytics_guard),
) -> Seasonality:
    result = await session.execute(select(Instrument).where(Instrument.symbol == symbol))
    instrument = result.scalars().first()
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")

    closes = await _load_closes(session, instrument.id, tf, 5000)
    if len(closes) < 2:
        raise HTTPException(status_code=404, detail="not enough candle data")

    # NSE equities trade on IST; crypto is a 24/7 UTC convention. Hour-of-day
    # seasonality must bucket in the exchange-local tz.
    tz = "Asia/Kolkata" if instrument.asset_class == "equity" else "UTC"
    return compute_seasonality(closes, bucket=bucket, tz=tz)
