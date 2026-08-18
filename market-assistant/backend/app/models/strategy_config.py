import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    # One config per (user, strategy, instrument, tf): the enable toggle upserts
    # onto this key so disabling flips the existing row rather than inserting a
    # second one that leaves the strategy still enabled for the worker.
    __table_args__ = (
        UniqueConstraint(
            "user_id", "strategy", "instrument_id", "tf",
            name="uq_strategy_configs_user_scope",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    tf: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
