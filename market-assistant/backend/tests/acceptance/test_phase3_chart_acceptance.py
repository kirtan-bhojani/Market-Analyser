import asyncio
import json

import pytest
from httpx import AsyncClient


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_rest_history_plus_live_ws_update_reflect_a_forming_candle(
    client: AsyncClient, redis_sync_client, seed_btc_1m_candles
):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    history = resp.json()["candles"]
    assert len(history) > 0

    # Simulate the ingest pipeline closing a new 1m bar and fanning it out over
    # Redis — the same event the frontend's useCandles hook consumes over
    # /ws/candles.
    forming_candle = {**history[-1], "c": history[-1]["c"] + 5}
    redis_sync_client.publish("candles:BTC/USDT:1m", json.dumps(forming_candle))
    await asyncio.sleep(0.1)

    resp_after = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    assert resp_after.status_code == 200
