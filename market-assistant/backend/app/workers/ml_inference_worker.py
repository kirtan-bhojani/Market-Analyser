import uuid
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import build_features
from app.ml.inference import predict_prob_up, should_emit_signal
from app.ml.registry import load_artifact
from app.ml.train import FEATURE_COLUMNS
from app.models.ml_model import MLModel
from app.models.signal import Signal
from app.scanner.dedup import DEDUP_TTL_SECONDS


async def run_ml_inference_job(
    ctx: dict[str, Any], ml_model_id: str, instrument_id: int, candles_window: pd.DataFrame
) -> None:
    """arq entrypoint. The live worker ctx exposes ``session_factory``; narrow
    inference tests pass a ready ``db_session``. Resolve whichever is present so
    the same registered job serves both."""
    session = ctx.get("db_session")
    if session is not None:
        await _infer(ctx, session, ml_model_id, instrument_id, candles_window)
        return
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        await _infer(ctx, session, ml_model_id, instrument_id, candles_window)


async def _infer(
    ctx: dict[str, Any],
    db_session: AsyncSession,
    ml_model_id: str,
    instrument_id: int,
    candles_window: pd.DataFrame,
) -> None:
    ml_model = await db_session.get(MLModel, uuid.UUID(ml_model_id))
    if ml_model is None or not ml_model.published:
        return

    artifact = load_artifact(ml_model.artifact_path)
    model, calibrator = artifact["model"], artifact["calibrator"]

    features = build_features(candles_window)
    if features.empty:
        return

    latest_row = features[FEATURE_COLUMNS].iloc[[-1]]
    prob_up = predict_prob_up(model, calibrator, latest_row)

    # T3-8: a published model MUST carry its decision threshold in metrics
    # (persisted via train.train_result_metrics). Silently defaulting to 0.55
    # would serve a threshold the publish gate never validated, so assert it.
    metrics = ml_model.metrics or {}
    if "threshold" not in metrics:
        raise ValueError(
            f"published MLModel {ml_model.id} is missing 'threshold' in metrics"
        )
    threshold = metrics["threshold"]
    if not should_emit_signal(ml_model.published, prob_up, threshold):
        return

    # Idempotency: the live pipeline re-enqueues candle-close jobs (re-flushed
    # candles, worker retries), so claim a per-(model, instrument, bar) key
    # before inserting. A failed claim means this bar already emitted -> skip.
    # redis is absent in the unit ctx used by narrow inference tests, in which
    # case dedup is a no-op (those tests run each bar exactly once).
    redis = ctx.get("redis")
    if redis is not None:
        bar_ts_iso = features.index[-1].isoformat()
        dedup_key = f"signal_dedup:ml:{ml_model.id}:{instrument_id}:{bar_ts_iso}"
        claimed = await redis.set(dedup_key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
        if not claimed:
            return

    signal = Signal(
        instrument_id=instrument_id,
        strategy="ml_lgbm_v1",
        direction="long",
        ts=features.index[-1],
        confidence=prob_up,
        meta={
            "model_id": str(ml_model.id),
            "baseline": {
                "model_net_return": (ml_model.metrics or {}).get("model_net_return"),
                "buy_hold_return": (ml_model.metrics or {}).get("buy_hold_return"),
                "random_return": (ml_model.metrics or {}).get("random_return"),
            },
        },
    )
    db_session.add(signal)
    await db_session.commit()
