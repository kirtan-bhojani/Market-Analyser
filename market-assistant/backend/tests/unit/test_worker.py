from arq.connections import RedisSettings

from app.core.config import get_settings
from app.ingest.backfill import backfill_gaps
from app.worker import WorkerSettings
from app.workers.news_worker import run_news_ingest


def test_backfill_gaps_registered_as_function():
    assert backfill_gaps in WorkerSettings.functions


def test_news_ingest_scheduled_as_cron_every_15_min():
    news_jobs = [c for c in WorkerSettings.cron_jobs if c.coroutine is run_news_ingest]
    assert len(news_jobs) == 1
    assert news_jobs[0].minute == {0, 15, 30, 45}


def test_backfill_sweep_scheduled_as_cron():
    from app.worker import trigger_backfill_sweep

    coroutines = [c.coroutine for c in WorkerSettings.cron_jobs]
    assert trigger_backfill_sweep in coroutines


def test_redis_settings_derived_from_config():
    assert WorkerSettings.redis_settings == RedisSettings.from_dsn(
        get_settings().redis_url
    )


def test_lifecycle_hooks_present():
    assert callable(WorkerSettings.on_startup)
    assert callable(WorkerSettings.on_shutdown)
