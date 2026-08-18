import uuid

import pytest
from httpx import AsyncClient

from app.models.scan_rule import ScanRule


async def _seed_rule(db_session, user_id: uuid.UUID) -> ScanRule:
    rule = ScanRule(
        user_id=user_id,
        name="RSI dip",
        definition={"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
        enabled=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest.mark.asyncio
async def test_create_and_list_own_subscription(
    client: AsyncClient, auth_headers: dict, db_session, test_user_id: uuid.UUID
):
    rule = await _seed_rule(db_session, test_user_id)

    resp = await client.post(
        "/api/alert-subscriptions",
        json={"rule_id": rule.id, "channel": "telegram", "target": "12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["rule_id"] == rule.id
    assert body["channel"] == "telegram"
    assert body["target"] == "12345"
    assert body["user_id"] == str(test_user_id)
    assert "id" in body

    resp2 = await client.get("/api/alert-subscriptions", headers=auth_headers)
    assert resp2.status_code == 200
    listed = resp2.json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_create_subscription_for_other_users_rule_returns_404(
    client: AsyncClient, auth_headers: dict, db_session, other_user_id: uuid.UUID
):
    rule = await _seed_rule(db_session, other_user_id)

    resp = await client.post(
        "/api/alert-subscriptions",
        json={"rule_id": rule.id, "channel": "telegram", "target": "12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_own_subscription_then_others_404(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    db_session,
    test_user_id: uuid.UUID,
):
    rule = await _seed_rule(db_session, test_user_id)
    created = (
        await client.post(
            "/api/alert-subscriptions",
            json={"rule_id": rule.id, "channel": "telegram", "target": "12345"},
            headers=auth_headers,
        )
    ).json()

    resp_other = await client.delete(
        f"/api/alert-subscriptions/{created['id']}", headers=other_user_headers
    )
    assert resp_other.status_code == 404

    resp = await client.delete(f"/api/alert-subscriptions/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp_list = await client.get("/api/alert-subscriptions", headers=auth_headers)
    assert resp_list.json() == []
