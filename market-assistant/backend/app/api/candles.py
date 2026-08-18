from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.candles import CandleOut, CandlesResponse, Timeframe
from app.core.config import get_settings
from app.core.deps import get_session
from app.models.candle import CandleRow
from app.models.instrument import Instrument

router = APIRouter(tags=["candles"])


@router.get("/candles", response_model=CandlesResponse)
async def get_candles(
    symbol: str,
    tf: Timeframe,
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> CandlesResponse:
    instrument = (
        await session.execute(select(Instrument).where(Instrument.symbol == symbol))
    ).scalars().first()
    if instrument is None:
        return CandlesResponse(candles=[], delayed=False, delay_minutes=0)

    stmt = (
        select(CandleRow)
        .where(
            CandleRow.instrument_id == instrument.id,
            CandleRow.tf == tf.value,
            CandleRow.ts >= from_,
            CandleRow.ts <= to,
        )
        .order_by(CandleRow.ts.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()

    settings = get_settings()
    is_delayed = instrument.asset_class == "equity"
    delay_minutes = settings.EQUITY_DELAY_MINUTES if is_delayed else 0

    return CandlesResponse(
        candles=[CandleOut.model_validate(row) for row in rows],
        delayed=is_delayed,
        delay_minutes=delay_minutes,
    )
