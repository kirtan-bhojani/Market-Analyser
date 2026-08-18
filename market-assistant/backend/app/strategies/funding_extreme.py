"""Funding-rate extreme preset (crypto only).

Bidirectional mean-reversion on a `funding_rate` column: crowded longs
(funding spikes positive) mean-revert short; crowded shorts (funding spikes
negative) mean-revert long. Requires a `funding_rate` column populated
upstream by a Binance funding-rate poller (out of scope here); test
fixtures inject the column directly. `asset_class_filter = "crypto"` is
checked by the scan worker so this preset never runs against equities.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts
from app.strategies.registry import register


class FundingExtremeStrategy:
    name = "funding_extreme"
    regime_mode = "any"
    asset_class_filter = "crypto"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "extreme_positive": {"type": "number", "default": 0.0025},
                "extreme_negative": {"type": "number", "default": -0.0025},
                "sl_pct": {"type": "number", "minimum": 0.1, "default": 2.0},
                "tp_pct": {"type": "number", "minimum": 0.1, "default": 3.0},
            },
            "required": ["extreme_positive", "extreme_negative", "sl_pct", "tp_pct"],
        }

    def default_params(self) -> dict[str, Any]:
        return {
            "extreme_positive": 0.0025,
            "extreme_negative": -0.0025,
            "sl_pct": 2.0,
            "tp_pct": 3.0,
        }

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        if "funding_rate" not in candles.columns or candles.empty:
            return []

        bar = candles.iloc[-1]
        rate = bar["funding_rate"]
        entry = float(bar["c"])
        ts = candle_ts(candles, len(candles) - 1)

        if rate >= params["extreme_positive"]:
            return [
                SignalCandidate(
                    ts=ts,
                    direction="short",
                    ref_entry=entry,
                    ref_sl=entry * (1 + params["sl_pct"] / 100.0),
                    ref_tp=entry * (1 - params["tp_pct"] / 100.0),
                    meta={"funding_rate": float(rate)},
                )
            ]
        if rate <= params["extreme_negative"]:
            return [
                SignalCandidate(
                    ts=ts,
                    direction="long",
                    ref_entry=entry,
                    ref_sl=entry * (1 - params["sl_pct"] / 100.0),
                    ref_tp=entry * (1 + params["tp_pct"] / 100.0),
                    meta={"funding_rate": float(rate)},
                )
            ]
        return []


register(FundingExtremeStrategy())
