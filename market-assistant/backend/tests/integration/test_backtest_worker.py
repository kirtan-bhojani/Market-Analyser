import uuid

import numpy as np
import pandas as pd
import pytest

from app.models.backtest import Backtest
from app.workers.backtest_worker import run_backtest_job


def _sine_candles(n=120, period=20, amplitude=10.0, base=100.0):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    t = np.arange(n)
    close = base + amplitude * np.sin(2 * np.pi * t / period)
    return pd.DataFrame({"o": close, "h": close, "l": close, "c": close, "v": 1.0}, index=idx)


@pytest.mark.asyncio
async def test_run_backtest_job_persists_stats_and_equity_curve(db_session, monkeypatch):
    bt_id = uuid.uuid4()
    bt = Backtest(
        id=bt_id,
        strategy="sma_cross",
        params={"fast": 3, "slow": 8},
        universe={"symbol": "BTC/USDT", "tf": "1h"},
        fees_bps=10.0,
        slippage_bps=5.0,
    )
    db_session.add(bt)
    await db_session.commit()

    async def _fake_load(*args, **kwargs):
        return _sine_candles()

    monkeypatch.setattr("app.workers.backtest_worker.load_candles_df", _fake_load)

    ctx = {"db_session": db_session}
    await run_backtest_job(ctx, str(bt_id))

    refreshed = await db_session.get(Backtest, bt_id)
    assert refreshed.status == "done"
    assert refreshed.stats is not None
    assert refreshed.stats["trade_count"] > 0
    assert len(refreshed.equity_curve) == 120
