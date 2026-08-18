import numpy as np
import pandas as pd

from app.backtest.costs import apply_costs
from app.ml.evaluate import simulate_directional_returns


def buy_and_hold_return(candles: pd.DataFrame, fees_bps: float, slippage_bps: float) -> float:
    entry = candles["c"].iloc[0]
    exit_ = candles["c"].iloc[-1]
    costs = apply_costs(
        entry_price=float(entry),
        exit_price=float(exit_),
        fees_bps=fees_bps,
        slippage_bps=slippage_bps,
        side="long",
    )
    return costs.net_pnl / float(entry)


def random_baseline_return(
    candles: pd.DataFrame,
    fees_bps: float,
    slippage_bps: float,
    horizon: int = 1,
    n_trials: int = 200,
    seed: int = 42,
    n_entries: int | None = None,
) -> float:
    # The random baseline must trade at the MODEL's horizon AND at the model's
    # entry FREQUENCY: comparing a model that takes k trades against a ~50%
    # coin-flip benchmark (many more trades, far more cost drag) is
    # apples-to-oranges. `n_entries` = the model's non-overlapping trade count;
    # each trial places exactly that many random entries. Falls back to ~half
    # the tradable bars when unspecified.
    rng = np.random.default_rng(seed)
    close = candles["c"].to_numpy()
    n = len(close)
    tradable = max(0, n - horizon)
    k = tradable // 2 if n_entries is None else n_entries
    k = max(0, min(k, tradable))

    trial_returns = []
    for _ in range(n_trials):
        entries_mask = np.zeros(n, dtype=bool)
        if k > 0:
            idx = rng.choice(tradable, size=k, replace=False)
            entries_mask[idx] = True
        trial_returns.append(
            simulate_directional_returns(
                close, entries_mask, horizon=horizon, fees_bps=fees_bps, slippage_bps=slippage_bps
            )
        )
    return float(np.mean(trial_returns)) if trial_returns else 0.0


def passes_baseline_gate(
    model_net_return: float, buy_hold_return: float, random_return: float
) -> bool:
    # Wrap in bool(): the inputs may be numpy floats, whose comparisons yield
    # numpy bools that fail strict `is True`/`is False` identity checks.
    return bool(model_net_return > buy_hold_return and model_net_return > random_return)
