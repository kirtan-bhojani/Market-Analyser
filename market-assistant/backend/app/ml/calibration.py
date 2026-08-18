from typing import Any, cast

import numpy as np
import numpy.typing as npt
from sklearn.isotonic import IsotonicRegression

FloatArray = npt.NDArray[np.float64]


def fit_calibrator(raw_probs: FloatArray, y_true: npt.NDArray[Any]) -> IsotonicRegression:
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    calibrator.fit(raw_probs, y_true)
    return calibrator


def apply_calibrator(calibrator: IsotonicRegression, raw_probs: FloatArray) -> FloatArray:
    clipped = np.clip(calibrator.predict(raw_probs), 0.0, 1.0)
    return cast(FloatArray, np.asarray(clipped, dtype=np.float64))
