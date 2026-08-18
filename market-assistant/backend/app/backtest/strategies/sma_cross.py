from typing import Any

import pandas as pd


class SmaCrossStrategy:
    """Fast/slow SMA crossover: enter long on fast-crosses-above-slow,
    exit on fast-crosses-below-slow. `params` requires 'fast' and 'slow'
    window lengths (int, fast < slow)."""

    def generate_signals(self, candles: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        fast_window = int(params["fast"])
        slow_window = int(params["slow"])
        if fast_window >= slow_window:
            raise ValueError("fast window must be < slow window")

        close = candles["c"]
        fast_sma = close.rolling(fast_window).mean()
        slow_sma = close.rolling(slow_window).mean()

        crossed_above = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
        crossed_below = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))

        entries = crossed_above.fillna(False)
        exits = crossed_below.fillna(False)

        return pd.DataFrame({"entries": entries, "exits": exits}, index=candles.index)
