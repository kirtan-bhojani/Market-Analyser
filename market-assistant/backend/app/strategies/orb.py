"""Opening Range Breakout (ORB) preset.

Defines an "opening range" from the first `or_bars` bars of the *most recent
UTC-day session* present in the candles handed to `generate_signals` and fires
a long/short signal on the first subsequent bar in that session that closes
outside the range on confirming relative volume
(`app.scanner.indicators.rel_volume`).

Session-anchoring matters because the live worker re-feeds a long rolling
window (~500 bars ≈ several days) on every candle close. Anchoring the opening
range to the window's oldest bars would fix it to a session days in the past
and emit a single ancient breakout that the per-bar dedup then suppresses
forever -- today's breakout would never surface. Anchoring to the latest
session yields today's opening range and today's breakout, and resets cleanly
each UTC day.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.scanner.indicators import rel_volume
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts, latest_session, rr_target
from app.strategies.registry import register


class ORBStrategy:
    name = "orb"
    regime_mode = "trend"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "or_bars": {"type": "integer", "minimum": 1, "default": 4},
                "rr": {"type": "number", "minimum": 0.5, "default": 2.0},
                "min_rel_volume": {"type": "number", "minimum": 1.0, "default": 2.0},
            },
            "required": ["or_bars", "rr", "min_rel_volume"],
        }

    def default_params(self) -> dict[str, Any]:
        return {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0}

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        or_bars = params["or_bars"]
        rr = params["rr"]
        min_rel_vol = params["min_rel_volume"]

        if len(candles) <= or_bars:
            return []

        session = latest_session(candles)
        if len(session) <= or_bars:
            return []

        opening_range = session.iloc[:or_bars]
        or_high = float(opening_range["h"].max())
        or_low = float(opening_range["l"].min())

        rv = rel_volume(session["v"].astype(float).tolist(), period=or_bars)
        signals: list[SignalCandidate] = []

        for i in range(or_bars, len(session)):
            bar = session.iloc[i]
            bar_rel_vol = rv[i]
            if bar_rel_vol != bar_rel_vol:  # NaN check without importing math
                continue
            if bar["c"] > or_high and bar_rel_vol >= min_rel_vol:
                entry = float(bar["c"])
                signals.append(
                    SignalCandidate(
                        ts=candle_ts(session, i),
                        direction="long",
                        ref_entry=entry,
                        ref_sl=or_low,
                        ref_tp=rr_target(entry, or_low, "long", rr),
                        meta={"or_high": or_high, "or_low": or_low, "rel_volume": bar_rel_vol},
                    )
                )
                break
            if bar["c"] < or_low and bar_rel_vol >= min_rel_vol:
                entry = float(bar["c"])
                signals.append(
                    SignalCandidate(
                        ts=candle_ts(session, i),
                        direction="short",
                        ref_entry=entry,
                        ref_sl=or_high,
                        ref_tp=rr_target(entry, or_high, "short", rr),
                        meta={"or_high": or_high, "or_low": or_low, "rel_volume": bar_rel_vol},
                    )
                )
                break

        return signals


register(ORBStrategy())
