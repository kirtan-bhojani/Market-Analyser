import json
from typing import Any

from redis.asyncio import Redis


def candle_channel(symbol: str, tf: str) -> str:
    return f"candles:{symbol}:{tf}"


async def publish_candle_update(
    redis: Redis, symbol: str, tf: str, candle: dict[str, Any]
) -> None:
    channel = candle_channel(symbol, tf)
    await redis.publish(channel, json.dumps(candle))
