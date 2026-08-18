from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AlertSubscriptionCreate(BaseModel):
    rule_id: int
    channel: str
    target: str


class AlertSubscriptionResponse(BaseModel):
    id: int
    user_id: UUID
    rule_id: int
    channel: str
    target: str
    model_config = {"from_attributes": True}
