from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.alerts.telegram import TelegramSendResult
from app.core.config import get_settings
from app.models.alert_subscription import AlertSubscription
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule
from app.workers import alert_worker

HIT_TS = datetime(2026, 1, 1, 0, 5, tzinfo=UTC)


async def _seed_hit(db_session, instrument_id: int, user_id):
    rule = ScanRule(
        user_id=user_id, name="always-fires", definition={"all": []}, enabled=True
    )
    db_session.add(rule)
    await db_session.flush()
    hit = ScanHit(
        rule_id=rule.id,
        instrument_id=instrument_id,
        ts=HIT_TS,
        payload={"rsi": 42.0},
    )
    db_session.add(hit)
    await db_session.commit()
    await db_session.refresh(hit)
    return rule, hit


@pytest.fixture
def _telegram_settings():
    # Populate a bot token so the job does not early-return, restore afterwards.
    settings = get_settings()
    original = settings.telegram_bot_token
    settings.telegram_bot_token = "test-bot-token"
    try:
        yield settings
    finally:
        settings.telegram_bot_token = original


@pytest.mark.asyncio
async def test_subscribed_user_receives_telegram_alert(
    db_session,
    session_factory,
    redis_client,
    test_user_id,
    sample_instrument,
    monkeypatch,
    _telegram_settings,
):
    rule, hit = await _seed_hit(db_session, sample_instrument.id, test_user_id)
    db_session.add(
        AlertSubscription(
            user_id=test_user_id, rule_id=rule.id, channel="telegram", target="12345"
        )
    )
    await db_session.commit()

    send_mock = AsyncMock(return_value=TelegramSendResult(ok=True, status_code=200))
    monkeypatch.setattr(alert_worker, "send_telegram_message", send_mock)

    ctx = {"session_factory": session_factory, "redis": redis_client}
    sent = await alert_worker.send_telegram_alert_job(ctx, hit.id)

    assert sent == 1
    send_mock.assert_called_once()
    assert send_mock.call_args.args[1] == "12345"


@pytest.mark.asyncio
async def test_no_subscription_sends_nothing(
    db_session,
    session_factory,
    redis_client,
    test_user_id,
    sample_instrument,
    monkeypatch,
    _telegram_settings,
):
    _rule, hit = await _seed_hit(db_session, sample_instrument.id, test_user_id)

    send_mock = AsyncMock(return_value=TelegramSendResult(ok=True, status_code=200))
    monkeypatch.setattr(alert_worker, "send_telegram_message", send_mock)

    ctx = {"session_factory": session_factory, "redis": redis_client}
    sent = await alert_worker.send_telegram_alert_job(ctx, hit.id)

    assert sent == 0
    send_mock.assert_not_called()
