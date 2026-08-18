from dataclasses import dataclass

import pytest

from app.scanner.cache import IndicatorCache
from app.scanner.indicators import ema, rsi


@dataclass
class FakeCandle:
    ts: int
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    v: float


def _series(n=40, start=100.0, step=1.0):
    candles = []
    price = start
    for i in range(n):
        price += step if i % 2 == 0 else -step * 0.5
        candles.append(
            FakeCandle(ts=i, o=price - 0.1, h=price + 0.5, l=price - 0.5, c=price, v=20 + i)
        )
    return candles


def test_update_matches_batch_recompute_for_rsi_and_ema():
    history = _series(40)

    def load_history(instrument_id, tf, limit):
        return history[:-1]  # everything except the newest bar, simulating warm-start

    cache = IndicatorCache(load_history=load_history, requested_indicators=["rsi:14", "ema:21"])
    snapshot = cache.get_or_create(instrument_id=1, tf="5m").update(history[-1])

    closes = [c.c for c in history]
    expected_rsi = rsi(closes, period=14)[-1]
    expected_ema = ema(closes, period=21)[-1]

    assert snapshot["rsi:14"] == pytest.approx(expected_rsi, rel=1e-6)
    assert snapshot["ema:21"] == pytest.approx(expected_ema, rel=1e-6)


def test_second_update_advances_incrementally_without_full_reload():
    history = _series(40)
    calls = {"count": 0}

    def load_history(instrument_id, tf, limit):
        calls["count"] += 1
        return history[:-2]

    cache = IndicatorCache(load_history=load_history, requested_indicators=["ema:21"])
    inst_cache = cache.get_or_create(instrument_id=1, tf="5m")
    inst_cache.update(history[-2])
    inst_cache.update(history[-1])

    assert calls["count"] == 1  # warm-start loaded once, second update was incremental

    closes = [c.c for c in history]
    expected_ema = ema(closes, period=21)[-1]
    snapshot = inst_cache.snapshot()
    assert snapshot["ema:21"] == pytest.approx(expected_ema, rel=1e-6)


def test_separate_instrument_tf_pairs_are_isolated():
    history_a = _series(40, start=100.0)
    history_b = _series(40, start=500.0)

    def load_history(instrument_id, tf, limit):
        return history_a[:-1] if instrument_id == 1 else history_b[:-1]

    cache = IndicatorCache(load_history=load_history, requested_indicators=["ema:21"])
    snap_a = cache.get_or_create(instrument_id=1, tf="5m").update(history_a[-1])
    snap_b = cache.get_or_create(instrument_id=2, tf="5m").update(history_b[-1])

    assert snap_a["ema:21"] != pytest.approx(snap_b["ema:21"])


def test_short_history_does_not_raise_for_atr_and_adx():
    """Guard: atr/adx raise IndexError when the series is shorter than their
    period; the cache must return NaN gracefully instead of crashing, matching
    the all-NaN behavior of the other indicators."""
    import math

    history = _series(5)  # 5 bars: fewer than the default 14-bar atr/adx window

    def load_history(instrument_id, tf, limit):
        return history[:-1]

    cache = IndicatorCache(
        load_history=load_history, requested_indicators=["atr:14", "adx:14"]
    )
    snapshot = cache.get_or_create(instrument_id=1, tf="5m").update(history[-1])

    assert math.isnan(snapshot["atr:14"])
    assert math.isnan(snapshot["adx:14"])
