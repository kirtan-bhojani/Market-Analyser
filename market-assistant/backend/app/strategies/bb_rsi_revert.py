"""Bollinger + RSI mean-reversion preset.

Fires a signal when the current bar's close closes outside the Bollinger
Band (below the lower band / above the upper band) confirmed by RSI
oversold/overbought, targeting a reversion back to the middle band (SMA).
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.scanner.indicators import bollinger, rsi
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts
from app.strategies.registry import register


class BollingerRSIRevertStrategy:
    name = "bb_rsi_revert"
    regime_mode = "range"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bb_period": {"type": "integer", "minimum": 5, "default": 20},
                "bb_std": {"type": "number", "minimum": 1.0, "default": 2.0},
                "rsi_oversold": {"type": "number", "default": 30.0},
                "rsi_overbought": {"type": "number", "default": 70.0},
            },
            "required": ["bb_period", "bb_std", "rsi_oversold", "rsi_overbought"],
        }

    def default_params(self) -> dict[str, Any]:
        return {"bb_period": 20, "bb_std": 2.0, "rsi_oversold": 30.0, "rsi_overbought": 70.0}

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        if len(candles) < params["bb_period"] + 1:
            return []

        closes = candles["c"].astype(float).tolist()
        mid, upper, lower = bollinger(
            closes, period=params["bb_period"], std_mult=params["bb_std"]
        )
        rsi_vals = rsi(closes, period=14)

        if (
            math.isnan(lower[-1])
            or math.isnan(upper[-1])
            or math.isnan(mid[-1])
            or math.isnan(rsi_vals[-1])
        ):
            return []

        bar = candles.iloc[-1]
        entry = float(bar["c"])
        ts = candle_ts(candles, len(candles) - 1)

        if entry < lower[-1] and rsi_vals[-1] <= params["rsi_oversold"]:
            # On an extreme bar the close can pierce far below the band, so a
            # band-anchored stop would land ABOVE entry (invalid for a long).
            # Clamp it below entry, keeping a band-width buffer either way.
            buffer = (mid[-1] - lower[-1]) * 0.25
            sl = min(lower[-1] - buffer, entry - buffer)
            return [
                SignalCandidate(
                    ts=ts,
                    direction="long",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=mid[-1],
                    meta={"lower_band": lower[-1], "rsi": rsi_vals[-1]},
                )
            ]
        if entry > upper[-1] and rsi_vals[-1] >= params["rsi_overbought"]:
            # Symmetric clamp: keep the short's stop above entry on extreme bars.
            buffer = (upper[-1] - mid[-1]) * 0.25
            sl = max(upper[-1] + buffer, entry + buffer)
            return [
                SignalCandidate(
                    ts=ts,
                    direction="short",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=mid[-1],
                    meta={"upper_band": upper[-1], "rsi": rsi_vals[-1]},
                )
            ]
        return []


register(BollingerRSIRevertStrategy())
