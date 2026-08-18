"""Pullback-in-trend preset.

Requires the close to be above a slow trend EMA (uptrend context), a recent
pullback to within tolerance of a faster EMA, and a bullish reversal bar
closing back above the prior bar's high before firing a long signal.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.scanner.indicators import ema
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts, rr_target, swing_low
from app.strategies.registry import register


class PullbackTrendStrategy:
    name = "pullback_trend"
    regime_mode = "trend"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "trend_ema": {"type": "integer", "minimum": 10, "default": 50},
                "pullback_ema": {"type": "integer", "minimum": 5, "default": 21},
                "pullback_tolerance_pct": {"type": "number", "minimum": 0.0, "default": 1.5},
                "sl_lookback": {"type": "integer", "minimum": 3, "default": 5},
                "rr": {"type": "number", "minimum": 0.5, "default": 2.0},
            },
            "required": [
                "trend_ema",
                "pullback_ema",
                "pullback_tolerance_pct",
                "sl_lookback",
                "rr",
            ],
        }

    def default_params(self) -> dict[str, Any]:
        return {
            "trend_ema": 50,
            "pullback_ema": 21,
            "pullback_tolerance_pct": 1.5,
            "sl_lookback": 5,
            "rr": 2.0,
        }

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        if len(candles) < params["trend_ema"] + 2:
            return []

        closes = candles["c"].astype(float).tolist()
        trend_ma = ema(closes, params["trend_ema"])
        pullback_ma = ema(closes, params["pullback_ema"])

        if math.isnan(trend_ma[-1]) or math.isnan(pullback_ma[-2]):
            return []

        bar = candles.iloc[-1]
        prior = candles.iloc[-2]

        in_uptrend = bar["c"] > trend_ma[-1]
        tolerance = pullback_ma[-2] * (params["pullback_tolerance_pct"] / 100.0)
        # A pullback is the low returning to WITHIN a tolerance band of the
        # pullback EMA. The old `or prior["l"] <= ma + tol` clause subsumed the
        # band and dropped the lower floor, so a deep breakdown far below the
        # EMA counted as a pullback. Keep only the abs-distance band.
        pulled_back = abs(prior["l"] - pullback_ma[-2]) <= tolerance
        reversal_bar = bar["c"] > bar["o"] and bar["c"] > prior["c"]

        if in_uptrend and pulled_back and reversal_bar:
            entry = float(bar["c"])
            sl = swing_low(candles, params["sl_lookback"])
            return [
                SignalCandidate(
                    ts=candle_ts(candles, len(candles) - 1),
                    direction="long",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=rr_target(entry, sl, "long", params["rr"]),
                    meta={
                        "trend_ema": float(trend_ma[-1]),
                        "pullback_ema": float(pullback_ma[-1]),
                    },
                )
            ]
        return []


register(PullbackTrendStrategy())
