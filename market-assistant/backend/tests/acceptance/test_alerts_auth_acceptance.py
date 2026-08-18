"""Phase 11 acceptance: security + alerting guarantees end-to-end.

1. Cross-user data isolation across scan_rules, chat_sessions, and
   alert_subscriptions (test env, X-Dev-User stub).
2. Anonymous requests are rejected with 401 when env=prod.
3. A Telegram alert for a scan hit is delivered (bot API mocked) in well
   under the 5s phase budget.
"""

import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.alerts.telegram import TelegramSendResult
from app.core.config import get_settings
from app.models.alert_subscription import AlertSubscription
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule
from app.workers import alert_worker

VALID_RULE = {
    "name": "RSI dip + volume spike",
    "definition": {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    },
}


@pytest.fixture
def prod_settings(monkeypatch):
    """Flip the cached settings singleton to prod for the duration of a test."""
    s = get_settings()
    monkeypatch.setattr(s, "env", "prod")
    return s


@pytest.mark.acceptance
async def test_cross_user_isolation_across_rules_sessions_and_subscriptions(
    client: AsyncClient, auth_headers: dict, other_user_headers: dict
):
    # User A creates one of each resource.
    rule_resp = await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    assert rule_resp.status_code == 201
    rule_id = rule_resp.json()["id"]

    session_resp = await client.post("/api/chat/sessions", headers=auth_headers)
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    sub_resp = await client.post(
        "/api/alert-subscriptions",
        json={"rule_id": rule_id, "channel": "telegram", "target": "111"},
        headers=auth_headers,
    )
    assert sub_resp.status_code == 201
    sub_id = sub_resp.json()["id"]

    # User B sees none of A's resources.
    b_rules = await client.get("/api/scanner/rules", headers=other_user_headers)
    assert b_rules.status_code == 200
    assert rule_id not in [r["id"] for r in b_rules.json()]

    b_sessions = await client.get("/api/chat/sessions", headers=other_user_headers)
    assert b_sessions.status_code == 200
    assert session_id not in [s["id"] for s in b_sessions.json()]

    b_subs = await client.get("/api/alert-subscriptions", headers=other_user_headers)
    assert b_subs.status_code == 200
    assert sub_id not in [s["id"] for s in b_subs.json()]

    # User B cannot subscribe to A's rule (existence is not even revealed).
    b_sub_attempt = await client.post(
        "/api/alert-subscriptions",
        json={"rule_id": rule_id, "channel": "telegram", "target": "222"},
        headers=other_user_headers,
    )
    assert b_sub_attempt.status_code == 404

    # User A still sees all three of its own resources.
    a_rules = await client.get("/api/scanner/rules", headers=auth_headers)
    assert rule_id in [r["id"] for r in a_rules.json()]
    a_sessions = await client.get("/api/chat/sessions", headers=auth_headers)
    assert session_id in [s["id"] for s in a_sessions.json()]
    a_subs = await client.get("/api/alert-subscriptions", headers=auth_headers)
    assert sub_id in [s["id"] for s in a_subs.json()]


@pytest.mark.acceptance
async def test_prod_rejects_anonymous_with_401(client: AsyncClient, prod_settings):
    for path in ("/api/scanner/rules", "/api/alert-subscriptions", "/api/chat/sessions"):
        resp = await client.get(path)
        assert resp.status_code == 401, f"{path}: expected 401, got {resp.status_code}"


@pytest.mark.acceptance
async def test_telegram_alert_delivered_within_5s(
    db_session,
    session_factory,
    redis_client,
    sample_instrument,
    monkeypatch,
):
    user_id = uuid.uuid4()
    rule = ScanRule(user_id=user_id, name="always-fires", definition={"all": []}, enabled=True)
    db_session.add(rule)
    await db_session.flush()
    hit = ScanHit(
        rule_id=rule.id,
        instrument_id=sample_instrument.id,
        ts=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
        payload={"rsi": 42.0},
    )
    db_session.add(hit)
    db_session.add(
        AlertSubscription(user_id=user_id, rule_id=rule.id, channel="telegram", target="12345")
    )
    await db_session.commit()
    await db_session.refresh(hit)

    monkeypatch.setattr(get_settings(), "telegram_bot_token", "test-bot-token")
    send_mock = AsyncMock(return_value=TelegramSendResult(ok=True, status_code=200))
    monkeypatch.setattr(alert_worker, "send_telegram_message", send_mock)

    ctx = {"session_factory": session_factory, "redis": redis_client}
    start = time.monotonic()
    sent = await alert_worker.send_telegram_alert_job(ctx, hit.id)
    elapsed = time.monotonic() - start

    assert sent == 1
    send_mock.assert_called_once()
    assert send_mock.call_args.args[1] == "12345"
    assert elapsed < 5.0, f"alert delivery took {elapsed:.3f}s, over the 5s budget"
