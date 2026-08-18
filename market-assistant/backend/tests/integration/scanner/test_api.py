import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import create_app

VALID_RULE = {
    "name": "RSI dip + volume spike",
    "definition": {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    },
}


@pytest.mark.asyncio
async def test_create_rule_returns_201_with_id(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == VALID_RULE["name"]
    assert body["enabled"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_create_rule_with_invalid_dsl_returns_422(client: AsyncClient, auth_headers: dict):
    bad_rule = {"name": "bad", "definition": {"ind": "not_real", "tf": "5m", "op": "<", "value": 1}}
    resp = await client.post("/api/scanner/rules", json=bad_rule, headers=auth_headers)
    assert resp.status_code == 422
    assert "ind" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_rules_scoped_to_current_user(
    client: AsyncClient, auth_headers: dict, other_user_headers: dict
):
    await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    resp = await client.get("/api/scanner/rules", headers=other_user_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_patch_toggles_enabled(client: AsyncClient, auth_headers: dict):
    created = (
        await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    ).json()
    resp = await client.patch(
        f"/api/scanner/rules/{created['id']}", json={"enabled": False}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_delete_removes_rule(client: AsyncClient, auth_headers: dict):
    created = (
        await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    ).json()
    resp = await client.delete(f"/api/scanner/rules/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/scanner/rules/{created['id']}", headers=auth_headers)
    assert resp2.status_code == 404


def test_ws_hits_channel_streams_published_event(redis_sync_client):
    user_id = uuid.uuid4()
    token = str(user_id)  # dev stub: the token IS the user's UUID
    with TestClient(create_app()) as tc:
        with tc.websocket_connect(f"/ws/scanner/hits?token={token}") as ws:
            time.sleep(0.2)  # let the server complete SUBSCRIBE before we publish
            redis_sync_client.publish(
                f"scan_hits:{user_id}",
                json.dumps(
                    {
                        "rule_id": 1,
                        "instrument_id": 2,
                        "tf": "5m",
                        "ts": "2026-01-01T00:05:00Z",
                        "payload": {},
                    }
                ),
            )
            received = json.loads(ws.receive_text())
            assert received["rule_id"] == 1
            assert received["instrument_id"] == 2
