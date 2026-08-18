import numpy as np
import pandas as pd

from app.backtest.strategies.sma_cross import SmaCrossStrategy


def _sine_candles(n=60, period=20, amplitude=10.0, base=100.0):
    # Deterministic sine wave, 1 point per "bar", no noise, so crossovers
    # are exactly reproducible and hand-verifiable.
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    t = np.arange(n)
    close = base + amplitude * np.sin(2 * np.pi * t / period)
    return pd.DataFrame({"o": close, "h": close, "l": close, "c": close, "v": 1.0}, index=idx)

def test_sma_cross_produces_exact_precomputed_trade_list():
    candles = _sine_candles(n=60, period=20, amplitude=10.0, base=100.0)
    strategy = SmaCrossStrategy()
    signals = strategy.generate_signals(candles, {"fast": 3, "slow": 8})

    fast_sma = candles["c"].rolling(3).mean()
    slow_sma = candles["c"].rolling(8).mean()
    expected_entries = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
    expected_exits = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))
    expected_entries = expected_entries.fillna(False)
    expected_exits = expected_exits.fillna(False)

    assert list(signals["entries"]) == list(expected_entries)
    assert list(signals["exits"]) == list(expected_exits)
    # Sanity: a 20-bar-period sine with 3/8 SMA cross produces multiple
    # non-adjacent crossovers, never simultaneous entry+exit on one bar.
    assert signals["entries"].sum() >= 2
    assert not (signals["entries"] & signals["exits"]).any()
