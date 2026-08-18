"""Faithful SignalCandidate -> backtest bridge.

Phase-6 presets emit ``list[SignalCandidate]`` (one-shot entry/SL/TP
setups). Two consumers live here:

* ``SignalStrategyAdapter`` adapts a preset to the Phase-5 ``run_backtest``
  ``Strategy`` protocol (bool ``entries``/``exits`` frame) -- used for the
  equity-curve/entries-exits visualisation.
* ``run_signal_backtest`` computes HONEST, self-contained trade stats: each
  trade's win/loss is decided by whether TP or SL was hit, and the P&L is
  directional (shorts handled correctly). ``run_backtest``'s stats are
  close-to-close and long-only, so they mislabel wick-through-TP bars and
  INVERT short trades; the stats shown on user cards must not, hence this
  path does not route through ``run_backtest``.

Both share a single walk-forward pass (``_walk_signal_trades``) so their
entry/exit resolution can never drift apart. NEVER import pandas-ta here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import pandas as pd

from app.strategies.base import SignalCandidate


class _SignalPreset(Protocol):
    name: str

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]: ...


@dataclass(frozen=True)
class _RawTrade:
    """A resolved walk-forward position. ``exit_idx``/``exit_reason`` are
    ``None`` for a position still open at the last bar (not a trade)."""

    entry_idx: int
    exit_idx: int | None
    direction: str
    entry_price: float
    tp: float
    sl: float
    exit_reason: str | None


def _timestamps(candles: pd.DataFrame) -> pd.Series | pd.Index:
    """Per-bar timestamps: prefer a DatetimeIndex, else a ``ts`` column."""
    if isinstance(candles.index, pd.DatetimeIndex):
        return candles.index
    if "ts" in candles.columns:
        return candles["ts"]
    raise ValueError("candles must have a DatetimeIndex or a 'ts' column")


def _ts_at(ts: pd.Series | pd.Index, i: int) -> pd.Timestamp:
    """Positional timestamp access. A ``ts`` COLUMN (Series) is label-indexed
    by ``[]``, which breaks on non-0..n row indices -- use ``.iloc`` there."""
    value = ts.iloc[i] if isinstance(ts, pd.Series) else ts[i]
    return pd.Timestamp(value)


def _walk_signal_trades(
    preset: _SignalPreset,
    candles: pd.DataFrame,
    params: dict[str, Any],
    window: int,
) -> list[_RawTrade]:
    """Walk bars left->right. While flat, feed the preset the trailing window
    ending at bar ``i`` and open a position only on a signal whose ``ts`` is
    the current bar. Close on the first later bar touching TP or SL:

    * long:  ``low<=sl`` -> "sl" (loss), ``high>=tp`` -> "tp" (win).
    * short: ``high>=sl`` -> "sl" (loss), ``low<=tp`` -> "tp" (win).

    Both touched in one bar resolves as SL (conservative loss). One position
    at a time; a position open at the last bar is recorded with a ``None``
    exit (callers skip it).
    """
    n = len(candles)
    ts = _timestamps(candles)
    highs = candles["h"].to_numpy(dtype=float)
    lows = candles["l"].to_numpy(dtype=float)

    trades: list[_RawTrade] = []
    in_position = False
    e_idx = 0
    e_dir = ""
    e_entry = 0.0
    e_tp = 0.0
    e_sl = 0.0

    for i in range(n):
        if not in_position:
            start = max(0, i - window + 1)
            window_df = candles.iloc[start : i + 1]
            signals = preset.generate_signals(window_df, params)
            current_ts = _ts_at(ts, i)
            fresh = next((s for s in signals if s.ts == current_ts), None)
            if fresh is not None:
                in_position = True
                e_idx = i
                e_dir = fresh.direction
                e_entry = float(fresh.ref_entry)
                e_tp = float(fresh.ref_tp)
                e_sl = float(fresh.ref_sl)
            # An entry bar is never also an exit bar: touch checks start next bar.
            continue

        hi = highs[i]
        lo = lows[i]
        if e_dir == "long":
            hit_sl = lo <= e_sl
            hit_tp = hi >= e_tp
        else:  # short
            hit_sl = hi >= e_sl
            hit_tp = lo <= e_tp

        if hit_sl or hit_tp:
            # SL-first (conservative) when both touch in the same bar.
            reason = "sl" if hit_sl else "tp"
            trades.append(
                _RawTrade(
                    entry_idx=e_idx,
                    exit_idx=i,
                    direction=e_dir,
                    entry_price=e_entry,
                    tp=e_tp,
                    sl=e_sl,
                    exit_reason=reason,
                )
            )
            in_position = False

    if in_position:
        trades.append(
            _RawTrade(
                entry_idx=e_idx,
                exit_idx=None,
                direction=e_dir,
                entry_price=e_entry,
                tp=e_tp,
                sl=e_sl,
                exit_reason=None,
            )
        )
    return trades


class SignalStrategyAdapter:
    """Adapts a Phase-6 SignalCandidate preset to the Phase-5 backtest
    Strategy protocol via a faithful RR/SL-TP walk-forward.

    Walk bars left->right; while flat, feed the preset a trailing window
    ending at the current bar; if it returns a signal whose ``ts`` is the
    current bar (a fresh setup on this bar), OPEN a position at this bar
    (``entries[i]=True``) recording direction/ref_sl/ref_tp. While in a
    position, close (``exits[j]=True``) on the FIRST later bar that touches
    TP or SL: long -> ``high>=tp`` is a win, ``low<=sl`` is a loss (both in
    the same bar resolves as SL-first = conservative loss); short ->
    ``low<=tp`` win, ``high>=sl`` loss. One position at a time; new signals
    are ignored while in a position. Signals not tied to the current bar
    are ignored. A position still open at the last bar is left open
    (``run_backtest`` only counts closed trades).
    """

    def __init__(self, preset: _SignalPreset, window: int = 60) -> None:
        self.preset = preset
        self.window = window
        self.name = f"{preset.name}_signal_bt"

    @staticmethod
    def _timestamps(candles: pd.DataFrame) -> pd.Series | pd.Index:
        """Per-bar timestamps: prefer a DatetimeIndex, else a ``ts`` column."""
        return _timestamps(candles)

    def generate_signals(self, candles: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        n = len(candles)
        entries = [False] * n
        exits = [False] * n

        for trade in _walk_signal_trades(self.preset, candles, params, self.window):
            entries[trade.entry_idx] = True
            if trade.exit_idx is not None:
                exits[trade.exit_idx] = True

        return pd.DataFrame({"entries": entries, "exits": exits}, index=candles.index)


@dataclass(frozen=True)
class SignalTrade:
    """One honestly-resolved trade. ``ret`` is the net directional return
    fraction after round-trip costs; ``exit_reason`` decides win/loss."""

    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    direction: str  # "long" | "short"
    entry_price: float  # signal.ref_entry
    exit_price: float  # tp level if TP hit, sl level if SL hit
    exit_reason: str  # "tp" | "sl"
    ret: float


@dataclass(frozen=True)
class SignalBacktestResult:
    trades: list[SignalTrade]
    equity_curve: pd.Series  # compounded per-trade equity, indexed by exit_ts
    stats: dict[str, Any]  # same public keys as run_backtest


def _finite(value: float) -> float:
    """Coerce to a plain, finite Python float (NaN/inf -> 0.0)."""
    return float(value) if math.isfinite(value) else 0.0


_TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}


def _session_floor_window(window: int, tf: str | None, asset_class: str) -> int:
    """Floor the rolling window to at least one trading session's worth of bars.

    Session-anchored presets (ORB, breakout_retest via ``latest_session``) need
    the full current session in view; a window shorter than the session (e.g. a
    default 60 on 15m equity, whose session is 25 bars — or 15m crypto, whose
    UTC-day session is 96 bars) truncates it and drops valid signals.
    """
    if tf is None:
        return window
    minutes = _TF_MINUTES.get(tf)
    if minutes is None:
        return window
    day_minutes = 375 if asset_class == "equity" else 1440
    session_bars = max(1, math.ceil(day_minutes / minutes))
    return max(window, session_bars)


def run_signal_backtest(
    preset: _SignalPreset,
    candles: pd.DataFrame,
    params: dict[str, Any],
    fees_bps: float,
    slippage_bps: float,
    window: int = 60,
    init_cash: float = 10_000.0,
    tf: str | None = None,
    asset_class: str = "crypto",
) -> SignalBacktestResult:
    """Honest, self-contained signal backtest.

    Each closed trade's win/loss is decided by whether TP or SL was hit, and
    its return is directional (shorts correct). Mandatory round-trip
    fees+slippage are subtracted. All stats are plain, finite, JSON-safe
    floats/ints, sharing ``run_backtest``'s public keys.
    """
    window = _session_floor_window(window, tf, asset_class)
    ts = _timestamps(candles)
    round_trip_cost = 2.0 * (fees_bps + slippage_bps) / 10_000.0

    trades: list[SignalTrade] = []
    for raw in _walk_signal_trades(preset, candles, params, window):
        if raw.exit_idx is None or raw.exit_reason is None:
            continue  # position still open at the last bar -> not a trade
        exit_price = raw.tp if raw.exit_reason == "tp" else raw.sl
        if raw.direction == "long":
            gross = (exit_price - raw.entry_price) / raw.entry_price
        else:  # short
            gross = (raw.entry_price - exit_price) / raw.entry_price
        ret = gross - round_trip_cost
        trades.append(
            SignalTrade(
                entry_ts=_ts_at(ts, raw.entry_idx),
                exit_ts=_ts_at(ts, raw.exit_idx),
                direction=raw.direction,
                entry_price=float(raw.entry_price),
                exit_price=float(exit_price),
                exit_reason=raw.exit_reason,
                ret=float(ret),
            )
        )

    rets = [t.ret for t in trades]
    trade_count = len(trades)

    if rets:
        equity_values = init_cash * np.cumprod([1.0 + r for r in rets])
        equity_curve = pd.Series(
            equity_values, index=pd.Index([t.exit_ts for t in trades], name="exit_ts")
        )
    else:
        equity_curve = pd.Series([], dtype=float)

    win_rate = (
        sum(1 for t in trades if t.exit_reason == "tp") / trade_count if trade_count else 0.0
    )
    net_return = float(np.prod([1.0 + r for r in rets]) - 1.0) if rets else 0.0

    if len(rets) < 2:
        sharpe = 0.0
    else:
        # These are per-TRADE returns, not per-bar: trades arrive irregularly,
        # so there is no meaningful periods-per-year to annualize by. Report the
        # raw mean/std ratio (a per-trade information ratio), NOT a sqrt(252)
        # "annualized" number that would fabricate a time horizon.
        ret_series = pd.Series(rets)
        std = float(ret_series.std(ddof=1))
        sharpe = float(ret_series.mean() / std) if std > 0 else 0.0

    if len(equity_curve) < 2:
        max_dd = 0.0
    else:
        running_max = equity_curve.cummax()
        max_dd = float((equity_curve / running_max - 1.0).min())

    stats: dict[str, Any] = {
        "sharpe": _finite(sharpe),
        "max_dd": _finite(max_dd),
        "win_rate": _finite(win_rate),
        "net_return": _finite(net_return),
        "trade_count": int(trade_count),
    }

    return SignalBacktestResult(trades=trades, equity_curve=equity_curve, stats=stats)
