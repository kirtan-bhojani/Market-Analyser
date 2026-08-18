"""Shared reference-level helpers used by every strategy preset.

Pure arithmetic (`rr_target`) plus thin pandas lookups over the candle
DataFrame (`swing_low`/`swing_high`) that presets use to derive entry/stop/
target levels.
"""

from __future__ import annotations

import pandas as pd


def latest_session(candles: pd.DataFrame) -> pd.DataFrame:
    """Sub-frame of the bars sharing the most recent bar's UTC day.

    Session-anchored presets (ORB opening range, VWAP reset) must reference
    the current trading session, not the oldest bar of an arbitrary rolling
    window. The whole NSE cash session (03:45-10:00 UTC) falls inside one UTC
    day, and crypto sessions are conventionally the UTC day, so grouping by
    normalized UTC day yields the session for both.

    Positional (numpy) masking keeps this correct for both frame shapes the
    presets see: a ``ts`` COLUMN over a RangeIndex (live worker / API) and a
    DatetimeIndex (backtest bridge). tz-aware and naive timestamps normalize
    cleanly.
    """
    ts = candles["ts"] if "ts" in candles.columns else candles.index.to_series()
    days = pd.to_datetime(pd.Series(ts.to_numpy())).dt.normalize().to_numpy()
    return candles.iloc[days == days[-1]]


def rr_target(entry: float, stop: float, direction: str, rr: float) -> float:
    """Risk-reward target price given an entry, stop, direction, and R multiple."""
    risk = abs(entry - stop)
    return entry + risk * rr if direction == "long" else entry - risk * rr


def candle_ts(candles: pd.DataFrame, i: int) -> pd.Timestamp:
    """Per-bar timestamp: prefer a `ts` column (unit-test fixtures), else the
    DataFrame's DatetimeIndex (backtest fixtures/bridge)."""
    if "ts" in candles.columns:
        return pd.Timestamp(candles["ts"].iloc[i])
    return pd.Timestamp(candles.index[i])


def swing_low(candles: pd.DataFrame, lookback: int) -> float:
    """Lowest low over the trailing `lookback` bars."""
    return float(candles["l"].iloc[-lookback:].min())


def swing_high(candles: pd.DataFrame, lookback: int) -> float:
    """Highest high over the trailing `lookback` bars."""
    return float(candles["h"].iloc[-lookback:].max())
