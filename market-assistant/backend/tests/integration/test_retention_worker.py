"""Phase 12 Task 4 (integration): retention deletes only 1m candles > retention window.

Runs against the real test Postgres (db_session fixture). 5m/1h rows are never
touched regardless of age.
"""

from datetime import UTC, datetime, timedelta

from app.core.retention import drop_old_candles
from app.models.candle import CandleRow


async def test_retention_deletes_only_1m_candles_older_than_60_days(
    db_session, sample_instrument
):
    now = datetime(2026, 7, 10, tzinfo=UTC)
    db_session.add_all(
        [
            CandleRow(instrument_id=sample_instrument.id, tf="1m",
                      ts=now - timedelta(days=0), o=1, h=1, l=1, c=1, v=1),
            CandleRow(instrument_id=sample_instrument.id, tf="1m",
                      ts=now - timedelta(days=59), o=1, h=1, l=1, c=1, v=1),
            CandleRow(instrument_id=sample_instrument.id, tf="1m",
                      ts=now - timedelta(days=61), o=1, h=1, l=1, c=1, v=1),
            CandleRow(instrument_id=sample_instrument.id, tf="1h",
                      ts=now - timedelta(days=400), o=1, h=1, l=1, c=1, v=1),
        ]
    )
    await db_session.flush()

    deleted = await drop_old_candles(db_session, tf="1m", older_than_days=60, now=now)
    assert deleted == 1

    from sqlalchemy import select

    remaining = (await db_session.execute(select(CandleRow))).scalars().all()
    assert len(remaining) == 3
    assert all(
        not (r.tf == "1m" and r.ts < now - timedelta(days=60)) for r in remaining
    )
