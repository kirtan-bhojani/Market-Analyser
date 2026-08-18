import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.models.ml_model import MLModel
from app.schemas.ml import MLModelResponse

router = APIRouter(prefix="/ml", tags=["ml"])


def _to_response(model: MLModel) -> MLModelResponse:
    metrics = model.metrics or {}
    return MLModelResponse(
        id=model.id,
        instrument_group=model.instrument_group,
        version=model.version,
        published=model.published,
        fold_metrics=metrics.get("fold_metrics", []),
        feature_importances=metrics.get("feature_importances", {}),
        model_net_return=metrics.get("model_net_return", 0.0),
        buy_hold_return=metrics.get("buy_hold_return", 0.0),
        random_return=metrics.get("random_return", 0.0),
        threshold=metrics.get("threshold", 0.55),
    )


@router.get("/models", response_model=list[MLModelResponse])
async def list_models(db: AsyncSession = Depends(get_session)) -> list[MLModelResponse]:
    result = await db.execute(select(MLModel))
    return [_to_response(m) for m in result.scalars().all()]


@router.get("/models/{model_id}", response_model=MLModelResponse)
async def get_model(
    model_id: uuid.UUID, db: AsyncSession = Depends(get_session)
) -> MLModelResponse:
    model = await db.get(MLModel, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    return _to_response(model)
