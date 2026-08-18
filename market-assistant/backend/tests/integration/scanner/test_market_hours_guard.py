from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.candle import CandleRow
from app.models.instrument import Instrument
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule
from app.scanner.worker import on_candle_close

IST = ZoneInfo("Asia/Kolkata")

# Same loosened always-fire rule as test_worker.py: rsi < 100 (our oscillating
# warm-start avoids a pure up-run) and rel_volume > 0 once the 20-bar baseline
# exists. 2025-06-09 is a Monday and not an NSE holiday, so the session gate is
# the only thing that differs between the two tests below.
RULE_DEFINITION = {
    "all": [
        {"ind": "rsi", "tf": "5m", "op": "<", "value": 100},
        {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 0},
    ]
}
SEED_BARS = 30


async def _seed_history(db_session, instrument_id: int, candle_ts: datetime) -> None:
    # Seed SEED_BARS oscillating 5m bars strictly preceding candle_ts so rsi(14)
    # and rel_volume(20) are numeric for the newest (test) bar.
    start = candle_ts - timedelta(minutes=5 * SEED_BARS)
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


async def _make_equity(db_session) -> Instrument:
    instrument = Instrument(
        symbol="RELIANCE.NS", asset_class="equity", exchange="NSE", active=True
    )
    db_session.add(instrument)
    await db_session.flush()
    return instrument


@pytest.mark.asyncio
async def test_scanner_skips_equity_event_outside_nse_session(
    db_session, redis_client, test_user_id
):
    instrument = await _make_equity(db_session)
    ts_utc = datetime(2025, 6, 9, 20, 0, tzinfo=IST).astimezone(UTC)
    await _seed_history(db_session, instrument.id, ts_utc)
    rule = ScanRule(
        user_id=test_user_id, name="always-fire", definition=RULE_DEFINITION, enabled=True
    )
    db_session.add(rule)
    await db_session.commit()

    candle = {
        "ts": ts_utc.isoformat().replace("+00:00", "Z"),
        "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 50,
    }
    hits = await on_candle_close(
        {"db": db_session, "redis": redis_client},
        instrument_id=instrument.id, tf="5m", candle=candle,
    )
    assert hits == 0

    result = await db_session.execute(
        select(ScanHit).where(ScanHit.instrument_id == instrument.id)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_scanner_fires_equity_event_inside_nse_session(
    db_session, redis_client, test_user_id
):
    instrument = await _make_equity(db_session)
    ts_utc = datetime(2025, 6, 9, 10, 0, tzinfo=IST).astimezone(UTC)
    await _seed_history(db_session, instrument.id, ts_utc)
    rule = ScanRule(
        user_id=test_user_id, name="always-fire", definition=RULE_DEFINITION, enabled=True
    )
    db_session.add(rule)
    await db_session.commit()

    candle = {
        "ts": ts_utc.isoformat().replace("+00:00", "Z"),
        "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 50,
    }
    hits = await on_candle_close(
        {"db": db_session, "redis": redis_client},
        instrument_id=instrument.id, tf="5m", candle=candle,
    )
    assert hits >= 1

    result = await db_session.execute(
        select(ScanHit).where(ScanHit.instrument_id == instrument.id)
    )
    assert len(result.scalars().all()) >= 1
