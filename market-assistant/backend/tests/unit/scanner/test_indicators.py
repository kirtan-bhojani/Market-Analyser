import math

import numpy as np
import pandas as pd
import pandas_ta as ta
import pytest

from app.scanner.indicators import adx, atr, bollinger, ema, gap_pct, rel_volume, rsi, sma, vwap


def _synthetic_ohlcv(n=100, seed=42, base=100.0):
    rng = np.random.default_rng(seed)
    closes = base + np.cumsum(rng.normal(0, base / 100.0, n))
    highs = closes + rng.uniform(0, base / 100.0, n)
    lows = closes - rng.uniform(0, base / 100.0, n)
    opens = closes + rng.uniform(-base / 200.0, base / 200.0, n)
    volumes = rng.uniform(10, 100, n)
    # A DatetimeIndex (all within one session) is required by the installed
    # pandas-ta version's vwap() for session-anchored cumulative grouping;
    # unrelated indicators (sma/ema/rsi) ignore the index.
    index = pd.date_range("2024-01-02 09:30", periods=n, freq="min")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=index,
    )


# (asset_class, base_price) -- crypto uses a BTC/USDT-shaped ~100 scale
# (matching the pre-existing fixture); equity uses a RELIANCE.NS-shaped
# ~2900 (INR) scale. Proves the pure indicator math is asset-class-agnostic:
# it must match pandas_ta at both price/volatility scales, not just one.
ASSET_CLASS_CASES = [("crypto", 100.0), ("equity", 2900.0)]


@pytest.mark.parametrize("asset_class,base_price", ASSET_CLASS_CASES)
def test_sma_matches_pandas_ta(asset_class, base_price):
    df = _synthetic_ohlcv(base=base_price)
    expected = ta.sma(df["close"], length=20)
    result = sma(df["close"].tolist(), period=20)
    for i in range(19, len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-9)


@pytest.mark.parametrize("asset_class,base_price", ASSET_CLASS_CASES)
def test_ema_matches_pandas_ta(asset_class, base_price):
    df = _synthetic_ohlcv(base=base_price)
    expected = ta.ema(df["close"], length=12)
    result = ema(df["close"].tolist(), period=12)
    for i in range(11, len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-6)


@pytest.mark.parametrize("asset_class,base_price", ASSET_CLASS_CASES)
def test_rsi_matches_pandas_ta(asset_class, base_price):
    df = _synthetic_ohlcv(base=base_price)
    expected = ta.rsi(df["close"], length=14)
    result = rsi(df["close"].tolist(), period=14)
    for i in range(27, len(df)):  # RSI needs warmup for Wilder smoothing to converge
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-6)


def test_vwap_matches_pandas_ta_single_session():
    df = _synthetic_ohlcv(n=50)
    expected = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
    result = vwap(
        df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), df["volume"].tolist()
    )
    for i in range(len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-9)


def test_atr_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.atr(df["high"], df["low"], df["close"], length=14)
    result = atr(df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), period=14)
    for i in range(20, len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-3)


def test_adx_matches_pandas_ta():
    df = _synthetic_ohlcv(n=200)
    expected = ta.adx(df["high"], df["low"], df["close"], length=14)["ADX_14"]
    result = adx(df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), period=14)
    for i in range(40, len(df)):
        if not math.isnan(expected.iloc[i]):
            assert result[i] == pytest.approx(expected.iloc[i], rel=1e-2)


def test_rel_volume_is_ratio_to_rolling_average():
    volumes = [10.0] * 20 + [50.0]
    result = rel_volume(volumes, period=20)
    assert result[20] == pytest.approx(5.0, rel=1e-9)


def test_gap_pct_computes_open_vs_prior_close():
    opens = [102.0, 95.0]
    prev_closes = [100.0, 100.0]
    result = gap_pct(opens, prev_closes)
    assert result[0] == pytest.approx(2.0, rel=1e-9)
    assert result[1] == pytest.approx(-5.0, rel=1e-9)


def test_bollinger_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.bbands(df["close"], length=20, std=2.0)
    mid, upper, lower = bollinger(df["close"].tolist(), period=20, std_mult=2.0)
    for i in range(19, len(df)):
        assert mid[i] == pytest.approx(expected["BBM_20_2.0_2.0"].iloc[i], rel=1e-6)
        assert upper[i] == pytest.approx(expected["BBU_20_2.0_2.0"].iloc[i], rel=1e-6)
        assert lower[i] == pytest.approx(expected["BBL_20_2.0_2.0"].iloc[i], rel=1e-6)
