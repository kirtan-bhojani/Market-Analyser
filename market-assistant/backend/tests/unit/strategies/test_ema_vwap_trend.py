"""Golden/negative coverage for the EMA(9/21)+VWAP-filter trend preset.

The brief's original fixture (a single monotonic rising series) never
produces an actual fast/slow EMA cross at the last bar: once both EMAs are
defined, the fast EMA sits above the slow EMA for the *entire* series (a
straight line's trailing 9-bar average is always above its trailing 21-bar
average), so `crossed_up` is False throughout and no signal ever fires.

Measured (see task-6 report): for the brief's `_rising_series(30)`,
`ema_fast[-2:] = [101.25, 101.30]`, `ema_slow[-2:] = [100.95, 101.00]` —
fast is already above slow at bar -2, so there is no cross at bar -1.

Fixed by building a down-then-up series so the fast EMA dips below the slow
EMA during the decline and crosses back above it exactly at the last bar.
The negative fixture reuses the identical price/EMA path (so the cross
state is unchanged) and only perturbs the last bar's high/low/volume to
drag the cumulative VWAP above the close, genuinely exercising the VWAP
veto instead of the brief's unsatisfiable "subtract a constant from close"
approach (which also unavoidably shifts the EMA cross and breaks it, as
verified empirically).
"""

from __future__ import annotations

import pandas as pd

from app.strategies.ema_vwap_trend import EMAVWAPTrendStrategy


def _bar(ts: str, o: float, h: float, lo: float, c: float, v: float) -> dict:
    return {"ts": pd.Timestamp(ts), "o": o, "h": h, "l": lo, "c": c, "v": v}


def _down_then_up_series(
    n_down: int = 20, n_up: int = 12, start: float = 100.0, step: float = 0.3
) -> list[dict]:
    prices = []
    price = start
    for _ in range(n_down):
        price -= step
        prices.append(price)
    for _ in range(n_up):
        price += step
        prices.append(price)

    bars = []
    for i, price in enumerate(prices):
        ts = f"2024-01-01T{9 + i // 4:02d}:{(i % 4) * 15:02d}"
        bars.append(_bar(ts, price - 0.05, price + 0.2, price - 0.2, price, 800))
    return bars


def test_ema_vwap_trend_golden_bullish_cross_above_vwap_fires_long() -> None:
    # Measured: ema_fast[-2:]=[..., 97.35...], ema_slow[-2:]=[..., 97.28...]
    # crossed_up=True (fast dips below slow through the decline, crosses back
    # above at the last bar); close=97.6 > vw[-1]=96.51 -> long fires.
    candles = pd.DataFrame(_down_then_up_series())
    strat = EMAVWAPTrendStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert len(signals) == 1
    assert signals[0].direction == "long"
    assert signals[0].ref_entry == candles.iloc[-1]["c"]


def test_ema_vwap_trend_negative_cross_below_vwap_fires_nothing() -> None:
    # Same EMA path as the golden case (crossed_up still True at the last
    # bar) but the last bar's high/low/volume are pumped so the cumulative
    # VWAP (which only depends on h/l/c/v, not the EMA closes) jumps well
    # above the close: vw[-1] ~= 120.6 > close=97.6 -> VWAP filter vetoes
    # the long and no signal fires.
    bars = _down_then_up_series()
    candles = pd.DataFrame(bars)
    last_idx = candles.index[-1]
    candles.loc[last_idx, "h"] = 150.0
    candles.loc[last_idx, "l"] = 150.0
    candles.loc[last_idx, "v"] = 50_000.0

    strat = EMAVWAPTrendStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
