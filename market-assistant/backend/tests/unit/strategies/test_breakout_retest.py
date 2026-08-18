import pandas as pd

from app.strategies.breakout_retest import BreakoutRetestStrategy


def _bar(
    ts: str, o: float, h: float, l: float, c: float, v: float  # noqa: E741
):
    return {"ts": pd.Timestamp(ts), "o": o, "h": h, "l": l, "c": c, "v": v}


def test_breakout_retest_golden_confirmed_retest_fires_one_long_signal():
    base = [
        _bar(f"2024-01-01T{9+i//4:02d}:{(i%4)*15:02d}", 100, 101, 99, 100, 500)
        for i in range(10)
    ]  # resistance ~101
    breakout = _bar("2024-01-01T12:15", 100, 106, 100, 105, 3000)  # breaks 101, volume confirm
    retest = _bar("2024-01-01T12:30", 104, 104.5, 101.2, 103, 900)  # holds above 101, closes up
    candles = pd.DataFrame(base + [breakout, retest])
    strat = BreakoutRetestStrategy()
    signals = strat.generate_signals(candles, strat.default_params())

    assert len(signals) == 1
    sig = signals[0]
    assert sig.direction == "long"
    assert sig.ref_entry == 103
    assert sig.ref_sl == 101  # broken resistance now acts as support


def test_breakout_retest_negative_retest_breaks_back_below_level_fires_nothing():
    base = [
        _bar(f"2024-01-01T{9+i//4:02d}:{(i%4)*15:02d}", 100, 101, 99, 100, 500)
        for i in range(10)
    ]
    breakout = _bar("2024-01-01T12:15", 100, 106, 100, 105, 3000)
    failed_retest = _bar("2024-01-01T12:30", 104, 104.5, 99.5, 100, 900)  # closes back below level
    candles = pd.DataFrame(base + [breakout, failed_retest])
    strat = BreakoutRetestStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
