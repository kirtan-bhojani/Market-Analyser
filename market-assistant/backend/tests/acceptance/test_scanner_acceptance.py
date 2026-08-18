"""Phase 4 acceptance: build a rule, replay synthetic data, hit within 2s.

Builds the golden ``rsi<30 AND rel_volume>2`` rule via the public
``POST /api/scanner/rules`` endpoint, subscribes to the user's ``scan_hits``
pub/sub channel, replays the synthetic candle series through the production
``on_candle_close`` path, and asserts a hit event arrives in under 2 seconds
with the expected rule name.
"""

import json
import time

import pytest

RULE_DEFINITION = {
    "all": [
        {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
        {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
    ]
}


@pytest.mark.acceptance
async def test_rsi_dip_and_relvol_spike_hit_appears_within_2s(
    client, auth_headers, test_user_id, redis_client, sample_instrument, replay_synthetic_candles
):
    created = await client.post(
        "/api/scanner/rules",
        json={"name": "RSI(5m)<30 AND relVol>2", "definition": RULE_DEFINITION},
        headers=auth_headers,
    )
    assert created.status_code == 201

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"scan_hits:{test_user_id}")
    try:
        start = time.monotonic()
        await replay_synthetic_candles(
            instrument_id=sample_instrument.id, tf="5m", scenario="rsi_dip_with_volume_spike"
        )

        message = None
        while time.monotonic() - start < 2.0:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if message:
                break

        elapsed = time.monotonic() - start
        assert message is not None, "no scan_hits event received within 2s of candle close"
        assert elapsed < 2.0, f"hit latency {elapsed:.3f}s exceeded 2s budget"

        payload = json.loads(message["data"])
        assert payload["rule_name"] == "RSI(5m)<30 AND relVol>2"
        assert payload["tf"] == "5m"
        assert payload["instrument_id"] == sample_instrument.id
    finally:
        await pubsub.unsubscribe(f"scan_hits:{test_user_id}")
        await pubsub.aclose()
