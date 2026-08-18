"""Breakout-retest preset.

Finds the highest high over the trailing `level_lookback` bars ("resistance"),
watches for the first subsequent bar that closes above it on confirming
relative volume (`app.scanner.indicators.rel_volume`), then checks whether the
very next bar retests that level (holds within `retest_tolerance_pct` of it)
and closes back above it. A held-and-confirmed retest fires a single long
signal with the broken resistance acting as the new stop-loss (support).
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.scanner.indicators import rel_volume
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts, latest_session, rr_target
from app.strategies.registry import register


class BreakoutRetestStrategy:
    name = "breakout_retest"
    regime_mode = "trend"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "level_lookback": {"type": "integer", "minimum": 5, "default": 10},
                "min_rel_volume": {"type": "number", "minimum": 1.0, "default": 2.0},
                "retest_tolerance_pct": {"type": "number", "minimum": 0.0, "default": 0.5},
                "rr": {"type": "number", "minimum": 0.5, "default": 2.0},
            },
            "required": ["level_lookback", "min_rel_volume", "retest_tolerance_pct", "rr"],
        }

    def default_params(self) -> dict[str, Any]:
        return {
            "level_lookback": 10,
            "min_rel_volume": 2.0,
            "retest_tolerance_pct": 0.5,
            "rr": 2.0,
        }

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        lookback = params["level_lookback"]
        # Anchor resistance to the trailing/latest session, not the oldest bars
        # of an arbitrary rolling window — otherwise the live worker re-emits the
        # same ancient breakout every bar (mirrors orb.py's session anchoring).
        session = latest_session(candles)
        if len(session) < lookback + 2:
            return []

        pre_breakout = session.iloc[:lookback]
        resistance = float(pre_breakout["h"].max())

        vols = session["v"].astype(float).tolist()
        rv = rel_volume(vols, period=lookback)
        tolerance = resistance * (params["retest_tolerance_pct"] / 100.0)

        # Scan backwards for the MOST RECENT breakout whose next bar is a held,
        # confirmed retest — not the oldest — so the emitted signal tracks the
        # current setup rather than replaying stale history.
        for i in range(len(session) - 2, lookback - 1, -1):
            if math.isnan(rv[i]):
                continue
            bar = session.iloc[i]
            if not (bar["c"] > resistance and rv[i] >= params["min_rel_volume"]):
                continue
            retest = session.iloc[i + 1]
            held_level = retest["l"] >= resistance - tolerance
            closed_up = retest["c"] > resistance
            if held_level and closed_up:
                entry = float(retest["c"])
                return [
                    SignalCandidate(
                        ts=candle_ts(session, i + 1),
                        direction="long",
                        ref_entry=entry,
                        ref_sl=resistance,
                        ref_tp=rr_target(entry, resistance, "long", params["rr"]),
                        meta={"resistance": resistance},
                    )
                ]
        return []


register(BreakoutRetestStrategy())
