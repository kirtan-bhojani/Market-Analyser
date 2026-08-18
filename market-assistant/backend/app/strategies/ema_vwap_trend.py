"""EMA(9/21) + VWAP filter trend preset.

Fires a signal on the bar where the fast EMA crosses the slow EMA, confirmed
by the close being on the trend side of the cumulative VWAP (above for
longs, below for shorts).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.scanner.indicators import ema, vwap
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts, latest_session, rr_target, swing_high, swing_low
from app.strategies.registry import register


class EMAVWAPTrendStrategy:
    name = "ema_vwap_trend"
    regime_mode = "trend"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fast": {"type": "integer", "minimum": 2, "default": 9},
                "slow": {"type": "integer", "minimum": 3, "default": 21},
                "swing_lookback": {"type": "integer", "minimum": 3, "default": 10},
                "rr": {"type": "number", "minimum": 0.5, "default": 2.0},
            },
            "required": ["fast", "slow", "swing_lookback", "rr"],
        }

    def default_params(self) -> dict[str, Any]:
        return {"fast": 9, "slow": 21, "swing_lookback": 10, "rr": 2.0}

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        if len(candles) < params["slow"] + 2:
            return []

        closes = candles["c"].astype(float).tolist()

        ema_fast = ema(closes, params["fast"])
        ema_slow = ema(closes, params["slow"])
        # VWAP must reset at the session open — a cumulative VWAP over the whole
        # rolling window anchors to an arbitrary old bar. EMAs are period-decayed
        # averages and stay full-window (see vwap_revert for the same split).
        session = latest_session(candles)
        vw = vwap(
            session["h"].astype(float).tolist(),
            session["l"].astype(float).tolist(),
            session["c"].astype(float).tolist(),
            session["v"].astype(float).tolist(),
        )

        i = len(candles) - 1
        entry = closes[-1]
        ts = candle_ts(candles, i)

        crossed_up = ema_fast[-2] <= ema_slow[-2] and ema_fast[-1] > ema_slow[-1]
        crossed_down = ema_fast[-2] >= ema_slow[-2] and ema_fast[-1] < ema_slow[-1]

        if crossed_up and entry > vw[-1]:
            sl = swing_low(candles, params["swing_lookback"])
            return [
                SignalCandidate(
                    ts=ts,
                    direction="long",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=rr_target(entry, sl, "long", params["rr"]),
                    meta={"vwap": float(vw[-1])},
                )
            ]
        if crossed_down and entry < vw[-1]:
            sl = swing_high(candles, params["swing_lookback"])
            return [
                SignalCandidate(
                    ts=ts,
                    direction="short",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=rr_target(entry, sl, "short", params["rr"]),
                    meta={"vwap": float(vw[-1])},
                )
            ]
        return []


register(EMAVWAPTrendStrategy())
