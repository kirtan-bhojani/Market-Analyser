import numpy as np
import pandas as pd
import pytest

from app.backtest.runner import run_backtest
from app.backtest.strategies.sma_cross import SmaCrossStrategy


def _sine_candles(n=120, period=20, amplitude=10.0, base=100.0):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    t = np.arange(n)
    close = base + amplitude * np.sin(2 * np.pi * t / period)
    return pd.DataFrame({"o": close, "h": close, "l": close, "c": close, "v": 1.0}, index=idx)


def test_runner_produces_equity_curve_and_stats_with_costs_applied():
    candles = _sine_candles()
    strategy = SmaCrossStrategy()
    params = {"fast": 3, "slow": 8}

    result = run_backtest(
        strategy=strategy,
        candles=candles,
        params=params,
        fees_bps=10.0,
        slippage_bps=5.0,
        init_cash=10_000.0,
    )

    assert len(result.equity_curve) == len(candles)
    assert result.equity_curve.iloc[0] == pytest.approx(10_000.0, rel=1e-6)
    assert result.stats["trade_count"] == len(result.trades)
    assert result.stats["trade_count"] > 0
    # Costs strictly reduce a trade's PnL vs. a zero-cost baseline unless
    # the trade is a scratch; with 10bps fee + 5bps slippage round-trip,
    # every closed trade must show non-zero fees_paid.
    assert all(t.fees_paid > 0 for t in result.trades)
