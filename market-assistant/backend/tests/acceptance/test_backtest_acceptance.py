import time

import numpy as np
import pandas as pd
import pytest

from app.backtest.runner import run_backtest
from app.backtest.serialization import stats_hash
from app.backtest.strategies.sma_cross import SmaCrossStrategy


def _six_months_hourly_btc_like_series():
    # 6 months of hourly bars, deterministic synthetic walk (seeded) so
    # the acceptance test needs no network/data-fixture download and is
    # 100% reproducible across CI runs.
    n = 24 * 30 * 6  # ~4320 bars
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(seed=42)
    steps = rng.normal(loc=0.0, scale=50.0, size=n)
    close = 30_000.0 + np.cumsum(steps)
    close = np.maximum(close, 1_000.0)  # keep price positive
    return pd.DataFrame(
        {"o": close, "h": close * 1.001, "l": close * 0.999, "c": close, "v": 1.0},
        index=idx,
    )


@pytest.mark.acceptance
def test_six_month_btc_1h_sma_cross_completes_under_30s():
    candles = _six_months_hourly_btc_like_series()
    strategy = SmaCrossStrategy()

    start = time.monotonic()
    result = run_backtest(
        strategy=strategy,
        candles=candles,
        params={"fast": 9, "slow": 21},
        fees_bps=10.0,
        slippage_bps=5.0,
    )
    elapsed = time.monotonic() - start

    assert elapsed < 30.0
    assert result.stats["trade_count"] >= 0


@pytest.mark.acceptance
def test_identical_input_produces_identical_stats_hash():
    candles = _six_months_hourly_btc_like_series()
    strategy = SmaCrossStrategy()
    params = {"fast": 9, "slow": 21}

    result_1 = run_backtest(strategy, candles, params, fees_bps=10.0, slippage_bps=5.0)
    result_2 = run_backtest(strategy, candles, params, fees_bps=10.0, slippage_bps=5.0)

    assert stats_hash(result_1.stats) == stats_hash(result_2.stats)
