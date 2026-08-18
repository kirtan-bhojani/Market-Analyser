import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtest.runner import run_backtest
from app.backtest.serialization import serialize_equity_curve
from app.backtest.strategies import SmaCrossStrategy
from app.core.deps import get_sessionmaker
from app.models.backtest import Backtest
from app.models.candle import CandleRow
from app.models.instrument import Instrument

STRATEGY_REGISTRY = {
    "sma_cross": SmaCrossStrategy,
}


def _to_float(value: Decimal | None) -> float:
    """Coerce a nullable Numeric column to float (missing OHLCV → 0.0)."""
    return float(value) if value is not None else 0.0


async def load_candles_df(
    session: AsyncSession,
    symbol: str,
    tf: str,
    start: datetime | None,
    end: datetime | None,
) -> pd.DataFrame:
    """Load OHLCV candles for `symbol`/`tf` in [start, end] into a DataFrame
    indexed by ts with float columns o/h/l/c/v."""
    instrument_id = (
        await session.execute(select(Instrument.id).where(Instrument.symbol == symbol))
    ).scalars().first()
    if instrument_id is None:
        return pd.DataFrame(columns=["o", "h", "l", "c", "v"])

    stmt = select(CandleRow).where(
        CandleRow.instrument_id == instrument_id,
        CandleRow.tf == tf,
    )
    if start is not None:
        stmt = stmt.where(CandleRow.ts >= start)
    if end is not None:
        stmt = stmt.where(CandleRow.ts <= end)
    stmt = stmt.order_by(CandleRow.ts.asc())

    rows = (await session.execute(stmt)).scalars().all()
    index = pd.DatetimeIndex([r.ts for r in rows], name="ts")
    return pd.DataFrame(
        {
            "o": [_to_float(r.o) for r in rows],
            "h": [_to_float(r.h) for r in rows],
            "l": [_to_float(r.l) for r in rows],
            "c": [_to_float(r.c) for r in rows],
            "v": [_to_float(r.v) for r in rows],
        },
        index=index,
    )


async def _run(session: AsyncSession, backtest_id: str) -> None:
    bt = await session.get(Backtest, uuid.UUID(backtest_id))
    if bt is None:
        return
    try:
        strategy_name = bt.strategy
        params = bt.params
        universe = bt.universe
        if strategy_name is None or params is None or universe is None:
            raise ValueError("backtest row missing strategy/params/universe")
        strategy = STRATEGY_REGISTRY[strategy_name]()
        symbol = universe["symbol"]
        tf = universe["tf"]
        # Annualization must know the asset's trading calendar (24/7 crypto vs
        # NSE session); default to crypto if the instrument row is missing.
        asset_class = await session.scalar(
            select(Instrument.asset_class).where(Instrument.symbol == symbol).limit(1)
        )
        candles = await load_candles_df(session, symbol, tf, bt.start_ts, bt.end_ts)
        result = run_backtest(
            strategy=strategy,
            candles=candles,
            params=params,
            fees_bps=float(bt.fees_bps),
            slippage_bps=float(bt.slippage_bps),
            timeframe=tf,
            asset_class=asset_class or "crypto",
        )
        bt.stats = result.stats
        bt.equity_curve = serialize_equity_curve(result.equity_curve)
        bt.status = "done"
    except Exception as exc:  # noqa: BLE001 - persisted for API/UI visibility
        bt.status = "failed"
        bt.stats = {"error": str(exc)}
    await session.commit()


async def run_backtest_job(ctx: dict[str, Any], backtest_id: str) -> None:
    session = ctx.get("db_session")
    if session is not None:
        await _run(session, backtest_id)
    else:
        async with get_sessionmaker()() as own_session:
            await _run(own_session, backtest_id)
