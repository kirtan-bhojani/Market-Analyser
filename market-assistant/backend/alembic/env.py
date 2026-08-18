import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_settings
from app.models import Base

config = context.config
# DO NOT run `alembic revision --autogenerate`. Base.metadata maps only a
# subset of the schema, and every migration is hand-written raw SQL.
# Autogenerate would diff the live DB against this partial metadata and emit
# spurious DROP/CREATE for the unmapped tables. Write migrations by hand.
target_metadata = Base.metadata


def _engine_kwargs_for_schema(db_schema: str) -> dict[str, Any]:
    # Mirrors app.core.deps.get_engine: "public" => no connect_args, byte-for-
    # byte unchanged behavior; any other schema sets the asyncpg search_path.
    kwargs: dict[str, Any] = {}
    if db_schema and db_schema != "public":
        kwargs["connect_args"] = {
            "server_settings": {"search_path": f"{db_schema},public"}
        }
    return kwargs


def run_migrations_offline() -> None:
    db_schema = get_settings().db_schema
    non_public_schema = db_schema if db_schema and db_schema != "public" else None
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema=non_public_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    db_schema = get_settings().db_schema
    non_public_schema = db_schema if db_schema and db_schema != "public" else None
    if non_public_schema:
        # Commit the schema DDL + search_path OUTSIDE alembic's migration
        # transaction. If these merely ran in the default (autobegin)
        # transaction, the outer transaction opened by
        # `run_migrations_online()`'s `engine.connect()` block is never
        # committed and SQLAlchemy rolls it back on block exit -> the
        # schema/tables/alembic_version silently vanish while
        # command.upgrade() still reports success. An explicit commit() makes
        # the CREATE SCHEMA durable and independent of the migration
        # transaction; SET search_path is a session-level setting that then
        # persists on this connection for the migrations below.
        # (Note: `with connection.execution_options(...)` cannot be used here —
        # Connection.execution_options() returns the same Connection, whose
        # context-manager __exit__ CLOSES the connection.)
        connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{non_public_schema}"')
        connection.exec_driver_sql(f'SET search_path TO "{non_public_schema}", public')
        connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=non_public_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    db_schema = get_settings().db_schema
    engine = create_async_engine(
        get_settings().database_url, **_engine_kwargs_for_schema(db_schema)
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def _run_migrations_online_sync() -> None:
    # command.upgrade() may be invoked from a test running inside an already
    # active asyncio event loop (e.g. pytest-asyncio). asyncio.run() cannot be
    # called from within a running loop, so run it on a dedicated thread with
    # its own loop when that's the case.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(run_migrations_online())
    else:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, run_migrations_online()).result()


if context.is_offline_mode():
    run_migrations_offline()
else:
    _run_migrations_online_sync()
