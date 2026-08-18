import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.backtest import Backtest


@pytest.mark.asyncio
async def test_backtest_requires_fees_and_slippage_bps(db_session):
    bt = Backtest(
        id=uuid.uuid4(),
        strategy="sma_cross",
        params={"fast": 3, "slow": 8},
        universe={"symbols": ["BTC/USDT"]},
        fees_bps=None,  # violates NOT NULL
        slippage_bps=5.0,
    )
    db_session.add(bt)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_backtest_persists_with_required_fields(db_session):
    bt = Backtest(
        id=uuid.uuid4(),
        strategy="sma_cross",
        params={"fast": 3, "slow": 8},
        universe={"symbols": ["BTC/USDT"]},
        fees_bps=10.0,
        slippage_bps=5.0,
    )
    db_session.add(bt)
    await db_session.commit()

    fetched = await db_session.get(Backtest, bt.id)
    assert fetched is not None
    assert fetched.fees_bps == 10.0
    assert fetched.status == "pending"
