"""ADX-only regime gate (Phase 6 stand-in).

A full multi-signal regime filter lands in Phase 7 and supersedes this;
for now every preset uses this single-indicator trend/range gate.
"""

from __future__ import annotations

import math

import pandas as pd

from app.scanner.indicators import adx


def adx_allows(
    candles: pd.DataFrame,
    period: int = 14,
    min_adx_trend: float = 20.0,
    mode: str = "trend",
) -> bool:
    """Return whether the current ADX regime permits trading in `mode`.

    `mode="trend"` requires the last ADX value >= `min_adx_trend`;
    `mode="range"` requires it to be below that threshold; any other mode
    (e.g. "any") always allows.

    `app.scanner.indicators.adx` raises `IndexError` when the input is
    shorter than `period`, and returns `NaN` during its warmup window even
    on longer series. Both cases are treated as "not enough signal yet" and
    default to False for trend mode (blocking trend-only entries until ADX
    is actually readable) — except "any"/other modes, which always allow.
    """
    if mode not in ("trend", "range"):
        return True

    highs = candles["h"].astype(float).tolist()
    lows = candles["l"].astype(float).tolist()
    closes = candles["c"].astype(float).tolist()

    if len(closes) < period:
        return False

    series = adx(highs, lows, closes, period=period)
    last_adx = series[-1]
    if math.isnan(last_adx):
        return False

    if mode == "trend":
        return last_adx >= min_adx_trend
    return last_adx < min_adx_trend
