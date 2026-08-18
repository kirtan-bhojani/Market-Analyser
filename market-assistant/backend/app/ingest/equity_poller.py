"""Session-aware, idempotent NIFTY-50 equity poller (arq task).

Runs on a 15-minute cron. Outside NSE trading hours it is a no-op. Inside a
session it refreshes the trailing window of 1-minute candles for every equity
instrument via ``fetch_candles`` and persists them with ``upsert_candles``,
which is idempotent on ``(instrument_id, tf, ts)`` and (when a Redis handle is
supplied) fans each written candle out over Phase-3 pub/sub.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.ingest.candle import Candle
from app.ingest.nse_calendar import IST, is_in_session
from app.ingest.universe_equity import ensure_equity_instruments
from app.ingest.writer import publish_candles, upsert_candles
from app.ingest.yfinance_adapter import fetch_candles

POLL_TF = "1m"


async def poll_equity_universe(ctx: dict[str, Any]) -> int:
    """Poll the NIFTY-50 equity universe for fresh 1m candles.

    Returns the total number of candles upserted. Returns 0 when called
    outside an NSE trading session (weekend/holiday/pre-open/post-close).
    """
    settings = get_settings()
    now = datetime.now(IST)

    if not is_in_session(now):
        return 0

    redis = ctx["redis"]

    # Context-manage the session so its connection is returned to the pool on
    # every tick (and on any error mid-loop); a bare factory() call leaked one
    # connection per 15-minute run.
    async with ctx["session_factory"]() as session:
        instruments = await ensure_equity_instruments(session)

        # Look back twice the poll interval so a delayed or skipped run still
        # sweeps the gap; upsert is idempotent on (instrument_id, tf, ts) so the
        # overlap re-writes nothing new.
        start = now - timedelta(minutes=2 * settings.EQUITY_POLL_INTERVAL_MIN)
        total_written = 0

        polled: list[Candle] = []
        for instrument in instruments:
            raw_symbol = instrument.symbol.removesuffix(".NS")
            # fetch_candles is a blocking yfinance call; run it off the event
            # loop so the poller doesn't stall the worker's other coroutines.
            candles = await asyncio.to_thread(fetch_candles, raw_symbol, POLL_TF, start, now)
            if not candles:
                continue
            written = await upsert_candles(session, instrument.id, candles)
            total_written += written
            polled.extend(candles)

        await session.commit()
        # Fan out to the WS feed only after the commit succeeds.
        await publish_candles(redis, polled)
        return total_written
