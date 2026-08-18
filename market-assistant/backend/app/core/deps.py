from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, cast

import redis.asyncio as redis
from arq.connections import ArqRedis
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if settings.db_schema and settings.db_schema != "public":
        kwargs["connect_args"] = {
            "server_settings": {"search_path": f"{settings.db_schema},public"}
        }
    return create_async_engine(settings.database_url, **kwargs)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # NOT lru_cache'd: the autouse test fixture disposes get_engine() and clears
    # its cache after every test, so a cached sessionmaker would stay bound to a
    # disposed engine / dead event loop (asyncpg cross-event-loop failure).
    # Construction is trivial, so rebuild on the current engine each call.
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession.

    Tests override this to bind sessions to their shared transaction; see
    the candles integration tests.
    """
    async with get_sessionmaker()() as session:
        yield session


@lru_cache
def get_redis() -> redis.Redis:
    # redis<6 (pinned transitively by arq) ships an untyped from_url; cast the
    # result back to the annotated return type to keep mypy --strict green.
    client = redis.from_url(  # type: ignore[no-untyped-call]
        get_settings().redis_url, decode_responses=True
    )
    return cast(redis.Redis, client)


async def get_arq_pool(request: Request) -> ArqRedis:
    """FastAPI dependency returning the shared arq pool created at app startup
    (see the lifespan in app.main), rather than a new pool per request.

    Integration tests override this with a fake pool so they do not depend on
    a live arq worker / redis.
    """
    return cast(ArqRedis, request.app.state.arq_pool)
