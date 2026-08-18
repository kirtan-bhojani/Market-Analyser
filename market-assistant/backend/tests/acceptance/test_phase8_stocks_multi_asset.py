"""Phase 8 acceptance: multi-asset (equity) support composes end to end.

Proves Tasks 1-10 wire together through the SAME public surfaces the frontend
calls:

* Test A — the session-aware NIFTY-50 equity poller (Task 4) writes 1m candles,
  and both ``GET /candles`` (Task 5 delay envelope) and
  ``GET /api/instruments`` (Task 6) surface RELIANCE.NS as a 15-min-delayed
  equity feed.
* Test B — the honest synchronous mini-backtest endpoint (Phase 6) runs the ORB
  preset (Phase 5/6, asset-class-agnostic) on equity candles and returns finite,
  JSON-safe stats. We use the mini-backtest endpoint, NOT Phase 5's async
  ``POST /backtests`` (which only enqueues an arq job and cannot produce stats
  inline in tests).
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.ingest.candle import Candle
from app.ingest.equity_poller import poll_equity_universe

pytestmark = pytest.mark.acceptance


def _fake_fetch_candles(symbol, tf, start, end, client=None):
    # One synthetic 1m candle per polled equity symbol, timestamped at the
    # frozen in-session `now` so it lands inside the test's /candles window.
    return [
        Candle(
            symbol=f"{symbol}.NS" if "." not in symbol else symbol,
            tf=tf,
            ts=end,
            o=Decimal("2900"),
            h=Decimal("2910"),
            l=Decimal("2895"),
            c=Decimal("2905"),
            v=Decimal("120000"),
        )
    ]


@pytest.mark.asyncio
async def test_nifty50_watchlist_live_with_delay_badge(
    db_session, redis_client, client, in_session_time
):
    # The poll writes through the SAME shared connection the `client` fixture
    # binds get_session to (session_factory -> db_session), so the API reads
    # the savepoint-committed candles/instruments.
    ctx = {"session_factory": lambda: db_session, "redis": redis_client}

    with patch(
        "app.ingest.equity_poller.fetch_candles", side_effect=_fake_fetch_candles
    ):
        written = await poll_equity_universe(ctx)
    assert written > 0

    resp = await client.get(
        "/candles",
        params={
            "symbol": "RELIANCE.NS",
            "tf": "1m",
            "from": "2025-06-09T00:00:00Z",
            "to": "2025-06-09T23:59:59Z",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["candles"]) > 0
    assert body["delayed"] is True
    assert body["delay_minutes"] == 15

    instruments_resp = await client.get(
        "/api/instruments", params={"asset_class": "equity"}
    )
    symbols = {i["symbol"] for i in instruments_resp.json()}
    assert "RELIANCE.NS" in symbols


@pytest.mark.asyncio
async def test_orb_backtest_runs_on_equity_candles(
    client, db_session, seeded_reliance_15m_breakout_day
):
    # Route A (API-level): drive the Phase-6 honest mini-backtest endpoint on
    # equity candles, mirroring test_orb_btc_recommendation.py.
    instrument = seeded_reliance_15m_breakout_day
    resp = await client.post(
        "/api/strategies/orb/backtest",
        json={
            "instrument_id": instrument.id,
            "tf": "15m",
            "params": {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0},
            "fees_bps": 10,
            "slippage_bps": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_candles"] == 26  # the reliance_15m_breakout_day session

    stats = body["stats"]
    assert "trade_count" in stats
    assert isinstance(stats["trade_count"], int | float)
    assert stats["win_rate"] is not None
    assert 0.0 <= stats["win_rate"] <= 1.0
    # net_return is finite / not NaN (== is False for NaN).
    assert stats["net_return"] == stats["net_return"]
