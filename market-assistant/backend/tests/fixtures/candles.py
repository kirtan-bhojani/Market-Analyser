"""Deterministic synthetic OHLCV fixtures for backtest smoke tests.

Pure NumPy/pandas construction (dev deps). No randomness, no wall-clock:
every call returns byte-identical data so preset backtest stats are
reproducible. NEVER import pandas-ta here.
"""

import numpy as np
import pandas as pd

# 60 days of 15m bars = 5760 bars. Multi-week, multi-cycle, and fast enough
# that an O(n*window) preset walk-forward through run_backtest finishes in a
# couple of seconds. (Full 90d/8640 was trimmed for smoke-test speed.)
_BTC_15M_BARS = 5760
_BTC_15M_START = pd.Timestamp("2024-01-01", tz="UTC")


def _btc_15m_3mo() -> pd.DataFrame:
    n = _BTC_15M_BARS
    i = np.arange(n, dtype=float)

    base = 40_000.0
    drift = 1.5  # gentle net uptrend over the window
    # Two superimposed cycles give both trends and mean-reverting swings.
    amp1 = 2_500.0
    period1 = 96 * 7  # ~weekly swing
    amp2 = 900.0
    period2 = 96  # ~daily swing

    close = base + drift * i + amp1 * np.sin(i / period1) + amp2 * np.sin(i / period2)
    # Guaranteed positive by construction (base >> amp1+amp2), but be explicit.
    assert (close > 0).all()

    # Open = prior close (first bar opens at its own close).
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]

    wiggle = 0.0015 + 0.0010 * np.abs(np.sin(i / 53.0))
    hi = np.maximum(open_, close) * (1.0 + wiggle)
    lo = np.minimum(open_, close) * (1.0 - wiggle)

    base_vol = 100.0
    vol = base_vol * (1.0 + 0.5 * np.sin(i / 41.0))
    # Deterministic periodic spikes so rel_volume varies meaningfully.
    vol[(i.astype(int) % 97) == 0] *= 3.0

    idx = pd.date_range(_BTC_15M_START, periods=n, freq="15min")
    return pd.DataFrame(
        {"o": open_, "h": hi, "l": lo, "c": close, "v": vol},
        index=idx,
    )


def _btc_15m_3mo_with_funding() -> pd.DataFrame:
    """Same base OHLCV as ``btc_15m_3mo`` plus a deterministic ``funding_rate``
    column: a triangle wave oscillating with amplitude 0.004, well past the
    default preset thresholds of +-0.0025, on a period short enough (240
    bars = 2.5 days) to cross both extremes many times across the fixture's
    5760 bars -- so a trailing-window walk-forward sees fresh extremes
    repeatedly, not just once."""
    df = _btc_15m_3mo()
    n = len(df)
    i = np.arange(n, dtype=float)

    period = 240.0
    amplitude = 0.004
    # Triangle wave in [-1, 1] via arcsin(sin(.)) normalization, scaled to
    # +-amplitude. Pure arithmetic, no randomness.
    phase = (i / period) % 1.0
    triangle = np.where(phase < 0.5, 4.0 * phase - 1.0, 3.0 - 4.0 * phase)
    df = df.copy()
    df["funding_rate"] = amplitude * triangle
    return df


def _reliance_15m_breakout_day() -> pd.DataFrame:
    """A single synthetic NSE equity session (RELIANCE.NS-shaped, ~2900
    range) of 15m bars, 09:15-15:30 IST (03:45-10:00 UTC on one UTC
    calendar day, matching ORB's ``_latest_session`` UTC-day masking) --
    26 bars total. Proves the backtest runner accepts equity-shaped candles
    (same ``o, h, l, c, v`` schema as ``_btc_15m_3mo``, just a different
    price/volume scale), not just crypto.

    Bars 0-3 are the flat opening range (default ``or_bars=4``). Bar 4
    breaks out above the opening range high on a deterministic volume
    spike (3x the opening-range average, clearing the default
    ``min_rel_volume=2.0``), triggering an ORB long signal at
    entry=2915, sl=2892, tp=2961 (default ``rr=2.0``:
    ``2915 + 2*(2915-2892) = 2961``). Bar 5's high (2965) touches TP
    before its low threatens SL, closing the trade a winner one bar
    later. Bars 6-25 are a gentle bounded drift, deliberately kept
    between SL and TP -- they exist only to fill out the session; no
    further signals fire on them (the ORB preset breaks after its first
    match per call).
    """
    start = pd.Timestamp("2024-06-03 03:45", tz="UTC")
    n = 26
    idx = pd.date_range(start, periods=n, freq="15min")

    # Bars 0-3: flat opening range.
    or_close = [2895.0, 2897.0, 2899.0, 2900.0]
    or_open = [2894.0, 2895.0, 2897.0, 2899.0]
    or_high = [c + 3.0 for c in or_close]
    or_low = [c - 3.0 for c in or_close]
    or_vol = [50_000.0] * 4

    # Bar 4: breakout above or_high(=2903) with a 3x volume spike.
    breakout_open = [2900.0]
    breakout_close = [2915.0]
    breakout_high = [2916.0]
    breakout_low = [2905.0]
    breakout_vol = [150_000.0]

    # Bar 5: high touches tp(=2961) before low threatens sl(=2892).
    tp_open = [2915.0]
    tp_close = [2960.0]
    tp_high = [2965.0]
    tp_low = [2950.0]
    tp_vol = [80_000.0]

    # Bars 6-25 (20 bars): bounded drift, safely between sl and tp.
    rest_n = n - 6
    j = np.arange(rest_n, dtype=float)
    rest_close = 2950.0 + 5.0 * np.sin(j / 3.0)
    rest_open = np.empty(rest_n)
    rest_open[0] = tp_close[-1]
    rest_open[1:] = rest_close[:-1]
    rest_high = np.maximum(rest_open, rest_close) + 2.0
    rest_low = np.minimum(rest_open, rest_close) - 2.0
    rest_vol = 60_000.0 * (1.0 + 0.1 * np.sin(j / 4.0))

    open_ = np.concatenate([or_open, breakout_open, tp_open, rest_open])
    close = np.concatenate([or_close, breakout_close, tp_close, rest_close])
    hi = np.concatenate([or_high, breakout_high, tp_high, rest_high])
    lo = np.concatenate([or_low, breakout_low, tp_low, rest_low])
    vol = np.concatenate([or_vol, breakout_vol, tp_vol, rest_vol])

    return pd.DataFrame({"o": open_, "h": hi, "l": lo, "c": close, "v": vol}, index=idx)


def load_fixture_candles(name: str) -> pd.DataFrame:
    """Return a deterministic synthetic OHLCV DataFrame for ``name``.

    Columns ``o, h, l, c, v`` (floats), indexed by a 15-minute
    ``DatetimeIndex``. Unknown names raise ``ValueError``.
    """
    if name == "btc_15m_3mo":
        return _btc_15m_3mo()
    if name == "btc_15m_3mo_with_funding":
        return _btc_15m_3mo_with_funding()
    if name == "reliance_15m_breakout_day":
        return _reliance_15m_breakout_day()
    raise ValueError(f"unknown fixture name: {name!r}")
