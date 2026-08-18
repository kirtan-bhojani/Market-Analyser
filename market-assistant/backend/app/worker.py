# worker.py = the arq entrypoint (WorkerSettings + lifecycle hooks).
# app/workers/ = the job implementations (e.g. news_worker.run_news_ingest).
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from arq import create_pool, cron
from arq.connections import RedisSettings
from arq.cron import CronJob
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.deps import get_redis, get_sessionmaker
from app.ingest.backfill import backfill_gaps
from app.ingest.equity_poller import poll_equity_universe
from app.models.instrument import Instrument
from app.scanner.worker import scan_on_candle_close_job
from app.strategies.worker import on_candle_close_job
from app.workers.alert_worker import send_telegram_alert_job
from app.workers.backtest_worker import run_backtest_job
from app.workers.ml_inference_worker import run_ml_inference_job
from app.workers.news_worker import run_news_ingest
from app.workers.retention_worker import retention_job

logger = logging.getLogger(__name__)

# Rolling window the periodic sweep re-checks for gaps on each active instrument.
_BACKFILL_SWEEP_WINDOW = timedelta(hours=1)
_BACKFILL_SWEEP_TF = "1m"


def warn_if_telegram_unconfigured(settings: Settings) -> None:
    """telegram_bot_token is intentionally optional in prod (config fail-fast does
    not require it), so surface a loud startup warning when it is unset instead of
    silently dropping every alert."""
    if not settings.telegram_bot_token:
        logger.warning(
            "telegram_bot_token is not set — Telegram alert delivery is disabled; "
            "set it to enable scanner alert fan-out"
        )


async def trigger_backfill_sweep(ctx: dict[str, Any]) -> int:
    """Periodic cron trigger: for every active instrument, detect and fill any
    gaps in the trailing window via ``backfill_gaps`` (same ctx contract)."""
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.symbol).where(
                Instrument.active.is_(True),
                # The sweep backfills via the CCXT binance exchange, which only
                # knows crypto pairs; equity/other instruments have no binance
                # symbol and would error every run.
                Instrument.asset_class == "crypto",
            )
        )
        instruments = result.all()

    end_ts = datetime.now(UTC)
    start_ts = end_ts - _BACKFILL_SWEEP_WINDOW
    total = 0
    for instrument_id, symbol in instruments:
        # Isolate per-instrument failures (a delisted symbol, a transient CCXT
        # error) so one bad instrument never aborts the whole sweep.
        try:
            total += await backfill_gaps(
                ctx, instrument_id, symbol, _BACKFILL_SWEEP_TF, start_ts, end_ts
            )
        except Exception:
            logger.warning(
                "backfill sweep failed for instrument %s (%s); continuing",
                instrument_id,
                symbol,
                exc_info=True,
            )
    return total


async def on_startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    warn_if_telegram_unconfigured(settings)
    ctx["session_factory"] = get_sessionmaker()
    ctx["redis"] = get_redis()
    # Dedicated arq pool so jobs can enqueue follow-up jobs (e.g. the scanner
    # fanning out Telegram alerts after each hit). Closed in on_shutdown.
    ctx["arq_pool"] = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    ctx["backfill_rate_limit_ms"] = settings.BACKFILL_RATE_LIMIT_MS
    # Import ccxt lazily so merely importing this module (e.g. in tests that
    # only inspect WorkerSettings) never pulls in the network client.
    import ccxt.async_support as ccxt_async

    ctx["exchange"] = ccxt_async.binance({"enableRateLimit": True})


async def on_shutdown(ctx: dict[str, Any]) -> None:
    exchange = ctx.get("exchange")
    if exchange is not None:
        await exchange.close()
    pool = ctx.get("arq_pool")
    if pool is not None:
        await pool.aclose()


class WorkerSettings:
    """arq worker definition. Run with ``arq app.worker.WorkerSettings``."""

    redis_settings: RedisSettings = RedisSettings.from_dsn(get_settings().redis_url)
    functions: list[Any] = [
        backfill_gaps,
        run_backtest_job,
        on_candle_close_job,
        scan_on_candle_close_job,
        send_telegram_alert_job,
        poll_equity_universe,
        run_ml_inference_job,
        retention_job,
    ]
    cron_jobs: list[CronJob] = [
        cron(run_news_ingest, minute=set(range(0, 60, 15)), run_at_startup=False),
        cron(trigger_backfill_sweep, minute={7, 37}),
        cron(poll_equity_universe, minute=set(range(0, 60, 15))),
        cron(retention_job, hour=3, minute=0),
    ]
    on_startup = staticmethod(on_startup)
    on_shutdown = staticmethod(on_shutdown)
