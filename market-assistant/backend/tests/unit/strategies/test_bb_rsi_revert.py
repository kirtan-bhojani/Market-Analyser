import pandas as pd

from app.strategies.bb_rsi_revert import BollingerRSIRevertStrategy


def _day(i: int) -> pd.Timestamp:
    return pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)


def _bar(
    ts: pd.Timestamp, o: float, h: float, l: float, c: float, v: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": ts, "o": o, "h": h, "l": l, "c": c, "v": v}


def test_bb_rsi_revert_golden_oversold_below_lower_band_fires_one_long_signal():
    bars = [_bar(_day(i), 100, 100.3, 99.7, 100, 500) for i in range(20)]
    # Sharp drop over 6 bars to push RSI < 30 and close below lower band.
    price = 100.0
    for j in range(6):
        price -= 4.0
        bars.append(_bar(_day(20 + j), price + 1, price + 1.2, price - 0.3, price, 500))
    candles = pd.DataFrame(bars)
    strat = BollingerRSIRevertStrategy()
    signals = strat.generate_signals(candles, strat.default_params())

    assert len(signals) == 1
    sig = signals[0]
    assert sig.direction == "long"
    assert sig.ref_entry == candles.iloc[-1]["c"]


def test_bb_rsi_revert_negative_close_inside_bands_fires_nothing():
    bars = [_bar(_day(i), 100, 100.3, 99.7, 100, 500) for i in range(26)]
    candles = pd.DataFrame(bars)
    strat = BollingerRSIRevertStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
