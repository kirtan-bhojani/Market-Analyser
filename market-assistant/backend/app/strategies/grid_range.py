"""Grid-range preset.

Self-contained range math (no indicators): builds evenly spaced grid levels
across the trailing range and fires a long when the final bar's low touches
the lowest grid line (within tolerance), or a short when its high touches the
highest grid line.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts
from app.strategies.registry import register


class GridRangeStrategy:
    name = "grid_range"
    regime_mode = "range"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "range_lookback": {"type": "integer", "minimum": 10, "default": 20},
                "grid_levels": {"type": "integer", "minimum": 2, "default": 5},
                "touch_tolerance_pct": {"type": "number", "minimum": 0.0, "default": 1.0},
            },
            "required": ["range_lookback", "grid_levels", "touch_tolerance_pct"],
        }

    def default_params(self) -> dict[str, Any]:
        return {"range_lookback": 20, "grid_levels": 5, "touch_tolerance_pct": 1.0}

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        lookback = params["range_lookback"]
        if len(candles) < lookback:
            return []

        window = candles.iloc[-lookback:]
        range_high = float(window["h"].max())
        range_low = float(window["l"].min())
        if range_high == range_low:
            return []

        levels = [
            range_low + (range_high - range_low) * i / params["grid_levels"]
            for i in range(params["grid_levels"] + 1)
        ]
        bar = candles.iloc[-1]
        entry = float(bar["c"])
        tolerance = (range_high - range_low) * (params["touch_tolerance_pct"] / 100.0)
        ts = candle_ts(candles, len(candles) - 1)

        lowest_level, highest_level = levels[0], levels[-1]

        if bar["l"] <= lowest_level + tolerance:
            next_level_up = levels[1]
            # The close can sit ABOVE the next grid line, which would put the
            # long's TP below entry -> the backtester scores it as an instant
            # win. Only emit when the target is genuinely above entry.
            if next_level_up <= entry:
                return []
            return [
                SignalCandidate(
                    ts=ts,
                    direction="long",
                    ref_entry=entry,
                    ref_sl=range_low - tolerance,
                    ref_tp=next_level_up,
                    meta={"grid_levels": levels},
                )
            ]
        if bar["h"] >= highest_level - tolerance:
            next_level_down = levels[-2]
            # Symmetric guard: skip if the close is already below the next grid
            # line down, which would leave the short's TP above entry.
            if next_level_down >= entry:
                return []
            return [
                SignalCandidate(
                    ts=ts,
                    direction="short",
                    ref_entry=entry,
                    ref_sl=range_high + tolerance,
                    ref_tp=next_level_down,
                    meta={"grid_levels": levels},
                )
            ]
        return []


register(GridRangeStrategy())
