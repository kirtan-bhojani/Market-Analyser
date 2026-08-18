import uuid

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.backtest import BacktestCreateRequest, BacktestResponse
from app.core.auth import get_current_user_id
from app.core.deps import get_arq_pool, get_session
from app.models.backtest import Backtest

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=BacktestResponse)
async def create_backtest(
    request: BacktestCreateRequest,
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> BacktestResponse:
    bt = Backtest(
        id=uuid.uuid4(),
        user_id=user_id,
        strategy=request.strategy,
        params=request.params,
        universe=request.universe,
        start_ts=request.start_ts,
        end_ts=request.end_ts,
        fees_bps=request.fees_bps,
        slippage_bps=request.slippage_bps,
        status="pending",
    )
    session.add(bt)
    await session.commit()
    await arq_pool.enqueue_job("run_backtest_job", str(bt.id))
    return BacktestResponse(id=bt.id, status=bt.status)


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> BacktestResponse:
    bt = await session.get(Backtest, backtest_id)
    # Owner-scoped: a mismatch (including a NULL owner on a pre-ownership row)
    # 404s rather than 403 so a caller can't probe which ids exist.
    if bt is None or bt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest not found")
    return BacktestResponse(
        id=bt.id, status=bt.status, stats=bt.stats, equity_curve=bt.equity_curve
    )
