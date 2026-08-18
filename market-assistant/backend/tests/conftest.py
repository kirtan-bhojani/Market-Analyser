# ruff: noqa: E402 -- DATABASE_URL must be set before app.core.config is imported
import os

# Native-lib thread hygiene: the ML modules pull in lightgbm/sklearn, which link
# their own OpenMP runtime. Under the full single-process run, the OpenMP thread
# pool (and lightgbm's tqdm monitor thread) is created/torn down across many
# per-test event loops and segfaults mid-suite. Pin every native thread pool to
# 1 and tolerate a duplicated libomp — this MUST happen before numpy/sklearn/
# lightgbm are first imported (i.e. before app.* below), so set it here at the
# very top of the first conftest pytest loads. setdefault respects an explicit
# override from the caller's environment.
for _var, _val in (
    ("OMP_NUM_THREADS", "1"),
    ("OPENBLAS_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
    ("KMP_DUPLICATE_LIB_OK", "TRUE"),
):
    os.environ.setdefault(_var, _val)

# pandas-ta (scanner/backtest tests) creates tqdm progress bars, which spin up a
# persistent daemon "monitor" thread. That leaves the parent process
# multi-threaded, so when pytest-forked forks an ML test the child inherits a
# mid-flight OpenMP/thread state and segfaults. Disabling the monitor interval
# stops the thread from ever starting, keeping the parent single-threaded and
# every fork clean. No effect on non-forked (Linux CI) runs beyond dropping a
# progress-bar heartbeat thread nothing depends on.
import tqdm as _tqdm

_tqdm.tqdm.monitor_interval = 0

# Preload lightgbm's OpenMP runtime (libomp) BEFORE anything pulls in OpenBLAS's
# (numpy/pandas/pandas-ta, loaded by the scanner/backtest/analytics tests). On
# macOS the two OpenMP runtimes otherwise co-initialize in an order that
# segfaults mid-suite; loading lightgbm first — combined with
# KMP_DUPLICATE_LIB_OK above — pins a single, stable libomp for the whole
# process. Best-effort: if lightgbm isn't installed the ML tests are skipped
# anyway, so a failed import here is harmless.
try:
    import lightgbm as _lightgbm  # noqa: F401
except Exception:
    pass

# Test hermeticity: neutralize a developer-local .env (e.g. a Supabase
# DATABASE_URL lacking the +asyncpg driver, which breaks the async engine).
# In pydantic-settings, an OS env var outranks the .env file; setdefault beats
# the .env yet still respects an explicit `DATABASE_URL` export, so `pytest`
# stays hermetic against local Postgres (CI has no .env and gets this default).
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://market:market@localhost:5434/market_assistant"
)

# The config default is now ENV=prod (fail-closed auth). The whole suite relies
# on the non-prod dev auth stub (X-Dev-User / raw-UUID WS tokens), so pin
# ENV=test here — BEFORE the first get_settings() (lru_cache) call at import
# time. setdefault respects an explicit ENV export but gives CI/local a test env.
os.environ.setdefault("ENV", "test")

# Full hermeticity: ignore the developer-local .env FILE entirely during tests
# so local runs match CI (which has no .env). The setdefault guards above only
# help vars the .env sets; a test that delenv's a secret (e.g. test_startup_
# failure) would still see the .env FILE re-supply it. Disabling the env_file
# source at the class level closes that gap for every Settings construction.
import app.core.config as _config  # noqa: E402

_config.Settings.model_config["env_file"] = None
_config.get_settings.cache_clear()

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
import redis as redis_sync
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.core.config import get_settings
from app.core.deps import get_engine, get_redis, get_session
from app.main import create_app
from app.models.candle import CandleRow
from app.models.instrument import Instrument
from app.scanner.worker import on_candle_close


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_schema():
    # A freshly-started Postgres (local dev or CI) has an empty `public`
    # schema. Acceptance and ingest integration tests INSERT into tables
    # (instruments/candles/news_items/...) that only exist after migrations,
    # and pytest may collect them before tests/integration/test_migrations.py
    # creates the schema, so run `alembic upgrade head` ONCE at session start.
    # This is synchronous (command.upgrade manages its own event loop, see
    # alembic/env.py), so it does not conflict with the function-scoped
    # event loops pytest-asyncio hands each test. test_migrations.py may later
    # drop and re-create the schema mid-session; nothing table-dependent is
    # collected after it, so that is safe.
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
async def _reset_cached_engine():
    # get_engine()/get_redis() are lru_cache'd, but pytest-asyncio gives each
    # test its own event loop by default. asyncpg/redis connections can't
    # cross event loops, so the cached clients must be disposed and evicted
    # after every test.
    yield
    engine = get_engine()
    await engine.dispose()
    get_engine.cache_clear()

    redis_client = get_redis()
    await redis_client.aclose()
    get_redis.cache_clear()


@pytest.fixture
async def db_connection():
    # Test isolation via the "join an external transaction" pattern: open an
    # outer connection-level transaction shared by every session in a test.
    # Sessions bound to this connection with join_transaction_mode=
    # "create_savepoint" act on a SAVEPOINT for their own commit()/rollback(),
    # so the outer transaction stays open and all sessions see each other's
    # (savepoint-committed) writes. Tearing down rolls the outer transaction
    # back, so nothing a test committed persists. Setup happens after the
    # autouse _reset_cached_engine fixture, so this connection is closed before
    # that disposes the engine.
    engine = get_engine()
    connection = await engine.connect()
    transaction = await connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest.fixture
async def db_session(db_connection):
    session = AsyncSession(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def session_factory(db_connection):
    # Zero-arg callable yielding a NEW AsyncSession bound to the SAME shared
    # connection/outer transaction as db_session. Used as `async with
    # session_factory() as s`; a session's commit() releases a savepoint (the
    # outer transaction survives) so its writes are visible to db_session and
    # to later factory sessions. The outer rollback in db_connection cleans up.
    def _make() -> AsyncSession:
        return AsyncSession(
            bind=db_connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

    return _make


@pytest.fixture
def test_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_headers(test_user_id: uuid.UUID) -> dict[str, str]:
    return {"X-Dev-User": str(test_user_id)}


@pytest.fixture
def other_user_headers(other_user_id: uuid.UUID) -> dict[str, str]:
    return {"X-Dev-User": str(other_user_id)}


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def test_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def client(app, db_connection, session_factory):
    # Like test_client, but the get_session dependency is bound to the SAME
    # shared connection/outer transaction as db_session, so the API reads
    # rows a test seeded (and savepoint-committed) via db_session.
    async def _override_get_session():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def redis_sync_client():
    # Plain synchronous Redis client against the same instance the app uses,
    # for test-side publishing into the pub/sub fan-out. Skips the test when
    # no Redis is reachable (e.g. a bare unit-only environment).
    client = redis_sync.Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        client.ping()
    except Exception:
        pytest.skip("Redis not available")
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
async def redis_client():
    # Async Redis client (decode_responses=True) against the app's instance,
    # for the scanner worker's pub/sub fan-out and dedup keys. Skips when Redis
    # is unreachable. Do NOT aclose/cache_clear here: the autouse
    # _reset_cached_engine fixture already disposes get_redis after the test;
    # a double-close would error.
    client = get_redis()
    try:
        await client.ping()
    except Exception:
        pytest.skip("Redis not available")

    # The suite shares this Redis instance across runs, but Postgres FK id
    # sequences reset whenever the schema is recreated (see
    # test_migrations.py), so a fresh rule_id/instrument_id combined with a
    # fixed test candle ts can collide with a leftover
    # scan_hit_dedup:{rule_id}:{instrument_id}:{tf}:{bar_ts} key from a
    # previous run and wrongly suppress a hit. Clear only the scanner dedup
    # keyspace (never flushdb - other tests/data may share this instance) so
    # every run starts hermetic.
    keys = [k async for k in client.scan_iter(match="scan_hit_dedup:*")]
    if keys:
        await client.delete(*keys)

    # Same hazard for the signal worker's dedup keyspace: a stale
    # signal_dedup:{strategy}:{instrument_id}:{tf}:{bar_ts}:{direction} key from a
    # previous run (fresh instrument_id + fixed fixture bar ts) would wrongly
    # suppress the signal under test. Clear only this keyspace (never flushdb).
    signal_keys = [k async for k in client.scan_iter(match="signal_dedup:*")]
    if signal_keys:
        await client.delete(*signal_keys)

    yield client


@pytest.fixture
async def sample_instrument(db_session):
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()
    return instrument


@pytest.fixture
async def seeded_instrument(db_session):
    # Committed (savepoint released) so the API's own session — bound to the
    # same shared connection via the `client` override — can read it.
    instrument = Instrument(
        symbol="ETH/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.commit()
    return instrument


@pytest.fixture
async def seeded_signal(db_session):
    from app.models.signal import Signal

    instrument = Instrument(
        symbol="SOL/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()
    signal = Signal(
        instrument_id=instrument.id,
        strategy="orb",
        direction="long",
        ts=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        confidence=0.7,
        ref_entry=100.0,
        ref_sl=99.0,
        ref_tp=102.0,
        meta={"note": "seed"},
    )
    db_session.add(signal)
    await db_session.commit()
    return signal


@pytest.fixture
async def seed_btc_1m_candles(db_session):
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(60):
        db_session.add(
            CandleRow(
                instrument_id=instrument.id,
                tf="1m",
                ts=start + timedelta(minutes=i),
                o=100 + i,
                h=101 + i,
                l=99 + i,
                c=100.5 + i,
                v=10 + i,
            )
        )
    await db_session.commit()
    return instrument


def _rsi_dip_with_volume_spike_series() -> tuple[list[float], list[float]]:
    # Matches Task 5's golden series: 40 flat bars, then a 15-bar monotonic
    # RSI-triggering drop; a single relative-volume spike at bar index 50.
    # By bar 50 the close series has fallen monotonically (RSI -> ~0, < 30) and
    # rel_volume(20) = 200 / 20-baseline = 10 (> 2), so the AND rule fires there.
    closes = [100.0] * 40 + list(np.linspace(100, 70, 15))
    volumes = [20.0] * 55
    volumes[50] = 200.0
    return closes, volumes


@pytest.fixture
async def replay_synthetic_candles(db_session, redis_client):
    """Replay a synthetic candle series through the production candle-close path.

    CRITICAL: ``on_candle_close`` builds a FRESH ``IndicatorCache`` on every call
    and warm-starts it by loading candle history FROM THE DB (via ``ctx["db"]``),
    then appends only the one passed candle. So a bar only has enough history to
    make rsi/rel_volume non-NaN if the PRIOR bars are already persisted. We
    therefore PROCESS bar i against persisted history 0..i-1, THEN persist bar i
    on the SAME session (SAVEPOINT-isolated, so a separate connection wouldn't
    see the flushed rows) so the NEXT bar's warm-start can read it.
    """

    async def _replay(instrument_id: int, tf: str, scenario: str) -> None:
        if scenario != "rsi_dip_with_volume_spike":
            raise ValueError(f"unknown scenario {scenario!r}")
        closes, volumes = _rsi_dip_with_volume_spike_series()
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True)):
            ts = f"2026-01-01T00:{i:02d}:00Z"
            candle = {
                "ts": ts,
                "o": c - 0.1,
                "h": c + 0.5,
                "l": c - 0.5,
                "c": c,
                "v": v,
            }
            # 1) process bar i against history 0..i-1 (a hit may fire here)
            await on_candle_close(
                {"db": db_session, "redis": redis_client},
                instrument_id=instrument_id,
                tf=tf,
                candle=candle,
            )
            # 2) persist bar i so the next bar's warm-start sees it
            db_session.add(
                CandleRow(
                    instrument_id=instrument_id,
                    tf=tf,
                    ts=datetime.fromisoformat(ts.replace("Z", "+00:00")),
                    o=c - 0.1,
                    h=c + 0.5,
                    l=c - 0.5,
                    c=c,
                    v=v,
                )
            )
            await db_session.flush()

    return _replay


_IST = ZoneInfo("Asia/Kolkata")
# 2025-06-09 (Mon) 10:00 IST — mid-session on an NSE trading day.
_IN_SESSION_NOW = datetime(2025, 6, 9, 10, 0, tzinfo=_IST)


@pytest.fixture
def in_session_time():
    """Freeze ``app.ingest.equity_poller.datetime.now`` to an in-session NSE
    timestamp so ``poll_equity_universe`` treats the market as open. Only the
    ``datetime`` symbol in that module is patched; ``timedelta`` (imported
    separately there) keeps working, matching the equity_poller integration
    tests' approach."""
    with patch("app.ingest.equity_poller.datetime") as mock_dt:
        mock_dt.now.return_value = _IN_SESSION_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        yield mock_dt


@pytest.fixture
async def seeded_reliance_15m_breakout_day(db_session):
    """Seed a RELIANCE.NS equity instrument plus the Task 9
    ``reliance_15m_breakout_day`` fixture bars (26 15m candles of one NSE
    session) so the synchronous mini-backtest endpoint can run ORB on equity
    candles. Committed (savepoint released) so the API's own session — bound to
    the same shared connection via the ``client`` override — reads the rows.
    Returns the seeded ``Instrument``."""
    from tests.fixtures.candles import load_fixture_candles

    instrument = Instrument(
        symbol="RELIANCE.NS", asset_class="equity", exchange="NSE", active=True
    )
    db_session.add(instrument)
    await db_session.flush()

    df = load_fixture_candles("reliance_15m_breakout_day")
    db_session.add_all(
        [
            CandleRow(
                instrument_id=instrument.id,
                tf="15m",
                ts=ts.to_pydatetime(),
                o=float(row.o),
                h=float(row.h),
                l=float(row.l),
                c=float(row.c),
                v=float(row.v),
            )
            for ts, row in df.iterrows()
        ]
    )
    await db_session.commit()
    return instrument


@pytest.fixture
def fixture_trending_candles() -> pd.DataFrame:
    """Synthetic 60-bar monotonically-rising OHLCV series (deterministic,
    arithmetic-only) engineered so the repo's real `adx()` yields a strongly
    trending last value (verified empirically: last ADX == 100.0, well above
    any `min_adx_trend` threshold used in tests).

    A clean, noise-free linear uptrend maximizes +DI relative to -DI (down
    moves never occur), so ADX saturates at 100 — deliberately steep/clean
    rather than a realistic price series, to make the gate's trend/range
    branches unambiguous in tests.
    """
    n = 60
    closes = [100.0 + i * 2.0 for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    opens = [c - 1.5 for c in closes]
    volumes = [1_000.0] * n
    return pd.DataFrame({"o": opens, "h": highs, "l": lows, "c": closes, "v": volumes})


@pytest.fixture
def fixture_orb_breakout_candles() -> list[CandleRow]:
    """60-bar CandleRow series (unpersisted) engineered so the signal worker's
    DataFrame satisfies BOTH real-code preconditions (verified empirically):

      * ``adx_allows(df, mode="trend") is True`` — the clean monotonic uptrend
        (adapted from ``fixture_trending_candles``) yields a last ADX of 100.0.
      * ``get_strategy("orb").generate_signals(df, {"or_bars": 4, "rr": 2.0,
        "min_rel_volume": 2.0})`` returns EXACTLY 1 long candidate — a 3x volume
        spike at bar index 4 (rel_volume(4) == 3.0 >= 2.0) breaks above the
        opening-range high (107) formed by bars 0..3. Fires: entry=108, sl=99
        (OR low), tp=126.

    Returned as ORM ``CandleRow`` objects because the worker's
    ``load_recent_candles`` is monkeypatched to yield this list directly; the
    worker converts OHLCV to float and reads ``.ts`` for the Signal timestamp.
    """
    n = 60
    start = datetime(2024, 1, 1, tzinfo=UTC)
    rows: list[CandleRow] = []
    for i in range(n):
        c = 100.0 + i * 2.0
        v = 3_000.0 if i == 4 else 1_000.0
        rows.append(
            CandleRow(
                instrument_id=0,
                tf="15m",
                ts=start + timedelta(minutes=15 * i),
                o=c - 1.5,
                h=c + 1.0,
                l=c - 1.0,
                c=c,
                v=v,
            )
        )
    return rows
