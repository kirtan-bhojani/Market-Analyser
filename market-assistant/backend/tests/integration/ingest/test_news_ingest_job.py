import pytest
from sqlalchemy import func, select

from app.models.instrument import Instrument
from app.models.news_item import NewsItem
from app.workers.news_worker import run_news_ingest

FEED_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Crypto News</title>
    <item>
      <title>BTC surges past 70k</title>
      <link>https://example.com/btc</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>ETH devs ship update</title>
      <link>https://example.com/eth</link>
      <pubDate>Mon, 01 Jan 2024 13:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


@pytest.mark.asyncio
async def test_news_ingest_job_is_idempotent_and_populates_tickers(
    db_session, session_factory, tmp_path, monkeypatch
):
    db_session.add(Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance"))
    db_session.add(Instrument(symbol="ETH/USDT", asset_class="crypto", exchange="binance"))
    await db_session.commit()

    feed = tmp_path / "feed.xml"
    feed.write_text(FEED_XML)

    # Mock FinBERT at the loader boundary so transformers/torch are never needed.
    monkeypatch.setattr(
        "app.workers.news_worker.score_batch",
        lambda titles: [0.42 for _ in titles],
    )

    ctx = {"session_factory": session_factory, "feed_urls": [str(feed)]}

    first = await run_news_ingest(ctx)
    second = await run_news_ingest(ctx)

    assert first == 2
    assert second == 0  # url dedupe -> idempotent

    total = await db_session.scalar(select(func.count()).select_from(NewsItem))
    assert total == 2

    btc = await db_session.scalar(
        select(NewsItem).where(NewsItem.url == "https://example.com/btc")
    )
    assert btc is not None
    assert btc.tickers == ["BTC"]
    assert btc.sentiment is not None
    assert btc.source == "Crypto News"
