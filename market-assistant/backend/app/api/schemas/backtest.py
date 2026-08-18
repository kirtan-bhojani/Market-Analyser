import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings


class BacktestCreateRequest(BaseModel):
    strategy: str
    params: dict[str, Any]
    universe: dict[str, Any]
    start_ts: datetime
    end_ts: datetime
    fees_bps: float = Field(..., gt=0, description="Trading fee in bps; must be > 0")
    slippage_bps: float = Field(..., gt=0, description="Slippage in bps; must be > 0")

    @model_validator(mode="after")
    def _validate_window_and_universe(self) -> "BacktestCreateRequest":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be after start_ts")
        settings = get_settings()
        span_days = (self.end_ts - self.start_ts).days
        if span_days > settings.max_backtest_span_days:
            raise ValueError(
                f"backtest span {span_days}d exceeds max {settings.max_backtest_span_days}d"
            )
        # Universe may be a single {"symbol", "tf"} or carry a "symbols" list;
        # cap the number of symbols so a request can't fan out unbounded work.
        symbols = self.universe.get("symbols")
        count = len(symbols) if isinstance(symbols, list) else 1
        if count > settings.max_universe_size:
            raise ValueError(
                f"universe size {count} exceeds max {settings.max_universe_size}"
            )
        return self


class BacktestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    stats: dict[str, Any] | None = None
    equity_curve: list[dict[str, Any]] | None = None
