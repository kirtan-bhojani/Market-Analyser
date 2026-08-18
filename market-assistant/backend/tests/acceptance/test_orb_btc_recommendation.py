"""Phase 6 acceptance: enable ORB on BTC/USDT 15m, replay a breakout day,
get a recommendation-ready signal + honest mini-backtest stats.

Proves Tasks 1-13 compose end to end through the SAME public surfaces the
frontend calls: POST /api/strategy-configs to enable the preset, the real
candle-close worker (bound to the test's shared DB connection but otherwise
unmonkeypatched -- it exercises the real `load_recent_candles`), GET
/api/signals for the recommendation-ready signal, and the honest
POST /api/strategies/{name}/backtest mini-backtest (NOT Phase 5's
/api/backtests) for cost-adjusted stats.
"""

import pytest

import app.strategies.worker as worker_mod
from app.models.candle import CandleRow
from app.models.instrument import Instrument
from app.strategies.worker import on_candle_close

pytestmark = pytest.mark.acceptance


async def test_enable_orb_on_btc_15m_replay_breakout_day_produces_card_ready_signal(
    client,
    db_session,
    session_factory,
    redis_client,
    monkeypatch,
    fixture_orb_breakout_candles,
):
    # 1. Seed the real instrument the frontend targets.
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()

    # 2. Persist the engineered breakout-day candles under the real
    # instrument id so both the worker's `load_recent_candles` and the
    # mini-backtest endpoint read them from the DB (the fixture rows carry
    # instrument_id=0, which isn't seeded -- rebuild with the real id).
    db_session.add_all(
        [
            CandleRow(
                instrument_id=instrument.id,
                tf=row.tf,
                ts=row.ts,
                o=row.o,
                h=row.h,
                l=row.l,
                c=row.c,
                v=row.v,
            )
            for row in fixture_orb_breakout_candles
        ]
    )
    await db_session.commit()

    # 3. Enable ORB via the same API the frontend calls.
    resp = await client.post(
        "/api/strategy-configs",
        json={
            "strategy": "orb",
            "instrument_id": instrument.id,
            "tf": "15m",
            "params": {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            "enabled": True,
        },
    )
    assert resp.status_code == 201

    # 4. Bind the worker to the shared connection so it reads the seeded
    # config/candles; do NOT monkeypatch load_recent_candles -- this proves
    # the real DB read path composes with the preset + regime gate.
    monkeypatch.setattr(worker_mod, "get_sessionmaker", lambda: session_factory)

    # 5. Replay the breakout day through the production candle-close path.
    # Dedup makes repeats no-ops, so one call is enough.
    await on_candle_close(instrument_id=instrument.id, tf="15m")

    # 6. A recommendation-ready signal exists with correct reference levels.
    signals_resp = await client.get(
        f"/api/signals?instrument_id={instrument.id}&strategy=orb"
    )
    assert signals_resp.status_code == 200
    signals = signals_resp.json()
    assert len(signals) == 1
    sig = signals[0]
    assert sig["direction"] == "long"
    assert sig["ref_sl"] < sig["ref_entry"] < sig["ref_tp"]

    # 7. The honest mini-backtest (Phase 6's own endpoint, not Phase 5's
    # /api/backtests) returns real, finite, honest stats. Zero resolved
    # trades within the 60-bar fixture is a valid honest answer, so we do
    # NOT assert trade_count > 0 -- only that the shape is honest.
    bt_resp = await client.post(
        "/api/strategies/orb/backtest",
        json={
            "instrument_id": instrument.id,
            "tf": "15m",
            "params": {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            "fees_bps": 10,
            "slippage_bps": 5,
        },
    )
    assert bt_resp.status_code == 200
    body = bt_resp.json()
    assert body["n_candles"] == 60
    stats = body["stats"]
    assert "trade_count" in stats
    assert isinstance(stats["trade_count"], int | float)
    assert stats["win_rate"] is not None
    assert 0.0 <= stats["win_rate"] <= 1.0
