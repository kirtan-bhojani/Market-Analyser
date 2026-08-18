import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable: rows created before ownership tracking have no owner and are
    # therefore readable by nobody (owner-scoped GET 404s on a NULL mismatch).
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    universe: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    start_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    end_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    fees_bps: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    slippage_bps: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    equity_curve: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
