import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.candle import CandleRow
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule
from app.scanner.worker import on_candle_close

# Loosened so a single test candle can trigger: rsi is always < 100 (unless a
# pure up-run, which our oscillating warm-start history avoids) and rel_volume
# is > 0 for any positive volume once the 20-bar baseline exists.
RULE_DEFINITION = {
    "all": [
        {"ind": "rsi", "tf": "5m", "op": "<", "value": 100},
        {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 0},
    ]
}

# rsi(period=14) needs > 14 closes and rel_volume(period=20) needs a 20-bar
# preceding baseline for the newest bar to be numeric (not NaN). The passed
# test candle is the newest bar, so seeding 30 prior 5m bars makes both rsi and
# rel_volume defined; without this warm-start they'd be NaN and evaluate False.
SEED_BARS = 30
TEST_CANDLE = {"ts": "2026-01-01T00:05:00Z", "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 50}


async def _seed_history(db_session, instrument_id: int) -> None:
    # Oscillating closes (99/100/101) guarantee both gains and losses, so rsi is
    # strictly < 100; constant volume 50 makes rel_volume ~= 1 > 0. All bars
    # precede the test candle's timestamp.
    start = datetime(2025, 12, 31, 0, 0, tzinfo=UTC)
    for i in range(SEED_BARS):
        close = 100 + (i % 3) - 1
        db_session.add(
            CandleRow(
                instrument_id=instrument_id,
                tf="5m",
                ts=start + timedelta(minutes=5 * i),
                o=close,
                h=close + 1,
                l=close - 1,
                c=close,
                v=50,
            )
        )
    await db_session.flush()


@pytest.mark.asyncio
async def test_enabled_rule_writes_hit_and_publishes_event(
    db_session, redis_client, test_user_id, sample_instrument
):
    await _seed_history(db_session, sample_instrument.id)
    rule = ScanRule(
        user_id=test_user_id, name="always-fires", definition=RULE_DEFINITION, enabled=True
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"scan_hits:{test_user_id}")
    # Consume the subscribe confirmation: this round-trip guarantees the server
    # has registered the subscription before the worker publishes (pub/sub does
    # not buffer for not-yet-subscribed clients, so publishing first would race).
    confirm = await pubsub.get_message(timeout=2)
    assert confirm is not None and confirm["type"] == "subscribe"

    hits_written = await on_candle_close(
        {"db": db_session, "redis": redis_client},
        instrument_id=sample_instrument.id,
        tf="5m",
        candle=TEST_CANDLE,
    )
    assert hits_written == 1

    result = await db_session.execute(select(ScanHit).where(ScanHit.rule_id == rule.id))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].instrument_id == sample_instrument.id

    message = None
    for _ in range(20):
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message is not None:
            break
    assert message is not None
    payload = json.loads(message["data"])
    assert payload["rule_id"] == rule.id
    assert payload["instrument_id"] == sample_instrument.id
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_disabled_rule_writes_nothing(
    db_session, redis_client, test_user_id, sample_instrument
):
    await _seed_history(db_session, sample_instrument.id)
    rule = ScanRule(
        user_id=test_user_id, name="disabled", definition=RULE_DEFINITION, enabled=False
    )
    db_session.add(rule)
    await db_session.commit()

    hits_written = await on_candle_close(
        {"db": db_session, "redis": redis_client},
        instrument_id=sample_instrument.id,
        tf="5m",
        candle=TEST_CANDLE,
    )
    assert hits_written == 0


@pytest.mark.asyncio
async def test_same_bar_replayed_twice_dedups(
    db_session, redis_client, test_user_id, sample_instrument
):
    await _seed_history(db_session, sample_instrument.id)
    rule = ScanRule(
        user_id=test_user_id, name="always-fires", definition=RULE_DEFINITION, enabled=True
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)

    ctx = {"db": db_session, "redis": redis_client}
    first = await on_candle_close(
        ctx, instrument_id=sample_instrument.id, tf="5m", candle=TEST_CANDLE
    )
    second = await on_candle_close(
        ctx, instrument_id=sample_instrument.id, tf="5m", candle=TEST_CANDLE
    )

    assert first == 1
    assert second == 0
    result = await db_session.execute(select(ScanHit).where(ScanHit.rule_id == rule.id))
    assert len(result.scalars().all()) == 1
