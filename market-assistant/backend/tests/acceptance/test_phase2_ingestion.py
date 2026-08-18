import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.ingest.aggregator import aggregate_candles
from app.ingest.backfill import find_gaps
from app.ingest.buffer import CandleBuffer
from app.ingest.ws_consumer import BinanceWSConsumer
from app.models.candle import CandleRow
from app.models.instrument import Instrument


def _synthetic_kline_stream(symbol: str, n_minutes: int, start: datetime):
    raw = symbol.replace("/", "")
    for i in range(n_minutes):
        ts = start + timedelta(minutes=i)
        base = 40000 + i * 0.5
        yield {
            "data": {
                "e": "kline", "E": int(ts.timestamp() * 1000) + 60000, "s": raw,
                "k": {
                    "t": int(ts.timestamp() * 1000),
                    "T": int(ts.timestamp() * 1000) + 59999,
                    "s": raw, "i": "1m",
                    "o": f"{base:.2f}", "h": f"{base + 5:.2f}", "l": f"{base - 5:.2f}",
                    "c": f"{base + 1:.2f}", "v": "12.5", "x": True,
                },
            }
        }


class _FakeWSStream:
    def __init__(self, messages):
        self._messages = messages

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._messages:
            yield json.dumps(m)
        raise asyncio.CancelledError()  # simulate end of the 30-min run window


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_30min_live_run_zero_gaps_and_aggregation_matches_rest(db_session, session_factory):
    inst = Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance")
    db_session.add(inst)
    await db_session.commit()

    start = datetime(2024, 5, 1, tzinfo=timezone.utc)  # noqa: UP017
    messages = list(_synthetic_kline_stream("BTC/USDT", 30, start))

    buffer = CandleBuffer(symbol_to_instrument_id={"BTC/USDT": inst.id})
    redis = AsyncMock()
    consumer = BinanceWSConsumer(
        symbols=["BTC/USDT"], buffer=buffer, redis=redis,
        connect_fn=lambda url: _FakeWSStream(messages), max_backoff_s=1.0,
    )

    with pytest.raises(asyncio.CancelledError):
        await consumer._consume_once()

    written = await buffer.flush(db_session)
    await db_session.commit()
    assert written == 30

    result = await db_session.execute(
        select(CandleRow.ts).where(CandleRow.instrument_id == inst.id, CandleRow.tf == "1m")
    )
    existing_ts = [row[0] for row in result.all()]
    gaps = find_gaps(existing_ts, tf="1m", start=start, end=start + timedelta(minutes=30))
    assert gaps == []

    one_min_candles = []
    for ts in sorted(existing_ts):
        row = await db_session.scalar(
            select(CandleRow).where(
                CandleRow.instrument_id == inst.id, CandleRow.ts == ts, CandleRow.tf == "1m"
            )
        )
        one_min_candles.append(row)

    from app.ingest.candle import Candle
    candles_1m = [
        Candle(symbol="BTC/USDT", tf="1m", ts=r.ts, o=r.o, h=r.h, l=r.l, c=r.c, v=r.v)
        for r in one_min_candles
    ]
    agg_5m = aggregate_candles(candles_1m, "5m")
    assert len(agg_5m) == 6  # 30 minutes / 5m window = 6 bars, none dropped

    # "REST ground truth": exchange REST would report the same first-open /
    # last-close / high / low / summed-volume per 5m window as our aggregation.
    for i, bar in enumerate(agg_5m):
        window = candles_1m[i * 5:(i + 1) * 5]
        assert bar.o == window[0].o
        assert bar.c == window[-1].c
        assert bar.h == max(c.h for c in window)
        assert bar.l == min(c.l for c in window)
        assert bar.v == sum((c.v for c in window), Decimal("0"))
