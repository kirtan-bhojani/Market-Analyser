import numpy as np
import numpy.typing as npt

from app.backtest.costs import apply_costs


def _trade_returns(
    close: npt.NDArray[np.float64],
    entries_mask: npt.NDArray[np.bool_],
    horizon: int,
    fees_bps: float,
    slippage_bps: float,
) -> list[float]:
    """Per-trade net returns for NON-OVERLAPPING entries: after entering at bar
    i (held `horizon` bars) the next entry is only considered from i+horizon, so
    a run of consecutive entry signals becomes one position, not many stacked."""
    returns: list[float] = []
    n = len(close)
    i = 0
    while i < n:
        if not entries_mask[i]:
            i += 1
            continue
        if i + horizon >= n:
            break
        costs = apply_costs(
            entry_price=float(close[i]),
            exit_price=float(close[i + horizon]),
            fees_bps=fees_bps,
            slippage_bps=slippage_bps,
            side="long",
        )
        returns.append(costs.net_pnl / float(close[i]))
        i += horizon
    return returns


def simulate_directional_returns(
    close: npt.NDArray[np.float64],
    entries_mask: npt.NDArray[np.bool_],
    horizon: int,
    fees_bps: float,
    slippage_bps: float,
) -> float:
    """Cumulative (compounded) net return over NON-OVERLAPPING entries (0.0 if
    none). Compounded — not averaged — so it stays on the same capital-growth
    basis as ``buy_and_hold_return``; the baseline gate compares the two
    directly, so an average-per-trade figure would be apples-to-oranges."""
    returns = _trade_returns(close, entries_mask, horizon, fees_bps, slippage_bps)
    capital = 1.0
    for r in returns:
        capital *= 1.0 + r
    return capital - 1.0


def count_trades(entries_mask: npt.NDArray[np.bool_], horizon: int) -> int:
    """Number of non-overlapping trades ``entries_mask`` would execute."""
    count = 0
    n = len(entries_mask)
    i = 0
    while i < n:
        if not entries_mask[i]:
            i += 1
            continue
        if i + horizon >= n:
            break
        count += 1
        i += horizon
    return count
