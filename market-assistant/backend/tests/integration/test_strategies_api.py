import math
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.candle import CandleRow
from app.models.strategy_config import StrategyConfig

pytestmark = pytest.mark.asyncio


async def test_list_strategies_returns_all_eight_presets(client):
    resp = await client.get("/api/strategies")
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert {
        "orb",
        "vwap_revert",
        "ema_vwap_trend",
        "breakout_retest",
        "pullback_trend",
        "bb_rsi_revert",
        "grid_range",
        "funding_extreme",
    } <= names


async def test_enable_strategy_config_round_trip(client, seeded_instrument):
    resp = await client.post(
        "/api/strategy-configs",
        json={
            "strategy": "orb",
            "instrument_id": seeded_instrument.id,
            "tf": "15m",
            "params": {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            "enabled": True,
        },
    )
    assert resp.status_code == 201
    cfg_id = resp.json()["id"]

    resp2 = await client.get("/api/strategy-configs")
    assert resp2.status_code == 200
    assert any(c["id"] == cfg_id and c["enabled"] for c in resp2.json())


async def test_toggle_off_upserts_not_duplicates(client, db_session, seeded_instrument):
    # Enabling then disabling the same (strategy, instrument, tf) must leave a
    # SINGLE config row flipped to enabled=False -- not a second enabled=False
    # row alongside a still-enabled one that the worker would keep evaluating.
    payload = {
        "strategy": "orb",
        "instrument_id": seeded_instrument.id,
        "tf": "15m",
        "params": {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
        "enabled": True,
    }
    on = await client.post("/api/strategy-configs", json=payload)
    assert on.status_code == 201
    off = await client.post("/api/strategy-configs", json={**payload, "enabled": False})
    assert off.status_code in (200, 201)

    configs = (await client.get("/api/strategy-configs")).json()
    orb_configs = [c for c in configs if c["strategy"] == "orb"]
    assert len(orb_configs) == 1
    assert orb_configs[0]["enabled"] is False


async def test_create_strategy_config_unknown_strategy_is_422(client, seeded_instrument):
    resp = await client.post(
        "/api/strategy-configs",
        json={
            "strategy": "does_not_exist",
            "instrument_id": seeded_instrument.id,
            "tf": "15m",
            "params": {},
        },
    )
    assert resp.status_code == 422


async def test_get_signals_filters_by_instrument(client, seeded_signal):
    resp = await client.get(f"/api/signals?instrument_id={seeded_signal.instrument_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert all(s["instrument_id"] == seeded_signal.instrument_id for s in body)


async def test_patch_other_users_config_is_404(client, db_session, seeded_instrument):
    # A config owned by a different user must not be PATCH-able by the default
    # dev user the client authenticates as (DEV_USER_ID).
    other_cfg = StrategyConfig(
        user_id=uuid.uuid4(),
        strategy="orb",
        instrument_id=seeded_instrument.id,
        tf="15m",
        params={"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
        enabled=True,
    )
    db_session.add(other_cfg)
    await db_session.commit()

    resp = await client.patch(
        f"/api/strategy-configs/{other_cfg.id}",
        json={
            "strategy": "orb",
            "instrument_id": seeded_instrument.id,
            "tf": "15m",
            "params": {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            "enabled": False,
        },
    )
    assert resp.status_code == 404


async def test_mini_backtest_returns_honest_stats(client, db_session, seeded_instrument):
    # Seed a deterministic rising series with periodic volume spikes so the ORB
    # preset has enough history to run; committed via db_session so the endpoint's
    # session (shared connection) can read the rows.
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(150):
        c = 100.0 + i * 2.0
        v = 3_000.0 if i % 10 == 4 else 1_000.0
        db_session.add(
            CandleRow(
                instrument_id=seeded_instrument.id,
                tf="15m",
                ts=start + timedelta(minutes=15 * i),
                o=c - 1.5,
                h=c + 1.0,
                l=c - 1.0,
                c=c,
                v=v,
            )
        )
    await db_session.commit()

    resp = await client.post(
        "/api/strategies/orb/backtest",
        json={"instrument_id": seeded_instrument.id, "tf": "15m"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_candles"] == 150
    stats = body["stats"]
    for key in ("sharpe", "max_dd", "win_rate", "net_return", "trade_count"):
        assert key in stats
        assert math.isfinite(stats[key])
    assert stats["trade_count"] >= 0


async def test_mini_backtest_no_candles_is_404(client, seeded_instrument):
    resp = await client.post(
        "/api/strategies/orb/backtest",
        json={"instrument_id": seeded_instrument.id, "tf": "1h"},
    )
    assert resp.status_code == 404


async def test_mini_backtest_unknown_strategy_is_422(client, seeded_instrument):
    resp = await client.post(
        "/api/strategies/nope/backtest",
        json={"instrument_id": seeded_instrument.id, "tf": "15m"},
    )
    assert resp.status_code == 422
