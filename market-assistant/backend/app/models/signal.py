import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Numeric, Select, Text, select
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"))
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    ref_entry: Mapped[Decimal | None] = mapped_column(Numeric)
    ref_sl: Mapped[Decimal | None] = mapped_column(Numeric)
    ref_tp: Mapped[Decimal | None] = mapped_column(Numeric)
    backtest_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    @staticmethod
    def recent_for_instrument(instrument_id: int, limit: int = 20) -> "Select[tuple[Signal]]":
        """Select the most recent signals for an instrument, newest first."""
        return (
            select(Signal)
            .where(Signal.instrument_id == instrument_id)
            .order_by(Signal.ts.desc())
            .limit(limit)
        )
