from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd


class LeakageError(Exception):
    """Raised when a feature's timestamp is at or after its paired
    label's timestamp — i.e. the model would see the future."""


def assert_no_leakage(features: pd.DataFrame, labels: pd.DataFrame) -> None:
    if len(features) != len(labels):
        raise ValueError(
            f"features ({len(features)} rows) and labels ({len(labels)} rows) "
            "must be row-aligned and equal length"
        )

    feature_ts = features["feature_ts"].reset_index(drop=True)
    label_ts = labels["label_ts"].reset_index(drop=True)

    violations = feature_ts >= label_ts
    if violations.any():
        bad_rows = violations[violations].index.tolist()
        first = bad_rows[0]
        raise LeakageError(
            f"leakage detected at row {first} (and {len(bad_rows) - 1} more): "
            f"feature_ts={feature_ts[first]} >= label_ts={label_ts[first]}"
        )


def assert_no_cross_fold_leakage(
    feature_ts: pd.Series,
    label_ts: pd.Series,
    splits: Sequence[tuple[npt.NDArray[np.int_], npt.NDArray[np.int_]]],
) -> None:
    """Assert no training sample's label reaches into a fold's test window.

    Purged walk-forward keeps a gap between train and test, but the gap must
    exceed the label horizon: a training row's label_ts landing at/after the
    earliest test feature_ts means the training label overlaps data the test
    fold will be judged on. This catches that regardless of how ``purge`` was
    set relative to the horizon.
    """
    ft = feature_ts.reset_index(drop=True)
    lt = label_ts.reset_index(drop=True)
    for fold_i, (train_idx, test_idx) in enumerate(splits):
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        max_train_label = lt.iloc[train_idx].max()
        min_test_feature = ft.iloc[test_idx].min()
        if pd.notna(max_train_label) and max_train_label >= min_test_feature:
            raise LeakageError(
                f"cross-fold leakage in fold {fold_i}: a training label_ts "
                f"({max_train_label}) reaches into the test window "
                f"(first test feature_ts={min_test_feature})"
            )
