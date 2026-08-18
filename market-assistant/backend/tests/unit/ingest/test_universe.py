from unittest.mock import AsyncMock

import pytest

from app.ingest.universe import get_top_n_by_volume


@pytest.mark.asyncio
async def test_returns_top_n_symbols_sorted_by_quote_volume_desc():
    fake_tickers = {
        "BTC/USDT": {"quoteVolume": 500_000_000},
        "ETH/USDT": {"quoteVolume": 300_000_000},
        "DOGE/BTC": {"quoteVolume": 999_000_000},  # wrong quote asset, excluded
        "SOL/USDT": {"quoteVolume": 100_000_000},
        "ADA/USDT": {"quoteVolume": 50_000_000},
    }
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(return_value=fake_tickers)

    result = await get_top_n_by_volume(exchange, n=3, quote_asset="USDT")

    assert result == ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


@pytest.mark.asyncio
async def test_fewer_symbols_than_n_returns_all_available():
    fake_tickers = {
        "BTC/USDT": {"quoteVolume": 500_000_000},
        "ETH/USDT": {"quoteVolume": 300_000_000},
    }
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(return_value=fake_tickers)

    result = await get_top_n_by_volume(exchange, n=20, quote_asset="USDT")

    assert result == ["BTC/USDT", "ETH/USDT"]
