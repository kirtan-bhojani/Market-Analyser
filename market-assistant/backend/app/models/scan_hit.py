from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ScanHit(Base):
    __tablename__ = "scan_hits"
    # Authoritative same-bar dedup: at most one hit per (rule, instrument, bar).
    # The Redis SET-NX key is a best-effort fast path; this constraint is what
    # actually prevents duplicate rows under replay / concurrent workers.
    __table_args__ = (
        UniqueConstraint("rule_id", "instrument_id", "ts", name="uq_scan_hits_rule_instrument_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("scan_rules.id"))
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id"))
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
