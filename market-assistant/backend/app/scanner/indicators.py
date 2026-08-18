"""Core technical indicators over plain Python float lists.

Pure-Python and stateless: no pandas/numpy dependency at runtime. Values are
cross-checked in tests against `pandas-ta` fixtures (a dev-only dependency).
Used by the scanner's batch warm-start cache and cross-checked against
incremental updates.
"""

from __future__ import annotations

import math

NAN = float("nan")


def sma(values: list[float], period: int) -> list[float]:
    """Simple moving average over a trailing window of `period` values."""
    out = [NAN] * len(values)
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average, seeded with an SMA over the first `period` values."""
    out = [NAN] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(closes: list[float], period: int = 14) -> list[float]:
    """Relative Strength Index using Wilder's smoothing (RMA).

    Matches `pandas_ta.rsi`'s default `mamode="rma"`: gains/losses are
    smoothed with an EWM of alpha=1/period seeded from the *first* delta
    (pandas `ewm(adjust=False)` semantics), not an SMA warm-up over the
    first `period` bars. RSI values are therefore defined from index 1
    onward rather than only after a full `period` warm-up window.
    """
    out = [NAN] * len(closes)
    if len(closes) <= period:
        return out
    alpha = 1 / period
    avg_gain: float | None = None
    avg_loss: float | None = None
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        if avg_gain is None or avg_loss is None:
            avg_gain = gain
            avg_loss = loss
        else:
            avg_gain = alpha * gain + (1 - alpha) * avg_gain
            avg_loss = alpha * loss + (1 - alpha) * avg_loss
        out[i] = _rsi_from_avgs(avg_gain, avg_loss)
    return out


def _rsi_from_avgs(avg_gain: float, avg_loss: float) -> float:
    denom = avg_gain + avg_loss
    if denom == 0:
        return NAN
    return 100 * avg_gain / denom


def vwap(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> list[float]:
    """Volume-weighted average price, cumulative over the given bars.

    Callers are responsible for session resets: pass only one trading
    session's bars per call (e.g. one day) to match daily VWAP semantics.
    """
    out = [NAN] * len(closes)
    cum_pv = 0.0
    cum_v = 0.0
    for i in range(len(closes)):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += typical * volumes[i]
        cum_v += volumes[i]
        out[i] = cum_pv / cum_v if cum_v else NAN
    return out


def _true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    tr = [NAN] * len(closes)
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    return tr


def _wilder_smooth_presma(values: list[float], period: int) -> list[float]:
    """Wilder's smoothing (RMA) seeded with a (possibly NaN-skipping) mean over
    `values[0:period]`, matching `pandas_ta`'s `atr()` "presma" seeding: the
    seed is the (skip-NaN) average of the first `period` values, placed at
    index `period - 1`, after which the recurrence continues with the raw
    (unaveraged) values.
    """
    out = [NAN] * len(values)
    window = [v for v in values[:period] if not math.isnan(v)]
    if not window:
        return out
    seed = sum(window) / len(window)
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = (prev * (period - 1) + values[i]) / period
        out[i] = prev
    return out


def _rma_from_first_valid(values: list[float], period: int, start_index: int) -> list[float]:
    """EWM(alpha=1/period, adjust=False) starting at `start_index`, seeded with
    the raw value at `start_index` (no SMA warm-up). Matches `pandas_ta`'s
    `rma()`, which is a plain `Series.ewm(alpha=1/period, adjust=False).mean()`
    with no presma treatment for series (e.g. +DM/-DM/DX) that aren't routed
    through `atr()`'s explicit presma seeding.
    """
    out = [NAN] * len(values)
    if start_index >= len(values):
        return out
    prev = values[start_index]
    out[start_index] = prev
    alpha = 1 / period
    for i in range(start_index + 1, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out[i] = prev
    return out


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float]:
    """Average True Range using Wilder's smoothing of the true range series.

    Matches `pandas_ta.atr()`'s default (`mamode="rma"`, `prenan=False`,
    no talib): true range is seeded via an SMA over its first `period` values
    (index 0 is a real value here, since `prenan=False`), then smoothed with
    Wilder's recurrence. Traced from
    `pandas_ta/volatility/atr.py` + `pandas_ta/volatility/true_range.py`
    (installed pandas-ta 0.4.71b0) — the naive "SMA over `tr[1:period+1]`"
    seeding from the brief is off by one index vs. the oracle.
    """
    tr = _true_range(highs, lows, closes)
    return _wilder_smooth_presma(tr, period)


def adx(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float]:
    """Average Directional Index (Wilder), matching `pandas_ta.adx`'s `ADX_{period}` column.

    Traced from `pandas_ta/trend/adx.py` (non-talib, `tvmode=False` path,
    installed pandas-ta 0.4.71b0):
    - The internal ATR call passes `prenan=True`, so its true-range series has
      index 0 forced to NaN; the presma seed is then the *skip-NaN* mean of
      `tr[0:period]` (i.e. of `tr[1:period]`, `period - 1` values).
    - +DM/-DM are *not* presma-seeded: they're smoothed via a raw
      `ewm(alpha=1/period, adjust=False)`, whose first defined value (index 1,
      since diffs are undefined at index 0) becomes the seed directly.
    - DX is computed pointwise as `100 * |+DI - -DI| / (+DI + -DI)` wherever
      the internal ATR is defined and nonzero.
    - The final ADX is *also* a raw ewm (no presma) over DX, seeded with DX's
      first defined value.
    """
    n = len(closes)
    plus_dm = [NAN] * n
    minus_dm = [NAN] * n
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    tr = _true_range(highs, lows, closes)
    tr_for_adx = list(tr)
    tr_for_adx[0] = NAN  # internal atr() call within adx() uses prenan=True
    smoothed_tr = _wilder_smooth_presma(tr_for_adx, period)
    smoothed_plus_dm = _rma_from_first_valid(plus_dm, period, start_index=1)
    smoothed_minus_dm = _rma_from_first_valid(minus_dm, period, start_index=1)

    dx = [NAN] * n
    for i in range(period - 1, n):
        if math.isnan(smoothed_tr[i]) or smoothed_tr[i] == 0:
            continue
        plus_di = 100 * smoothed_plus_dm[i] / smoothed_tr[i]
        minus_di = 100 * smoothed_minus_dm[i] / smoothed_tr[i]
        denom = plus_di + minus_di
        dx[i] = 100 * abs(plus_di - minus_di) / denom if denom else 0.0

    first_dx_index = next((i for i in range(n) if not math.isnan(dx[i])), None)
    if first_dx_index is None:
        return [NAN] * n
    return _rma_from_first_valid(dx, period, start_index=first_dx_index)


def rel_volume(volumes: list[float], period: int = 20) -> list[float]:
    """Ratio of each bar's volume to the average volume of the *preceding*
    `period` bars (today's volume is excluded from its own baseline average,
    matching the conventional trading definition of relative volume).
    """
    out = [NAN] * len(volumes)
    for i in range(period, len(volumes)):
        avg = sum(volumes[i - period : i]) / period
        if avg != 0:
            out[i] = volumes[i] / avg
    return out


def gap_pct(opens: list[float], prev_closes: list[float]) -> list[float]:
    """Percentage gap of each bar's open versus the prior bar's close."""
    return [
        (opens[i] - prev_closes[i]) / prev_closes[i] * 100 if prev_closes[i] else NAN
        for i in range(len(opens))
    ]


def bollinger(
    closes: list[float], period: int = 20, std_mult: float = 2.0
) -> tuple[list[float], list[float], list[float]]:
    """Bollinger Bands: (mid, upper, lower), mid = SMA, bands = mid +/- std_mult * stddev.

    Uses the *sample* standard deviation (N - 1 denominator), matching
    `pandas_ta.bbands()`'s default `ddof=1` (traced from
    `pandas_ta/statistics/stdev.py` / `variance.py`, installed pandas-ta
    0.4.71b0) rather than a population (N) denominator.
    """
    mid = sma(closes, period)
    upper = [NAN] * len(closes)
    lower = [NAN] * len(closes)
    for i in range(len(closes)):
        if i >= period - 1:
            window = closes[i - period + 1 : i + 1]
            m = mid[i]
            variance = sum((x - m) ** 2 for x in window) / (period - 1)
            std = math.sqrt(variance)
            upper[i] = m + std_mult * std
            lower[i] = m - std_mult * std
    return mid, upper, lower
