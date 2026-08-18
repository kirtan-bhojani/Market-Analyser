import uuid
from typing import Any

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_group: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False, default="ml_lgbm_v1")
    artifact_path: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
