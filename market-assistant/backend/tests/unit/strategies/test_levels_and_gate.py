import pandas as pd

from app.strategies.levels import rr_target, swing_high, swing_low
from app.strategies.regime_gate import adx_allows


def test_rr_target_long():
    assert rr_target(entry=100.0, stop=95.0, direction="long", rr=2.0) == 110.0


def test_rr_target_short():
    assert rr_target(entry=100.0, stop=105.0, direction="short", rr=2.0) == 90.0


def test_swing_low_and_high():
    candles = pd.DataFrame({"l": [10, 8, 9, 12], "h": [15, 16, 14, 18]})
    assert swing_low(candles, lookback=4) == 8
    assert swing_high(candles, lookback=4) == 18


def test_adx_allows_trend_mode(fixture_trending_candles):
    assert (
        adx_allows(fixture_trending_candles, period=14, min_adx_trend=20.0, mode="trend") is True
    )


def test_adx_allows_range_mode_blocks_trending(fixture_trending_candles):
    assert (
        adx_allows(fixture_trending_candles, period=14, min_adx_trend=20.0, mode="range") is False
    )
