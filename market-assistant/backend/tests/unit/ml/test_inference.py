import numpy as np
import pandas as pd

from app.ml.calibration import fit_calibrator
from app.ml.inference import predict_prob_up, should_emit_signal


class _StubModel:
    def predict_proba(self, X):
        return np.array([[0.2, 0.8]])  # always predicts "up" with raw 0.8


def test_predict_prob_up_applies_calibration_to_model_output():
    calibrator = fit_calibrator(np.array([0.2, 0.5, 0.8]), np.array([0, 0, 1]))
    features_row = pd.DataFrame({"x": [1.0]})

    prob_up = predict_prob_up(_StubModel(), calibrator, features_row)

    assert 0.0 <= prob_up <= 1.0


def test_should_emit_signal_false_when_unpublished_even_with_high_confidence():
    assert should_emit_signal(published=False, prob_up=0.99, threshold=0.55) is False


def test_should_emit_signal_gates_on_threshold_when_published():
    assert should_emit_signal(published=True, prob_up=0.60, threshold=0.55) is True
    assert should_emit_signal(published=True, prob_up=0.50, threshold=0.55) is False
    # Threshold boundary is inclusive.
    assert should_emit_signal(published=True, prob_up=0.55, threshold=0.55) is True
