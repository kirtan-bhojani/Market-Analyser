from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Minimum mini-backtest window per timeframe = bars in one NSE cash session
# (375 min: 09:15-15:30 IST). Guarantees session-anchored presets see a full
# opening range / VWAP reset. 1d uses a warmup-sized floor (one bar == one
# session, but ATR/RSI-14 need history).
_MIN_WINDOW_BY_TF = {"1m": 375, "5m": 75, "15m": 25, "1h": 7, "1d": 20}
_DEFAULT_MIN_WINDOW = 20


class StrategyMeta(BaseModel):
    name: str
    label: str
    regime_mode: str  # "trend" | "range" | "any"
    param_schema: dict[str, Any]
    default_params: dict[str, Any]


class StrategyConfigIn(BaseModel):
    strategy: str
    instrument_id: int
    tf: str
    params: dict[str, Any]
    enabled: bool = True


class StrategyConfigOut(StrategyConfigIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instrument_id: int | None
    strategy: str
    direction: str
    ts: str
    confidence: float | None
    ref_entry: float | None
    ref_sl: float | None
    ref_tp: float | None
    backtest_ref: str | None
    meta: dict[str, Any] | None

    @field_validator("ts", mode="before")
    @classmethod
    def _coerce_ts(cls, value: Any) -> Any:
        # ORM Signal.ts is a datetime (TIMESTAMPTZ) but the wire shape is an ISO
        # string; coerce so returning an ORM object via response_model serializes.
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_validator("backtest_ref", mode="before")
    @classmethod
    def _coerce_backtest_ref(cls, value: Any) -> Any:
        # ORM Signal.backtest_ref is a UUID; the wire shape is a string.
        if value is None:
            return None
        return str(value)


class MiniBacktestRequest(BaseModel):
    instrument_id: int
    tf: str
    params: dict[str, Any] | None = None
    fees_bps: int = 10
    slippage_bps: int = 5
    # Rolling lookback the preset's generate_signals sees per bar. Floored per
    # timeframe (see _floor_window_to_session) so the window always spans at
    # least one full trading session: session-anchored presets (ORB opening
    # range, VWAP reset) need the true session open, not the oldest bar of a
    # too-short window. A 1m NSE session is 375 bars, so the old ge=20 floor
    # silently fabricated the opening range / VWAP anchor.
    window: int = Field(default=60, ge=1, le=2000)

    @model_validator(mode="after")
    def _floor_window_to_session(self) -> "MiniBacktestRequest":
        floor = _MIN_WINDOW_BY_TF.get(self.tf, _DEFAULT_MIN_WINDOW)
        if self.window < floor:
            self.window = floor
        return self


class MiniBacktestResponse(BaseModel):
    stats: dict[str, float]
    n_candles: int
