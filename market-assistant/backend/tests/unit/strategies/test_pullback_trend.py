import pandas as pd

from app.strategies.pullback_trend import PullbackTrendStrategy


def _bar(
    ts: object, o: float, h: float, l: float, c: float, v: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": pd.Timestamp(ts), "o": o, "h": h, "l": l, "c": c, "v": v}


def _day(i: int) -> pd.Timestamp:
    # The brief's "day{i:03d}" placeholders aren't parseable date strings;
    # use real calendar days (still strictly increasing per bar) instead.
    return pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)


def test_pullback_trend_golden_bounce_off_ema21_fires_one_long_signal():
    bars = []
    price = 100.0
    # Strong uptrend for 50 bars (well above EMA50, ADX-trend eligible).
    for i in range(50):
        price += 0.6
        bars.append(_bar(_day(i), price - 0.1, price + 0.3, price - 0.3, price, 500))
    # Pullback down toward EMA21 for 3 bars. (0.8/bar is too shallow for the
    # real EMA21 to lag into tolerance range; 1.5/bar actually brings the low
    # within pullback_tolerance_pct of the real EMA21 -- see task-8 report.)
    for j in range(3):
        price -= 1.5
        bars.append(_bar(_day(50 + j), price + 0.3, price + 0.4, price - 0.4, price, 500))
    # Bullish reversal bar: closes above prior bar's high, back above open.
    last_high = bars[-1]["h"]
    reversal_open = price
    reversal_close = last_high + 0.5
    bars.append(
        _bar(
            _day(53), reversal_open, reversal_close + 0.2, reversal_open - 0.2, reversal_close, 900
        )
    )

    candles = pd.DataFrame(bars)
    strat = PullbackTrendStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert len(signals) == 1
    assert signals[0].direction == "long"


def test_pullback_trend_negative_pullback_without_reversal_bar_fires_nothing():
    bars = []
    price = 100.0
    for i in range(50):
        price += 0.6
        bars.append(_bar(_day(i), price - 0.1, price + 0.3, price - 0.3, price, 500))
    for j in range(3):
        price -= 1.5
        bars.append(_bar(_day(50 + j), price + 0.3, price + 0.4, price - 0.4, price, 500))
    # Final bar continues down instead of reversing.
    price -= 0.5
    bars.append(_bar(_day(53), price + 0.3, price + 0.35, price - 0.35, price, 500))

    candles = pd.DataFrame(bars)
    strat = PullbackTrendStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
