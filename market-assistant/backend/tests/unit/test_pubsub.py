import json
from unittest.mock import AsyncMock

import pytest

from app.core.pubsub import candle_channel, publish_candle_update


def test_candle_channel_naming():
    assert candle_channel("BTC/USDT", "1m") == "candles:BTC/USDT:1m"


@pytest.mark.asyncio
async def test_publish_candle_update_publishes_to_correct_channel():
    redis = AsyncMock()
    candle = {"ts": "2024-01-01T00:00:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 100}

    await publish_candle_update(redis, "BTC/USDT", "1m", candle)

    redis.publish.assert_awaited_once_with("candles:BTC/USDT:1m", json.dumps(candle))
