from datetime import UTC, datetime

from app.chat.tools import news_tools
from app.models.news_item import NewsItem


async def test_get_news_filters_by_symbol(db_session):
    db_session.add(
        NewsItem(
            source="rss",
            title="BTC ETF inflows rise",
            url="http://example.com/btc",
            published_at=datetime(2024, 1, 2, tzinfo=UTC),
            sentiment=0.4,
            tickers=["BTC"],
        )
    )
    db_session.add(
        NewsItem(
            source="rss",
            title="ETH upgrade shipped",
            url="http://example.com/eth",
            published_at=datetime(2024, 1, 1, tzinfo=UTC),
            sentiment=0.1,
            tickers=["ETH"],
        )
    )
    await db_session.flush()

    result = await news_tools.get_news({"symbol": "BTC/USDT"}, {"db": db_session})
    assert len(result["news"]) == 1
    assert result["news"][0]["title"] == "BTC ETF inflows rise"
    assert result["news"][0]["sentiment"] == 0.4


async def test_get_news_no_symbol_returns_general_feed(db_session):
    result = await news_tools.get_news({}, {"db": db_session})
    assert result["news"] == []
