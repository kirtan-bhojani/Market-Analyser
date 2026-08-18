"""TEST-ONLY HTTP routes for driving E2E scenarios over the wire.

This router is mounted by ``app.main.create_app`` ONLY when
``settings.env == "test"`` and must NEVER be reachable in production. It exposes
the same synthetic-candle replay logic the backend acceptance test uses (see
``tests/conftest.py::replay_synthetic_candles``) so the Playwright spec can
trigger a scanner hit via a plain HTTP POST.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_redis, get_session
from app.models.candle import CandleRow
from app.scanner.worker import on_candle_close

router = APIRouter(prefix="/test", tags=["test-only"])


class ReplayRequest(BaseModel):
    scenario: str
    instrument_id: int
    tf: str = "5m"


def _rsi_dip_with_volume_spike_series() -> tuple[list[float], list[float]]:
    closes = [100.0] * 40 + [100.0 - i * (30.0 / 14) for i in range(15)]
    volumes = [20.0] * 55
    volumes[50] = 200.0
    return closes, volumes


@router.post("/replay-synthetic-candles")
async def replay_synthetic_candles(
    body: ReplayRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, int]:
    if body.scenario != "rsi_dip_with_volume_spike":
        raise HTTPException(status_code=400, detail=f"unknown scenario {body.scenario!r}")
    closes, volumes = _rsi_dip_with_volume_spike_series()
    hits = 0
    for i, (c, v) in enumerate(zip(closes, volumes, strict=True)):
        ts = f"2026-01-01T00:{i:02d}:00Z"
        candle = {"ts": ts, "o": c - 0.1, "h": c + 0.5, "l": c - 0.5, "c": c, "v": v}
        # process bar i against persisted history 0..i-1, then persist bar i so
        # the next bar's warm-start (which reads history from the DB) sees it.
        hits += await on_candle_close(
            {"db": session, "redis": redis},
            instrument_id=body.instrument_id,
            tf=body.tf,
            candle=candle,
        )
        session.add(
            CandleRow(
                instrument_id=body.instrument_id,
                tf=body.tf,
                ts=datetime.fromisoformat(ts.replace("Z", "+00:00")),
                o=c - 0.1,
                h=c + 0.5,
                l=c - 0.5,
                c=c,
                v=v,
            )
        )
        await session.commit()
    return {"hits": hits}
