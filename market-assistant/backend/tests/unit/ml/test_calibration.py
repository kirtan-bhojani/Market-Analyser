import numpy as np
from sklearn.isotonic import IsotonicRegression

from app.ml.calibration import apply_calibrator, fit_calibrator


def test_calibrator_output_is_monotonic_and_bounded():
    raw = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    y = np.array([0, 0, 1, 0, 1, 1, 1, 1])

    calibrator = fit_calibrator(raw, y)
    calibrated = apply_calibrator(calibrator, raw)

    assert (calibrated >= 0.0).all()
    assert (calibrated <= 1.0).all()
    # Non-decreasing in raw-probability order (isotonic regression's defining property).
    assert np.all(np.diff(calibrated) >= -1e-12)


def test_calibrator_matches_direct_sklearn_fit_on_same_data():
    raw = np.array([0.1, 0.2, 0.3, 0.4])
    y = np.array([0, 1, 0, 1])

    ours = apply_calibrator(fit_calibrator(raw, y), raw)

    reference = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    reference.fit(raw, y)
    expected = reference.predict(raw)

    assert np.allclose(ours, expected)


def test_calibrator_clips_out_of_range_inputs():
    raw = np.array([0.2, 0.5, 0.8])
    y = np.array([0, 1, 1])
    calibrator = fit_calibrator(raw, y)

    calibrated = apply_calibrator(calibrator, np.array([-0.5, 1.5]))
    assert (calibrated >= 0.0).all()
    assert (calibrated <= 1.0).all()
