import pandas as pd
import pytest

from app.backtest.leakage import LeakageError, assert_no_leakage


def test_raises_when_feature_ts_equals_label_ts():
    features = pd.DataFrame({
        "feature_ts": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"]),
        "x": [1.0, 2.0],
    })
    labels = pd.DataFrame({
        "label_ts": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T02:00:00Z"]),
        "y": [1, 0],
    })
    with pytest.raises(LeakageError, match="row 0"):
        assert_no_leakage(features, labels)


def test_raises_when_feature_ts_after_label_ts():
    features = pd.DataFrame({
        "feature_ts": pd.to_datetime(["2024-01-01T03:00:00Z"]),
        "x": [1.0],
    })
    labels = pd.DataFrame({
        "label_ts": pd.to_datetime(["2024-01-01T02:00:00Z"]),
        "y": [1],
    })
    with pytest.raises(LeakageError, match="row 0"):
        assert_no_leakage(features, labels)


def test_passes_when_all_feature_ts_strictly_before_label_ts():
    features = pd.DataFrame({
        "feature_ts": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"]),
        "x": [1.0, 2.0],
    })
    labels = pd.DataFrame({
        "label_ts": pd.to_datetime(["2024-01-01T01:00:00Z", "2024-01-01T02:00:00Z"]),
        "y": [1, 0],
    })
    assert_no_leakage(features, labels)  # does not raise
