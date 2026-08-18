import numpy as np
import pandas as pd
import pytest

from app.backtest.leakage import LeakageError, assert_no_leakage
from app.ml.features import build_features


def _candles(n=40, base=100.0, seed=7):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(seed)
    # Deterministic pseudo-random walk (fixed seed => fixed fixture).
    steps = rng.normal(loc=0.05, scale=1.0, size=n)
    close = base + np.cumsum(steps)
    high = close + 0.5
    low = close - 0.5
    volume = 100.0 + rng.normal(loc=0.0, scale=10.0, size=n)
    return pd.DataFrame({"o": close, "h": high, "l": low, "c": close, "v": volume}, index=idx)


def test_build_features_matches_hand_computed_ret1_and_drops_warmup_nans():
    candles = _candles()
    features = build_features(candles)

    # Longest window is 20 (volume-z / vwap). pandas rolling(20) is NaN for the
    # first 19 rows (indices 0..18) and valid from index 19, so exactly 19
    # warmup rows are dropped -> len(candles) - 19 survive.
    assert len(features) == len(candles) - 19
    assert not features.isna().any().any()

    # Hand-verify ret_1 for the first surviving row against the raw close series
    # (ret_1 is a pure one-bar pct_change, independent of every other feature's
    # warmup window, so it is exact-checkable without recomputing the others).
    first_surviving_ts = features.index[0]
    pos = candles.index.get_loc(first_surviving_ts)
    expected_ret_1 = (candles["c"].iloc[pos] - candles["c"].iloc[pos - 1]) / candles["c"].iloc[
        pos - 1
    ]
    assert features.loc[first_surviving_ts, "ret_1"] == pytest.approx(expected_ret_1, abs=1e-12)

    # RSI is bounded [0, 100] on every surviving row.
    assert (features["rsi_14"] >= 0).all()
    assert (features["rsi_14"] <= 100).all()

    # feature_ts column mirrors the index exactly (used downstream for leakage pairing).
    assert (features["feature_ts"] == features.index).all()


def test_build_features_regime_one_hots_from_regime_series():
    candles = _candles()
    regime = pd.Series("trend_up", index=candles.index)
    features = build_features(candles, regime=regime)

    assert (features["regime_trend_up"] == 1.0).all()
    assert (features["regime_trend_down"] == 0.0).all()
    assert (features["regime_range"] == 0.0).all()
    assert (features["regime_high_vol"] == 0.0).all()


def test_features_paired_with_strictly_later_labels_pass_leakage_guard():
    candles = _candles()
    features = build_features(candles)
    horizon_bars = pd.Timedelta(hours=2)

    labels = pd.DataFrame({"label_ts": features["feature_ts"] + horizon_bars})
    assert_no_leakage(
        features.rename(columns={"feature_ts": "feature_ts"}),
        labels,
    )  # does not raise


def test_features_paired_with_same_ts_labels_fail_leakage_guard():
    candles = _candles()
    features = build_features(candles)

    labels = pd.DataFrame({"label_ts": features["feature_ts"]})  # no gap at all
    with pytest.raises(LeakageError):
        assert_no_leakage(features, labels)
