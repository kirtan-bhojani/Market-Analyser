from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.backtest.costs import TradeCosts, apply_costs
from app.backtest.leakage import assert_no_leakage
from app.backtest.protocol import Strategy
from app.backtest.stats import compute_stats


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    trades: list[TradeCosts]
    stats: dict[str, Any]


def run_backtest(
    strategy: Strategy,
    candles: pd.DataFrame,
    params: dict[str, Any],
    fees_bps: float,
    slippage_bps: float,
    init_cash: float = 10_000.0,
    timeframe: str = "1d",
    asset_class: str = "crypto",
) -> BacktestResult:
    # Optional leakage guard (no-op for signal strategies without feature/label frames).
    if "_features" in params and "_labels" in params:
        assert_no_leakage(params["_features"], params["_labels"])

    signals = strategy.generate_signals(candles, params)
    entries = signals["entries"].astype(bool)
    exits = signals["exits"].astype(bool)
    close = candles["c"].astype(float)

    fees_frac = fees_bps / 10_000.0
    slippage_frac = slippage_bps / 10_000.0
    cost_per_side = fees_frac + slippage_frac

    # Position: 1.0 while long, 0.0 while flat. A signal at bar t executes at bar t's
    # close, so the position held at t only earns the return from t to t+1 (shift(1)).
    position = pd.Series(np.nan, index=close.index)
    position[entries] = 1.0
    position[exits] = 0.0
    position = position.ffill().fillna(0.0)

    bar_returns = close.pct_change().fillna(0.0)
    gross_returns = position.shift(1).fillna(0.0) * bar_returns

    # Mandatory cost drag: each entry and each exit pays (fees + slippage) of equity.
    cost_drag = (entries.astype(float) + exits.astype(float)) * cost_per_side
    net_returns = gross_returns - cost_drag

    equity_curve = init_cash * (1.0 + net_returns).cumprod()

    # Closed trades: walk bars, pairing each entry (when flat) with the next exit.
    trades: list[TradeCosts] = []
    in_position = False
    entry_price = 0.0
    for is_entry, is_exit, price in zip(entries.to_numpy(), exits.to_numpy(), close.to_numpy()):
        if is_entry and not in_position:
            in_position = True
            entry_price = float(price)
        elif is_exit and in_position:
            trades.append(
                apply_costs(
                    entry_price=entry_price,
                    exit_price=float(price),
                    fees_bps=fees_bps,
                    slippage_bps=slippage_bps,
                    side="long",
                )
            )
            in_position = False

    stats = compute_stats(
        equity_curve, trades, timeframe=timeframe, asset_class=asset_class, init_cash=init_cash
    )
    return BacktestResult(equity_curve=equity_curve, trades=trades, stats=stats)
