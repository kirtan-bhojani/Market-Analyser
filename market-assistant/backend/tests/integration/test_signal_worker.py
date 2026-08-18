import asyncio

import pytest

import app.strategies.worker as worker_mod
from app.models.instrument import Instrument
from app.models.signal import Signal
from app.models.strategy_config import StrategyConfig
from app.strategies.worker import on_candle_close


async def _poll_one_message(pubsub, total_timeout: float = 1.0):
    """Poll a pubsub for a single message within `total_timeout` seconds."""
    messages = []
    waited = 0.0
    step = 0.05
    while waited < total_timeout:
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=step)
        if msg is not None:
            messages.append(msg)
            # keep polling briefly to catch any (unexpected) extra publishes
            continue
        if messages:
            break
        await asyncio.sleep(step)
        waited += step
    return messages


@pytest.fixture(autouse=True)
def _bind_worker_to_shared_connection(monkeypatch, session_factory, fixture_orb_breakout_candles):
    # The worker opens its OWN session; bind it to the test's shared connection
    # so worker + test see each other's rows, and sidestep candle persistence by
    # returning the engineered fixture directly.
    monkeypatch.setattr(worker_mod, "get_sessionmaker", lambda: session_factory)

    async def _fake_load_recent_candles(session, instrument_id, tf, limit):
        return fixture_orb_breakout_candles

    monkeypatch.setattr(worker_mod, "load_recent_candles", _fake_load_recent_candles)


@pytest.mark.asyncio
async def test_enabled_config_produces_signal_row_and_ws_publish(
    db_session, redis_client, fixture_orb_breakout_candles
):
    instrument = Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance")
    db_session.add(instrument)
    await db_session.flush()
    db_session.add(
        StrategyConfig(
            user_id="00000000-0000-0000-0000-000000000001",
            strategy="orb",
            instrument_id=instrument.id,
            tf="15m",
            params={"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            enabled=True,
        )
    )
    await db_session.commit()

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("signals:BTC/USDT:15m")
    try:
        await on_candle_close(instrument_id=instrument.id, tf="15m")

        rows = (
            await db_session.execute(
                Signal.__table__.select().where(Signal.instrument_id == instrument.id)
            )
        ).fetchall()
        assert len(rows) == 1
        assert rows[0].strategy == "orb"
        assert rows[0].direction == "long"

        messages = await _poll_one_message(pubsub)
        assert len(messages) == 1
    finally:
        await pubsub.unsubscribe("signals:BTC/USDT:15m")
        await pubsub.aclose()


@pytest.mark.asyncio
async def test_repeated_candle_close_is_idempotent(
    db_session, redis_client, fixture_orb_breakout_candles
):
    instrument = Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance")
    db_session.add(instrument)
    await db_session.flush()
    db_session.add(
        StrategyConfig(
            user_id="00000000-0000-0000-0000-000000000001",
            strategy="orb",
            instrument_id=instrument.id,
            tf="15m",
            params={"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            enabled=True,
        )
    )
    await db_session.commit()

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("signals:BTC/USDT:15m")
    try:
        # Two closes over the same rolling window: the dedup guard must make the
        # second call a full no-op (0 new rows, 0 new publishes).
        await on_candle_close(instrument_id=instrument.id, tf="15m")
        await on_candle_close(instrument_id=instrument.id, tf="15m")

        rows = (
            await db_session.execute(
                Signal.__table__.select().where(Signal.instrument_id == instrument.id)
            )
        ).fetchall()
        assert len(rows) == 1

        messages = await _poll_one_message(pubsub)
        assert len(messages) == 1
    finally:
        await pubsub.unsubscribe("signals:BTC/USDT:15m")
        await pubsub.aclose()


@pytest.mark.asyncio
async def test_disabled_config_produces_nothing(
    db_session, redis_client, fixture_orb_breakout_candles
):
    instrument = Instrument(symbol="ETH/USDT", asset_class="crypto", exchange="binance")
    db_session.add(instrument)
    await db_session.flush()
    db_session.add(
        StrategyConfig(
            user_id="00000000-0000-0000-0000-000000000001",
            strategy="orb",
            instrument_id=instrument.id,
            tf="15m",
            params={"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            enabled=False,
        )
    )
    await db_session.commit()

    await on_candle_close(instrument_id=instrument.id, tf="15m")

    rows = (
        await db_session.execute(
            Signal.__table__.select().where(Signal.instrument_id == instrument.id)
        )
    ).fetchall()
    assert rows == []
