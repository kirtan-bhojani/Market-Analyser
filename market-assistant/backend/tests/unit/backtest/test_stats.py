import math

import pandas as pd
import pytest

from app.backtest.costs import TradeCosts
from app.backtest.stats import compute_stats


def test_stats_match_hand_calculation_on_fixture_curve():
    # Equity curve: start at 100, then +10, -5, +8, -3, +2 (5 daily steps).
    equity = pd.Series([100.0, 110.0, 105.0, 113.0, 110.0, 112.0])
    returns = equity.pct_change().dropna()
    # returns = [0.10, -0.045454545..., 0.076190476..., -0.026548672..., 0.018181818...]
    mean_r = returns.mean()
    std_r = returns.std(ddof=1)
    # Daily equity bars -> 252 periods/year (annualization now derives from tf).
    expected_sharpe = (mean_r / std_r) * math.sqrt(252)

    # Max drawdown: running max = [100,110,110,113,113,113]
    # drawdown = equity/running_max - 1 = [0, 0, -0.045454545, 0, -0.026548672, -0.008849558]
    expected_max_dd = -0.045454545454545456

    trades = [
        TradeCosts(gross_pnl=10.0, fees_paid=1.0, slippage_paid=0.5, net_pnl=9.0),
        TradeCosts(gross_pnl=-6.0, fees_paid=1.0, slippage_paid=0.5, net_pnl=-7.0),
        TradeCosts(gross_pnl=9.0, fees_paid=1.0, slippage_paid=0.5, net_pnl=8.0),
        TradeCosts(gross_pnl=-2.0, fees_paid=1.0, slippage_paid=0.5, net_pnl=-3.0),
        TradeCosts(gross_pnl=3.0, fees_paid=1.0, slippage_paid=0.5, net_pnl=2.0),
    ]
    # win_rate = 3 wins / 5 trades = 0.6
    # net_return = (112 - 100) / 100 = 0.12

    stats = compute_stats(equity, trades, timeframe="1d", asset_class="equity")

    assert stats["sharpe"] == pytest.approx(expected_sharpe, rel=1e-9)
    assert stats["max_dd"] == pytest.approx(expected_max_dd, rel=1e-9)
    assert stats["win_rate"] == pytest.approx(0.6, rel=1e-9)
    assert stats["net_return"] == pytest.approx(0.12, rel=1e-9)
    assert stats["trade_count"] == 5
