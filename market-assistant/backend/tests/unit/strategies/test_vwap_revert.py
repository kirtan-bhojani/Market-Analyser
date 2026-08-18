import pandas as pd
import pytest

from app.strategies.vwap_revert import VWAPRevertStrategy


def _bar(
    ts: str, o: float, h: float, l: float, c: float, v: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": pd.Timestamp(ts), "o": o, "h": h, "l": l, "c": c, "v": v}


def test_vwap_revert_golden_oversold_fires_one_long_signal():
    # Flat-ish series around 100 to build a tight VWAP/std, then one bar
    # that spikes 5 stdevs below VWAP with RSI already oversold.
    bars = [
        _bar(f"2024-01-01T{9+i//4:02d}:{(i%4)*15:02d}", 100, 100.5, 99.5, 100, 500)
        for i in range(20)
    ]
    bars.append(_bar("2024-01-01T14:15", 100, 100, 90, 91, 500))
    candles = pd.DataFrame(bars)
    strat = VWAPRevertStrategy()
    signals = strat.generate_signals(candles, strat.default_params())

    assert len(signals) == 1
    sig = signals[0]
    assert sig.direction == "long"
    assert sig.ref_entry == 91
    assert sig.ref_tp == pytest.approx(sig.meta["vwap"], abs=0.5)


def test_vwap_revert_negative_small_deviation_fires_nothing():
    # Realistic dispersion: ~24 bars with small alternating up/down moves
    # around 100 (so real RSI sits comfortably above rsi_oversold=35, NOT
    # collapsed to 0, and the expanding std reflects normal noise), then a
    # final bar closing only slightly below VWAP so its z-score is well under
    # std_k=3.0. Both gate conditions fail -> no signal. (Measured on the real
    # indicators: last-bar RSI ~= 38.4 > 35, deviation z-score ~= -1.21.)
    bars = []
    for i in range(24):
        c = 100.5 if i % 2 == 0 else 99.5
        bars.append(_bar(f"2024-01-01T{9+i//4:02d}:{(i%4)*15:02d}", c, c + 0.3, c - 0.3, c, 500))
    bars.append(_bar("2024-01-01T15:15", 99.4, 99.7, 99.1, 99.4, 500))
    candles = pd.DataFrame(bars)
    strat = VWAPRevertStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
