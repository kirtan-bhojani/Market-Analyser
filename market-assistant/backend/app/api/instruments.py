import uuid
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.config import get_settings
from app.core.deps import get_session
from app.ingest.universe_equity import ensure_equity_instruments
from app.models.instrument import Instrument
from app.schemas.instrument import AssetClass, InstrumentIn, InstrumentOut, InstrumentPatch

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


def _to_out(instrument: Instrument) -> InstrumentOut:
    settings = get_settings()
    is_delayed = instrument.asset_class == "equity"
    return InstrumentOut(
        id=instrument.id,
        symbol=instrument.symbol,
        asset_class=cast(AssetClass, instrument.asset_class),
        exchange=instrument.exchange,
        active=instrument.active,
        delayed=is_delayed,
        delay_minutes=settings.EQUITY_DELAY_MINUTES if is_delayed else 0,
    )


@router.get("", response_model=list[InstrumentOut])
async def list_instruments(
    asset_class: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[InstrumentOut]:
    query = select(Instrument)
    if asset_class:
        query = query.where(Instrument.asset_class == asset_class)
    result = await session.execute(query)
    return [_to_out(i) for i in result.scalars().all()]


@router.post("", response_model=InstrumentOut, status_code=201)
async def create_instrument(
    payload: InstrumentIn,
    session: AsyncSession = Depends(get_session),
    _user_id: uuid.UUID = Depends(require_admin),
) -> InstrumentOut:
    instrument = Instrument(
        symbol=payload.symbol,
        asset_class=payload.asset_class,
        exchange=payload.exchange,
        active=True,
    )
    session.add(instrument)
    await session.commit()
    await session.refresh(instrument)
    return _to_out(instrument)


@router.post("/seed-nifty50", response_model=list[InstrumentOut], status_code=201)
async def seed_nifty50(
    session: AsyncSession = Depends(get_session),
    _user_id: uuid.UUID = Depends(require_admin),
) -> list[InstrumentOut]:
    instruments = await ensure_equity_instruments(session)
    await session.commit()
    for instrument in instruments:
        await session.refresh(instrument)
    return [_to_out(i) for i in instruments]


@router.patch("/{instrument_id}", response_model=InstrumentOut)
async def patch_instrument(
    instrument_id: int,
    payload: InstrumentPatch,
    session: AsyncSession = Depends(get_session),
    _user_id: uuid.UUID = Depends(require_admin),
) -> InstrumentOut:
    instrument = await session.get(Instrument, instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    if payload.active is not None:
        instrument.active = payload.active
    await session.commit()
    await session.refresh(instrument)
    return _to_out(instrument)
