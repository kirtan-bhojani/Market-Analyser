from app.chat.tools import signal_tools


async def test_get_recent_signals_for_symbol(db_session, seeded_signal):
    result = await signal_tools.get_recent_signals({"symbol": "SOL/USDT"}, {"db": db_session})
    assert len(result["signals"]) == 1
    assert result["signals"][0]["strategy"] == "orb"
    assert result["signals"][0]["direction"] == "long"


async def test_get_recent_signals_unknown_symbol(db_session):
    result = await signal_tools.get_recent_signals({"symbol": "NOPE"}, {"db": db_session})
    assert result == {"symbol": "NOPE", "available": False}


async def test_get_scan_hits_empty(db_session):
    result = await signal_tools.get_scan_hits({}, {"db": db_session})
    assert result == {"hits": []}


async def test_run_quick_backtest_unknown_strategy(db_session):
    result = await signal_tools.run_quick_backtest(
        {"strategy": "does_not_exist", "symbol": "BTC/USDT"}, {"db": db_session}
    )
    assert result["available"] is False


async def test_run_quick_backtest_uses_cache(db_session, monkeypatch):
    async def fake_cache_get(key):
        return {"strategy": "ema_vwap_trend", "symbol": "BTC/USDT", "stats": {"sharpe": 1.2}}

    monkeypatch.setattr(signal_tools, "_cache_get", fake_cache_get)
    result = await signal_tools.run_quick_backtest(
        {"strategy": "ema_vwap_trend", "symbol": "BTC/USDT"}, {"db": db_session}
    )
    assert result["stats"]["sharpe"] == 1.2
