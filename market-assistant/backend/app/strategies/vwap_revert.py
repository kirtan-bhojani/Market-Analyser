"""VWAP mean-revert preset.

Fires a signal when the current bar's close deviates by at least `std_k`
expanding-window standard deviations from the cumulative VWAP, confirmed by
RSI oversold/overbought, targeting a reversion back to VWAP.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.scanner.indicators import atr, rsi, vwap
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts, latest_session
from app.strategies.registry import register


class VWAPRevertStrategy:
    name = "vwap_revert"
    regime_mode = "range"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "std_k": {"type": "number", "minimum": 1.0, "default": 3.0},
                "rsi_oversold": {"type": "number", "default": 35.0},
                "rsi_overbought": {"type": "number", "default": 65.0},
                "sl_atr_mult": {"type": "number", "minimum": 0.1, "default": 1.5},
            },
            "required": ["std_k", "rsi_oversold", "rsi_overbought", "sl_atr_mult"],
        }

    def default_params(self) -> dict[str, Any]:
        return {"std_k": 3.0, "rsi_oversold": 35.0, "rsi_overbought": 65.0, "sl_atr_mult": 1.5}

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        highs = candles["h"].astype(float).tolist()
        lows = candles["l"].astype(float).tolist()
        closes = candles["c"].astype(float).tolist()

        # VWAP (and the deviation std it feeds) MUST reset at the session open;
        # a cumulative VWAP over an arbitrary rolling window anchors to the
        # window's oldest bar and fabricates the reversion reference. RSI/ATR are
        # period-based indicators and are computed over the full window as usual.
        session = latest_session(candles)
        s_high = session["h"].astype(float).tolist()
        s_low = session["l"].astype(float).tolist()
        s_close = session["c"].astype(float).tolist()
        s_vol = session["v"].astype(float).tolist()
        sv = vwap(s_high, s_low, s_close, s_vol)

        rsi_vals = rsi(closes, period=14)
        atr_vals = atr(highs, lows, closes, period=14) if len(closes) >= 14 else None

        deviation = pd.Series([c - v for c, v in zip(s_close, sv)])
        std = deviation.expanding(min_periods=5).std()

        i = len(candles) - 1  # full-window index (RSI/ATR); last bar is the session's last
        dev = deviation.iloc[-1]
        sd = std.iloc[-1]
        vwap_now = sv[-1]
        if sd == 0 or pd.isna(sd) or pd.isna(vwap_now):
            return []

        rsi_last = rsi_vals[i]
        if pd.isna(rsi_last):
            return []

        bar = candles.iloc[-1]
        entry = float(bar["c"])
        a = float(atr_vals[i]) if atr_vals is not None and not pd.isna(atr_vals[i]) else 0.0
        ts = candle_ts(candles, i)
        vwap_now = float(vwap_now)

        if dev <= -params["std_k"] * sd and rsi_last <= params["rsi_oversold"]:
            sl = entry - a * params["sl_atr_mult"]
            return [
                SignalCandidate(
                    ts=ts,
                    direction="long",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=vwap_now,
                    meta={"vwap": vwap_now, "deviation_std": float(dev / sd)},
                )
            ]
        if dev >= params["std_k"] * sd and rsi_last >= params["rsi_overbought"]:
            sl = entry + a * params["sl_atr_mult"]
            return [
                SignalCandidate(
                    ts=ts,
                    direction="short",
                    ref_entry=entry,
                    ref_sl=sl,
                    ref_tp=vwap_now,
                    meta={"vwap": vwap_now, "deviation_std": float(dev / sd)},
                )
            ]
        return []


register(VWAPRevertStrategy())
