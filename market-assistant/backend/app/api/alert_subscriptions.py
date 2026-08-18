import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.deps import get_session
from app.models.alert_subscription import AlertSubscription
from app.models.scan_rule import ScanRule
from app.schemas.alert_subscription import AlertSubscriptionCreate, AlertSubscriptionResponse

router = APIRouter(prefix="/api/alert-subscriptions", tags=["alert-subscriptions"])


@router.post("", response_model=AlertSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: AlertSubscriptionCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AlertSubscription:
    rule = await session.get(ScanRule, payload.rule_id)
    if rule is None or rule.user_id != user_id:
        raise HTTPException(status_code=404, detail="rule not found")
    # T3-15: a telegram target (chat_id) is owned by the first user to register
    # it; a different user must not be able to route alerts into that chat.
    if payload.channel == "telegram":
        foreign = await session.scalar(
            select(AlertSubscription)
            .where(
                AlertSubscription.channel == "telegram",
                AlertSubscription.target == payload.target,
                AlertSubscription.user_id != user_id,
            )
            .limit(1)
        )
        if foreign is not None:
            raise HTTPException(status_code=403, detail="target belongs to another user")
    # T2-14: upsert — a duplicate (user, rule, channel, target) returns the
    # existing row instead of inserting a second identical subscription.
    existing = await session.scalar(
        select(AlertSubscription)
        .where(
            AlertSubscription.user_id == user_id,
            AlertSubscription.rule_id == payload.rule_id,
            AlertSubscription.channel == payload.channel,
            AlertSubscription.target == payload.target,
        )
        .limit(1)
    )
    if existing is not None:
        return existing
    subscription = AlertSubscription(
        user_id=user_id,
        rule_id=payload.rule_id,
        channel=payload.channel,
        target=payload.target,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


@router.get("", response_model=list[AlertSubscriptionResponse])
async def list_subscriptions(
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[AlertSubscription]:
    result = await session.execute(
        select(AlertSubscription).where(AlertSubscription.user_id == user_id)
    )
    return list(result.scalars().all())


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    sub = await session.get(AlertSubscription, subscription_id)
    if sub is None or sub.user_id != user_id:
        raise HTTPException(status_code=404, detail="subscription not found")
    await session.delete(sub)
    await session.commit()
