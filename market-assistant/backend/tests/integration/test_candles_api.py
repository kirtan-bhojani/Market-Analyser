from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.models.candle import CandleRow
from app.models.instrument import Instrument


@pytest.mark.asyncio
async def test_get_candles_ordered_and_paginated(client: AsyncClient, seed_btc_1m_candles):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
            "limit": 10,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    candles = body["candles"]
    assert len(candles) == 10
    timestamps = [c["ts"] for c in candles]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_get_candles_bad_tf_returns_422(client: AsyncClient):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "3m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_candles_empty_range_returns_empty_list(client: AsyncClient, seed_btc_1m_candles):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2099-01-01T00:00:00Z",
            "to": "2099-01-02T00:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["candles"] == []


@pytest.mark.asyncio
async def test_get_candles_unknown_symbol_returns_empty_list(client: AsyncClient):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "NOPE/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["candles"] == []
    assert body["delayed"] is False
    assert body["delay_minutes"] == 0


@pytest.mark.asyncio
async def test_equity_candles_response_flagged_delayed(client: AsyncClient, db_session):
    instrument = Instrument(symbol="RELIANCE.NS", asset_class="equity", exchange="NSE", active=True)
    db_session.add(instrument)
    await db_session.flush()
    db_session.add(
        CandleRow(
            instrument_id=instrument.id, tf="1m",
            ts=datetime(2025, 6, 9, 10, 0, tzinfo=UTC),
            o=2900, h=2910, l=2895, c=2905, v=120000,
        )
    )
    await db_session.commit()

    resp = await client.get(
        "/candles",
        params={
            "symbol": "RELIANCE.NS",
            "tf": "1m",
            "from": "2025-06-09T00:00:00Z",
            "to": "2025-06-09T23:59:59Z",
        },
    )
    body = resp.json()

    assert resp.status_code == 200
    assert body["delayed"] is True
    assert body["delay_minutes"] == 15


@pytest.mark.asyncio
async def test_crypto_candles_response_not_delayed(
    client: AsyncClient, db_session, seed_btc_1m_candles
):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    body = resp.json()

    assert body["delayed"] is False
    assert body["delay_minutes"] == 0
