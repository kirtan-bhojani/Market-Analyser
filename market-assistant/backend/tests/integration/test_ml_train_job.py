import numpy as np
import pandas as pd
import pytest

from app.ml.baseline import passes_baseline_gate
from app.ml.train import train_model


def _alternating_candles(n=60, up_step=3.0, down_step=1.0, base=100.0):
    # Alternating up/down bars with a larger up-step than down-step, so a
    # perfect long-only-on-up predictor clearly beats a hold-through-everything
    # buy-and-hold, while a naive buy-and-hold still nets a mild positive drift.
    # Volume MUST vary: a constant-volume window makes the rolling volume-z
    # feature 0/0 = NaN and drops every row, leaving zero training samples.
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    closes = [base]
    for i in range(1, n):
        step = up_step if i % 2 == 1 else -down_step
        closes.append(closes[-1] + step)
    close = np.array(closes)
    volume = 1000.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {"o": close, "h": close + 0.1, "l": close - 0.1, "c": close, "v": volume}, index=idx
    )


class _PerfectClassifier:
    """Test double: a deterministic, genuinely-generalizing perfect predictor.

    On the alternating fixture the fixed-horizon(1) label at row i is
    y=1 iff close[i+1] > close[i]. close rises on odd bars (up_step) and
    falls on even bars, so y=1 exactly when bar i is even, which is exactly
    when ret_1[i] (the prior one-bar return) is negative. So predicting "up"
    whenever ret_1 < 0 is perfect on EVERY row, including unseen walk-forward
    test folds -- no memorization, so it drives calibration/baseline/gate the
    way a real edge-having model would."""

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        preds = (X["ret_1"].to_numpy() < 0).astype(float)
        return np.column_stack([1 - preds, preds])


class _NullClassifier:
    """Test double: always predicts a constant, low raw probability --
    simulates a model with zero learned signal."""

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.full(n, 0.9), np.full(n, 0.1)])


def test_train_model_publishes_when_pipeline_clearly_beats_both_baselines(tmp_path):
    candles = _alternating_candles()
    result = train_model(
        candles=candles,
        regime=None,
        instrument_group="crypto_majors",
        version="test-perfect",
        horizon=1,
        n_splits=3,
        test_size=8,
        purge=1,
        fees_bps=10.0,
        slippage_bps=5.0,
        threshold=0.55,
        classifier_factory=lambda: _PerfectClassifier(),
        artifact_base_dir=tmp_path,
    )

    assert len(result.fold_metrics) == 3
    assert result.model_net_return > result.buy_hold_return
    assert result.model_net_return > result.random_return
    assert result.published is True
    assert result.published == passes_baseline_gate(
        result.model_net_return, result.buy_hold_return, result.random_return
    )
    assert result.artifact_path  # file was written
    assert set(result.feature_importances.keys()) >= {"ret_1", "rsi_14", "vwap_dist"}


def test_train_model_stays_unpublished_when_model_has_no_edge(tmp_path):
    candles = _alternating_candles()  # buy_hold_return is positive on this fixture
    result = train_model(
        candles=candles,
        regime=None,
        instrument_group="crypto_majors",
        version="test-null",
        horizon=1,
        n_splits=3,
        test_size=8,
        purge=1,
        fees_bps=10.0,
        slippage_bps=5.0,
        threshold=0.55,
        classifier_factory=lambda: _NullClassifier(),
        artifact_base_dir=tmp_path,
    )

    # Null classifier's calibrated probability (0.1) never clears the 0.55
    # threshold, so zero trades are taken => model_net_return == 0.0, which
    # cannot exceed a positive buy_hold_return => gate fails => unpublished,
    # and the inference worker (Task 9) must emit nothing for this model.
    assert result.model_net_return == pytest.approx(0.0)
    assert result.buy_hold_return > 0.0
    assert result.published is False
