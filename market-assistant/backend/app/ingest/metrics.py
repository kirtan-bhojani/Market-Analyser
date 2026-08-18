import time
from typing import Protocol


class SupportsRedisKV(Protocol):
    async def set(self, name: str, value: str) -> object: ...

    async def get(self, name: str) -> str | bytes | None: ...


async def record_heartbeat(redis: SupportsRedisKV, source: str) -> None:
    await redis.set(f"ingest:heartbeat:{source}", str(time.time()))


async def get_heartbeat_age(redis: SupportsRedisKV, source: str) -> float:
    value = await redis.get(f"ingest:heartbeat:{source}")
    if value is None:
        return float("inf")
    return time.time() - float(value)
