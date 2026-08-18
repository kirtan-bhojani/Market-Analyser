from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Timeframe(StrEnum):
    m1 = "1m"
    m5 = "5m"
    m15 = "15m"
    h1 = "1h"
    d1 = "1d"


class CandleOut(BaseModel):
    ts: datetime
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    v: float

    model_config = {"from_attributes": True}


class CandlesResponse(BaseModel):
    candles: list[CandleOut]
    delayed: bool
    delay_minutes: int
