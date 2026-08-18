from datetime import UTC, datetime, timedelta

import pytest

from app.models.candle import CandleRow
from app.models.instrument import Instrument


async def _seed_two_crypto_with_candles(db_session):
    btc = Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True)
    eth = Instrument(symbol="ETH/USDT", asset_class="crypto", exchange="binance", active=True)
    db_session.add_all([btc, eth])
    await db_session.flush()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    rows = []
    for i in range(60):
        ts = start + timedelta(hours=i)
        rows.append(
            CandleRow(
                instrument_id=btc.id,
                tf="1h",
                ts=ts,
                o=100 + i,
                h=101 + i,
                l=99 + i,
                c=100.5 + i,
                v=10 + i,
            )
        )
        rows.append(
            CandleRow(
                instrument_id=eth.id,
                tf="1h",
                ts=ts,
                o=50 + i * 0.5,
                h=51 + i * 0.5,
                l=49 + i * 0.5,
                c=50.5 + i * 0.5,
                v=5 + i,
            )
        )
    db_session.add_all(rows)
    await db_session.commit()
    return btc, eth


@pytest.mark.asyncio
async def test_correlation_endpoint_returns_square_matrix(client, db_session):
    await _seed_two_crypto_with_candles(db_session)

    resp = await client.get(
        "/api/analytics/correlation",
        params={"asset_class": "crypto", "tf": "1h", "limit": 100},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["symbols"]) == {"BTC/USDT", "ETH/USDT"}
    assert len(body["matrix"]) == 2
    assert all(len(row) == 2 for row in body["matrix"])
    assert body["matrix"][0][0] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_seasonality_endpoint_ok_and_rejects_bad_bucket(client, db_session):
    await _seed_two_crypto_with_candles(db_session)

    resp = await client.get(
        "/api/analytics/seasonality",
        params={"symbol": "BTC/USDT", "tf": "1h", "bucket": "hour"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "hour"
    assert len(body["labels"]) == 24

    bad = await client.get(
        "/api/analytics/seasonality",
        params={"symbol": "BTC/USDT", "tf": "1h", "bucket": "decade"},
    )
    assert bad.status_code == 422
