from collections.abc import Iterable

from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pubsub import publish_candle_update
from app.ingest.candle import Candle
from app.models.candle import CandleRow


async def upsert_candles(
    session: AsyncSession,
    instrument_id: int,
    candles: list[Candle],
) -> int:
    """Batch upsert candles for one instrument. Idempotent on (instrument_id, tf, ts).

    Pure DB write — the Redis fan-out is deliberately NOT done here. Publish only
    AFTER the caller commits (see ``publish_candles``), so a WebSocket subscriber
    can never observe a candle whose row a later rollback discarded.
    """
    if not candles:
        return 0

    rows = [
        {
            "instrument_id": instrument_id,
            "tf": c.tf,
            "ts": c.ts,
            "o": c.o,
            "h": c.h,
            "l": c.l,
            "c": c.c,
            "v": c.v,
        }
        for c in candles
    ]

    stmt = insert(CandleRow).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[CandleRow.instrument_id, CandleRow.tf, CandleRow.ts],
        set_={
            "o": stmt.excluded.o,
            "h": stmt.excluded.h,
            "l": stmt.excluded.l,
            "c": stmt.excluded.c,
            "v": stmt.excluded.v,
        },
    )
    await session.execute(stmt)
    return len(rows)


async def publish_candles(redis: Redis, candles: Iterable[Candle]) -> None:
    """Fan out committed candles to their Redis pub/sub channels for the WS feed.

    Call this ONLY after the DB commit succeeds — publishing pre-commit risks
    surfacing a candle that a rollback later discarded.
    """
    for c in candles:
        await publish_candle_update(
            redis,
            c.symbol,
            c.tf,
            {
                "ts": c.ts.isoformat(),
                "o": float(c.o),
                "h": float(c.h),
                "l": float(c.l),
                "c": float(c.c),
                "v": float(c.v),
            },
        )
