import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class MLModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    instrument_group: str
    version: str
    published: bool
    fold_metrics: list[dict[str, Any]]
    feature_importances: dict[str, float]
    model_net_return: float
    buy_hold_return: float
    random_return: float
    threshold: float
