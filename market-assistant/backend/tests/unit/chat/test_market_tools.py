from app.chat.tools import market_tools


async def test_get_price_returns_last_close(db_session, seed_btc_1m_candles):
    ctx = {"db": db_session}
    result = await market_tools.get_price({"symbol": "BTC/USDT"}, ctx)
    assert result["symbol"] == "BTC/USDT"
    assert result["price"] == 159.5  # last close = 100.5 + 59


async def test_get_price_unknown_symbol_returns_no_data_marker(db_session):
    result = await market_tools.get_price({"symbol": "NOTASYMBOL"}, {"db": db_session})
    assert result == {"symbol": "NOTASYMBOL", "available": False}


async def test_get_indicators_returns_expected_snapshot_keys(db_session, seed_btc_1m_candles):
    result = await market_tools.get_indicators(
        {"symbol": "BTC/USDT", "tf": "1m"}, {"db": db_session}
    )
    assert set(result.keys()) == {"symbol", "tf", "rsi", "ema_9", "ema_21", "vwap", "atr", "adx"}
    assert isinstance(result["rsi"], float)


async def test_get_regime_labels_strong_uptrend(db_session, seed_btc_1m_candles):
    result = await market_tools.get_regime(
        {"symbol": "BTC/USDT", "tf": "1m"}, {"db": db_session}
    )
    assert result["regime"] in {"trend_up", "trend_down", "range"}
    assert "adx" in result and "atr_pct" in result


async def test_get_breadth_counts_active_instruments(db_session, seed_btc_1m_candles):
    result = await market_tools.get_breadth({"tf": "1m"}, {"db": db_session})
    assert "pct_above_ema50" in result
    assert result["instruments_counted"] >= 1
