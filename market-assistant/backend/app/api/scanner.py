import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.deps import get_session
from app.models.scan_rule import ScanRule
from app.scanner.dsl import RuleDSLError, parse_rule_definition

router = APIRouter(prefix="/api/scanner", tags=["scanner"])


class ScanRuleCreate(BaseModel):
    name: str
    definition: dict[str, Any]
    enabled: bool = True


class ScanRuleUpdate(BaseModel):
    name: str | None = None
    definition: dict[str, Any] | None = None
    enabled: bool | None = None


class ScanRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    definition: dict[str, Any]
    enabled: bool


def _validate_definition(definition: dict[str, Any]) -> dict[str, Any]:
    try:
        parse_rule_definition(definition)
    except RuleDSLError as e:
        raise HTTPException(status_code=422, detail=f"{e.path}: {e.message}") from e
    return definition


@router.post("/rules", response_model=ScanRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: ScanRuleCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ScanRule:
    _validate_definition(payload.definition)
    rule = ScanRule(
        user_id=user_id,
        name=payload.name,
        definition=payload.definition,
        enabled=payload.enabled,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/rules", response_model=list[ScanRuleOut])
async def list_rules(
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[ScanRule]:
    result = await session.execute(select(ScanRule).where(ScanRule.user_id == user_id))
    return list(result.scalars().all())


@router.get("/rules/{rule_id}", response_model=ScanRuleOut)
async def get_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ScanRule:
    rule = await session.get(ScanRule, rule_id)
    if rule is None or rule.user_id != user_id:
        raise HTTPException(status_code=404, detail="rule not found")
    return rule


@router.patch("/rules/{rule_id}", response_model=ScanRuleOut)
async def update_rule(
    rule_id: int,
    payload: ScanRuleUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ScanRule:
    rule = await session.get(ScanRule, rule_id)
    if rule is None or rule.user_id != user_id:
        raise HTTPException(status_code=404, detail="rule not found")
    if payload.definition is not None:
        _validate_definition(payload.definition)
        rule.definition = payload.definition
    if payload.name is not None:
        rule.name = payload.name
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    rule = await session.get(ScanRule, rule_id)
    if rule is None or rule.user_id != user_id:
        raise HTTPException(status_code=404, detail="rule not found")
    await session.delete(rule)
    await session.commit()
