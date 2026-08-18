import pandas as pd

from app.strategies.grid_range import GridRangeStrategy


def _day(i: int) -> pd.Timestamp:
    return pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)


def _bar(
    ts: pd.Timestamp, o: float, h: float, l: float, c: float, v: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": ts, "o": o, "h": h, "l": l, "c": c, "v": v}


def test_grid_range_golden_touch_of_lower_grid_line_fires_one_long_signal() -> None:
    # 19 bars define the 95-105 range (o=100,h=105,l=95,c=100). Grid levels
    # over that range at grid_levels=5 are 95,97,99,101,103,105; lowest level
    # is the range low (95) and tolerance = (105-95)*1% = 0.1. The final
    # bar's low is set to the range low itself so it genuinely touches the
    # lowest grid line (95 <= 95 + 0.1) and fires exactly one long signal.
    bars = [_bar(_day(i), 100, 105, 95, 100, 500) for i in range(19)]
    bars.append(_bar(_day(19), 97, 97.5, 95.0, 96.2, 500))
    candles = pd.DataFrame(bars)
    strat = GridRangeStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert len(signals) == 1
    assert signals[0].direction == "long"


def test_grid_range_negative_price_mid_range_fires_nothing() -> None:
    # First 19 bars still define the 95-105 range. The final bar is genuinely
    # interior: low=99.5 (> lowest level 95 + tolerance 0.1 = 95.1) and
    # high=100.5 (< highest level 105 - tolerance 0.1 = 104.9), so neither
    # grid line is touched and no signal fires.
    bars = [_bar(_day(i), 100, 105, 95, 100, 500) for i in range(19)]
    bars.append(_bar(_day(19), 100, 100.5, 99.5, 100, 500))
    candles = pd.DataFrame(bars)
    strat = GridRangeStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
