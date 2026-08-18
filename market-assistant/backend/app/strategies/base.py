from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass
class SignalCandidate:
    ts: pd.Timestamp
    direction: str  # "long" | "short"
    ref_entry: float
    ref_sl: float
    ref_tp: float
    confidence: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Strategy(Protocol):
    name: str
    regime_mode: str  # "trend" | "range" | "any"

    def param_schema(self) -> dict[str, Any]: ...
    def default_params(self) -> dict[str, Any]: ...
    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]: ...
