import logging

from app.ingest.rss import extract_tickers, fetch_feed

FEED_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Crypto News</title>
    <item>
      <title>BTC surges past 70k</title>
      <link>https://example.com/a</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>ETH devs ship update</title>
      <link>https://example.com/b</link>
      <pubDate>Mon, 01 Jan 2024 13:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Malformed entry with no link</title>
    </item>
  </channel>
</rss>
"""


def _write_feed(tmp_path) -> str:
    path = tmp_path / "feed.xml"
    path.write_text(FEED_XML)
    return str(path)


def test_fetch_feed_parses_valid_entries(tmp_path):
    items = fetch_feed(_write_feed(tmp_path), symbols=["BTC/USDT", "ETH/USDT"])

    assert [i.title for i in items] == [
        "BTC surges past 70k",
        "ETH devs ship update",
    ]
    first = items[0]
    assert first.source == "Crypto News"
    assert first.url == "https://example.com/a"
    assert first.published_at is not None
    assert first.published_at.tzinfo is not None
    assert first.tickers == ["BTC"]
    assert items[1].tickers == ["ETH"]


def test_malformed_entry_is_skipped_and_logged_not_raised(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        items = fetch_feed(_write_feed(tmp_path), symbols=["BTC/USDT"])

    assert len(items) == 2
    assert any("malformed" in r.getMessage().lower() for r in caplog.records)


def test_extract_tickers_is_case_insensitive_whole_word():
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    assert extract_tickers("btc rallies while SOL dips", symbols) == ["BTC", "SOL"]
    # substring, not whole word, must not match
    assert extract_tickers("BTCASHER announces raise", symbols) == []
