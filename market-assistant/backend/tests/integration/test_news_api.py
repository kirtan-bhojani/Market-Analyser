from datetime import UTC, datetime, timedelta

import pytest

from app.models.news_item import NewsItem


@pytest.mark.asyncio
async def test_news_endpoint_returns_items_newest_first(client, db_session):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            NewsItem(
                source="cryptowire",
                title="BTC rallies",
                url="https://example.com/btc",
                published_at=now,
                sentiment=0.8,
                tickers=["BTC/USDT"],
            ),
            NewsItem(
                source="marketwire",
                title="NIFTY dips",
                url="https://example.com/nifty",
                published_at=now - timedelta(hours=2),
                sentiment=-0.1,
                tickers=["NIFTY"],
            ),
        ]
    )
    await db_session.commit()

    resp = await client.get("/api/news", params={"limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert [item["title"] for item in body] == ["BTC rallies", "NIFTY dips"]
    assert body[0]["sentiment"] == pytest.approx(0.8)
    assert body[0]["tickers"] == ["BTC/USDT"]


@pytest.mark.asyncio
async def test_news_endpoint_filters_by_symbol(client, db_session):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            NewsItem(
                source="cryptowire",
                title="BTC rallies",
                url="https://example.com/btc2",
                published_at=now,
                sentiment=0.8,
                tickers=["BTC/USDT"],
            ),
            NewsItem(
                source="marketwire",
                title="NIFTY dips",
                url="https://example.com/nifty2",
                published_at=now - timedelta(hours=2),
                sentiment=-0.1,
                tickers=["NIFTY"],
            ),
        ]
    )
    await db_session.commit()

    resp = await client.get("/api/news", params={"symbol": "BTC/USDT"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "BTC rallies"
    assert body[0]["tickers"] == ["BTC/USDT"]
