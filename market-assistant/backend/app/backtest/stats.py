import math
from typing import Any

import pandas as pd

from app.backtest.costs import TradeCosts

# Legacy alias: annualization must derive from the bar size, not a fixed daily
# constant. Kept only so old imports don't break; use ``periods_per_year``.
TRADING_PERIODS_PER_YEAR = 252

_TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
# Fallback bar size for an unrecognized timeframe: treat it as daily so
# annualization stays defined (a bounded factor) instead of crashing a backtest
# on a novel tf string.
_DEFAULT_TF_MINUTES = 1440
_NSE_SESSION_MINUTES = 375  # 09:15-15:30 IST
_TRADING_DAYS_PER_YEAR = 252
_CALENDAR_MINUTES_PER_YEAR = 365 * 24 * 60  # 24/7 markets (crypto)


def periods_per_year(timeframe: str, asset_class: str = "crypto") -> float:
    """Number of ``timeframe`` bars in one year for this asset class.

    Annualizing a per-bar Sharpe by ``sqrt(252)`` is only correct for DAILY
    bars; a 1m equity bar packs ~94.5k periods/year, not 252. Equity bars are
    counted over the NSE session (375 min) x 252 trading days; crypto trades
    24/7 so bars are counted over the full calendar.
    """
    minutes = _TF_MINUTES.get(timeframe, _DEFAULT_TF_MINUTES)
    if asset_class == "equity":
        if minutes >= _NSE_SESSION_MINUTES:  # daily or coarser -> one bar/session
            return float(_TRADING_DAYS_PER_YEAR)
        return (_NSE_SESSION_MINUTES / minutes) * _TRADING_DAYS_PER_YEAR
    return _CALENDAR_MINUTES_PER_YEAR / minutes


def compute_stats(
    equity_curve: pd.Series,
    trades: list[TradeCosts],
    timeframe: str = "1d",
    asset_class: str = "crypto",
    init_cash: float | None = None,
) -> dict[str, Any]:
    returns = equity_curve.pct_change().dropna()

    if len(returns) < 2 or returns.std(ddof=1) == 0:
        sharpe = 0.0
    else:
        ann = math.sqrt(periods_per_year(timeframe, asset_class))
        sharpe = (returns.mean() / returns.std(ddof=1)) * ann

    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    max_dd = float(drawdown.min())

    trade_count = len(trades)
    wins = sum(1 for t in trades if t.net_pnl > 0)
    win_rate = wins / trade_count if trade_count > 0 else 0.0

    # Net return is measured against the STARTING CAPITAL. equity_curve.iloc[0]
    # is the equity AFTER the first bar's return (init_cash * (1+r0)), so using
    # it as the base drops the first bar's P&L; prefer init_cash when supplied.
    end_equity = float(equity_curve.iloc[-1])
    base = init_cash if init_cash is not None else float(equity_curve.iloc[0])
    net_return = (end_equity - base) / base

    return {
        "sharpe": float(sharpe),
        "max_dd": max_dd,
        "win_rate": win_rate,
        "net_return": net_return,
        "trade_count": trade_count,
    }
