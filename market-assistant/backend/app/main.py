from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.alert_subscriptions import router as alert_subscriptions_router
from app.api.analytics import router as analytics_router
from app.api.backtests import router as backtests_router
from app.api.candles import router as candles_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.instruments import router as instruments_router
from app.api.ml import router as ml_router
from app.api.news import router as news_router
from app.api.scanner import router as scanner_router
from app.api.strategies import router as strategies_router
from app.api.ws_candles import router as ws_candles_router
from app.api.ws_scanner import router as ws_scanner_router
from app.api.ws_signals import router as ws_signals_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.sentry import init_sentry


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # One shared arq pool for the whole process, created at startup instead of
    # per request (a new create_pool per request leaks connections under load).
    app.state.arq_pool = await create_pool(
        RedisSettings.from_dsn(get_settings().redis_url)
    )
    try:
        yield
    finally:
        await app.state.arq_pool.aclose()


def create_app() -> FastAPI:
    configure_logging()
    init_sentry()
    app = FastAPI(title="Market Analysis Assistant", lifespan=_lifespan)
    # Browser origins are locked to the configured allowlist; never "*".
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(candles_router)
    app.include_router(ws_candles_router)
    app.include_router(ws_signals_router)
    app.include_router(ws_scanner_router)
    app.include_router(scanner_router)
    app.include_router(alert_subscriptions_router)
    app.include_router(instruments_router)
    app.include_router(backtests_router)
    app.include_router(strategies_router)
    app.include_router(ml_router)
    app.include_router(chat_router)
    app.include_router(news_router)
    app.include_router(analytics_router)
    # Test-only replay route; mounted solely under ENV=test, never in prod.
    if get_settings().env == "test":
        from app.api.test_routes import router as test_router

        app.include_router(test_router)
    return app


app = create_app()
