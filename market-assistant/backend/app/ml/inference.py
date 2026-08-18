from typing import Any

import pandas as pd
from sklearn.isotonic import IsotonicRegression

from app.ml.calibration import apply_calibrator


def predict_prob_up(
    model: Any, calibrator: IsotonicRegression | None, features_row: pd.DataFrame
) -> float:
    raw = model.predict_proba(features_row)[:, 1]
    if calibrator is None:
        return float(raw[0])
    calibrated = apply_calibrator(calibrator, raw)
    return float(calibrated[0])


def should_emit_signal(published: bool, prob_up: float, threshold: float) -> bool:
    return published and prob_up >= threshold
