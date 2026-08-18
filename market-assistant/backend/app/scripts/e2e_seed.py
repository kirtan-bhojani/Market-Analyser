"""Idempotent seed for the full-stack e2e (H11): ensure instrument id=1 exists.

The Playwright scanner spec (and its test-only replay route) drives
``instrument_id=1``. A CandleRow FK requires that instrument to exist, so this
seeds a crypto instrument with an explicit id=1 (crypto is in-session 24/7, so
the scanner's session gate never blocks the replay). Safe to run repeatedly:
if id=1 is already present it is a no-op. Run with ENV=test.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.deps import get_sessionmaker
from app.models.instrument import Instrument

E2E_INSTRUMENT_ID = 1


async def seed() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        existing = (
            await session.execute(
                select(Instrument).where(Instrument.id == E2E_INSTRUMENT_ID)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return
        # A collision-proof symbol/exchange (never emitted by the real crypto or
        # NSE seeders) so this is safe on a shared DB. asset_class="crypto" keeps
        # the instrument in-session 24/7 so the scanner never gates the replay.
        session.add(
            Instrument(
                id=E2E_INSTRUMENT_ID,
                symbol="E2E-SCANNER",
                asset_class="crypto",
                exchange="e2e",
                active=True,
            )
        )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
