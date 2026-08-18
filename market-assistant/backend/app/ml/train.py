from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.backtest.leakage import assert_no_cross_fold_leakage, assert_no_leakage
from app.ml.baseline import buy_and_hold_return, passes_baseline_gate, random_baseline_return
from app.ml.calibration import apply_calibrator, fit_calibrator
from app.ml.evaluate import count_trades, simulate_directional_returns
from app.ml.features import build_features
from app.ml.labels import build_fixed_horizon_labels
from app.ml.registry import save_artifact
from app.ml.splitter import purged_walk_forward_splits

# regime_* one-hots are intentionally EXCLUDED: the inference worker has no
# regime series at serve time, so those columns would be all-zero at serve
# while training saw real dummies -- a train/serve skew. Keeping the model
# regime-free guarantees the feature vector is identical in both paths.
# build_features still emits the regime columns; they are simply not selected.
FEATURE_COLUMNS = [
    "ret_1",
    "ret_3",
    "ret_5",
    "vol_10",
    "rsi_14",
    "volume_z",
    "vwap_dist",
]


def default_lgbm_classifier() -> Any:
    import lightgbm as lgb

    return lgb.LGBMClassifier(n_estimators=100, num_leaves=15, learning_rate=0.05, random_state=42)


@dataclass(frozen=True)
class TrainResult:
    fold_metrics: list[dict[str, Any]]
    feature_importances: dict[str, float]
    model_net_return: float
    buy_hold_return: float
    random_return: float
    published: bool
    artifact_path: str
    threshold: float


def train_model(
    candles: pd.DataFrame,
    regime: pd.Series | None,
    instrument_group: str,
    version: str,
    horizon: int,
    n_splits: int,
    test_size: int,
    purge: int,
    fees_bps: float,
    slippage_bps: float,
    threshold: float = 0.55,
    classifier_factory: Callable[[], Any] = default_lgbm_classifier,
    artifact_base_dir: Path | None = None,
) -> TrainResult:
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    features = build_features(candles, regime=regime)
    labels = build_fixed_horizon_labels(candles, horizon=horizon)

    joined = features.join(labels, how="inner")
    assert_no_leakage(
        joined.rename(columns={"feature_ts": "feature_ts"}),
        joined[["label_ts"]],
    )

    X = joined[FEATURE_COLUMNS].reset_index(drop=True)
    y = joined["y"].reset_index(drop=True).to_numpy()
    # Map each kept (filtered) row back to its position in the FULL candle
    # series, so trade exits step `horizon` real bars ahead (matching the label
    # horizon) rather than `horizon` rows in the gap-collapsed filtered set.
    orig_pos = candles.index.get_indexer(joined.index)
    full_close = candles["c"].to_numpy()

    # The purged gap between train and test must cover the full label horizon:
    # the last training row's label looks `horizon` bars ahead, so a smaller
    # purge lets that label overlap the test window (leakage).
    if purge < horizon:
        raise ValueError(
            f"purge ({purge}) must be >= horizon ({horizon}) so a training "
            "label cannot reach into the test window"
        )

    n = len(X)
    splits = purged_walk_forward_splits(
        n_samples=n, n_splits=n_splits, test_size=test_size, purge=purge
    )
    # Defense in depth: verify no fold's training labels overlap its test window.
    assert_no_cross_fold_leakage(joined["feature_ts"], joined["label_ts"], splits)

    fold_metrics: list[dict[str, Any]] = []
    oof_raw = np.full(n, np.nan)
    oof_mask = np.zeros(n, dtype=bool)

    for fold_i, (train_idx, test_idx) in enumerate(splits):
        clf = classifier_factory()
        clf.fit(X.iloc[train_idx], y[train_idx])
        raw_test = clf.predict_proba(X.iloc[test_idx])[:, 1]

        oof_raw[test_idx] = raw_test
        oof_mask[test_idx] = True

        preds = (raw_test >= 0.5).astype(int)
        accuracy = float((preds == y[test_idx]).mean())
        fold_metrics.append(
            {
                "fold": fold_i,
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "accuracy": accuracy,
            }
        )

    oof_idx = np.where(oof_mask)[0]

    # Gate calibrator: fit on the EARLIER OOF bars and gate on the later,
    # unseen bars. Fitting an isotonic calibrator and then evaluating the gate
    # on that SAME OOF set lets it overfit noise and flatter the model
    # (in-sample optimism); a held-out fold keeps the gate honest. The SHIPPED
    # calibrator IS this gate calibrator (T3-5), so the model served in
    # production is exactly the one the publish gate validated — no gate/serve
    # calibration mismatch.
    split = len(oof_idx) // 2
    cal_idx = oof_idx[:split] if split else oof_idx
    eval_idx = oof_idx[split:] if split else oof_idx
    raw_cal, y_cal = oof_raw[cal_idx], y[cal_idx]
    raw_eval = oof_raw[eval_idx]
    if len(set(raw_cal.tolist())) > 1:
        gate_calibrator = fit_calibrator(raw_cal, y_cal)
        gated_eval = apply_calibrator(gate_calibrator, raw_eval)
    else:
        # Degenerate case (constant raw output): isotonic on a single unique x
        # is undefined-in-spirit, so serve/gate the raw constant directly.
        gate_calibrator = None
        gated_eval = raw_eval
    calibrator = gate_calibrator

    # Project the gated entries onto the full candle series by ts so the
    # simulator exits `horizon` real bars later (not horizon filtered rows).
    entered_filtered = np.zeros(n, dtype=bool)
    entered_filtered[eval_idx] = gated_eval >= threshold
    entries_mask_full = np.zeros(len(full_close), dtype=bool)
    entries_mask_full[orig_pos[entered_filtered]] = True

    model_net_return = simulate_directional_returns(
        full_close,
        entries_mask_full,
        horizon=horizon,
        fees_bps=fees_bps,
        slippage_bps=slippage_bps,
    )

    # Baselines over the SAME held-out window and SAME horizon as the model.
    eval_candles = (
        candles.reindex(joined.index).iloc[eval_idx[0] : eval_idx[-1] + 1]
        if len(eval_idx)
        else candles.iloc[:1]
    )
    buy_hold = buy_and_hold_return(eval_candles, fees_bps=fees_bps, slippage_bps=slippage_bps)
    # T2-6: the random baseline must trade at the model's entry FREQUENCY, so
    # pass the model's non-overlapping trade count rather than a coin-flip rate.
    n_model_trades = count_trades(entries_mask_full, horizon)
    random_return = random_baseline_return(
        eval_candles,
        fees_bps=fees_bps,
        slippage_bps=slippage_bps,
        horizon=horizon,
        n_entries=n_model_trades,
    )

    published = passes_baseline_gate(model_net_return, buy_hold, random_return)

    final_model = classifier_factory()
    final_model.fit(X, y)
    importances = getattr(final_model, "feature_importances_", None)
    if importances is not None:
        feature_importances = dict(zip(FEATURE_COLUMNS, [float(v) for v in importances]))
    else:
        feature_importances = {col: 0.0 for col in FEATURE_COLUMNS}

    artifact_path = save_artifact(
        {"model": final_model, "calibrator": calibrator},
        instrument_group=instrument_group,
        version=version,
        base_dir=artifact_base_dir,
    )

    return TrainResult(
        fold_metrics=fold_metrics,
        feature_importances=feature_importances,
        model_net_return=model_net_return,
        buy_hold_return=buy_hold,
        random_return=random_return,
        published=published,
        artifact_path=artifact_path,
        threshold=threshold,
    )


def train_result_metrics(result: TrainResult) -> dict[str, Any]:
    """Canonical MLModel.metrics payload for a TrainResult. The serving/inference
    path reads ``threshold`` from here and now ASSERTS its presence (T3-8), so
    persisting a model MUST use this to carry the threshold, not just the
    fold metrics."""
    return {
        "threshold": result.threshold,
        "model_net_return": result.model_net_return,
        "buy_hold_return": result.buy_hold_return,
        "random_return": result.random_return,
        "fold_metrics": result.fold_metrics,
        "feature_importances": result.feature_importances,
    }
