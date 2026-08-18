from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class CandleRow(Base):
    __tablename__ = "candles"

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    tf: Mapped[str] = mapped_column(String, primary_key=True)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    o: Mapped[Decimal | None] = mapped_column(Numeric)
    h: Mapped[Decimal | None] = mapped_column(Numeric)
    l: Mapped[Decimal | None] = mapped_column(Numeric)  # noqa: E741
    c: Mapped[Decimal | None] = mapped_column(Numeric)
    v: Mapped[Decimal | None] = mapped_column(Numeric)
