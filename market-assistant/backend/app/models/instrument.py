from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("symbol", "exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    exchange: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
