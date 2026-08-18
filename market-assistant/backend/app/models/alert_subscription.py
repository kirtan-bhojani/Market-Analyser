import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "rule_id",
            "channel",
            "target",
            name="uq_alert_sub_user_rule_channel_target",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("scan_rules.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    target: Mapped[str] = mapped_column(String, nullable=False)
