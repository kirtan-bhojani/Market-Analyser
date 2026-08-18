import calendar
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True, slots=True)
class RawNewsItem:
    source: str | None
    title: str
    url: str
    published_at: datetime | None
    tickers: list[str]


def _base_asset(symbol: str) -> str:
    # Universe symbols look like "BTC/USDT"; the base asset is the token we
    # match against news titles.
    return symbol.split("/", 1)[0].strip().upper()


def extract_tickers(title: str, symbols: list[str]) -> list[str]:
    """Return base assets from ``symbols`` that appear as whole words in ``title``.

    Matching is case-insensitive and whole-word (so "BTC" does not match
    "BTCASHER"). Order follows ``symbols``; duplicates are removed.
    """
    words = {w.upper() for w in _WORD_RE.findall(title)}
    tickers: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        token = _base_asset(symbol)
        if token in words and token not in seen:
            seen.add(token)
            tickers.append(token)
    return tickers


def fetch_feed(url: str, symbols: list[str] | None = None) -> list[RawNewsItem]:
    """Parse an RSS/Atom feed into ``RawNewsItem``s.

    ``url`` may be an http(s) URL, a local file path, or a raw feed string --
    ``feedparser.parse`` accepts all three. A malformed/incomplete entry
    (missing title or link) is skipped with a warning and never raised,
    mirroring the never-raise discipline of ``parse_binance_kline``.
    """
    symbols = symbols or []
    parsed = feedparser.parse(url)
    source = parsed.feed.get("title") if parsed.feed else None

    items: list[RawNewsItem] = []
    for entry in parsed.entries:
        try:
            title = entry.get("title")
            link = entry.get("link")
            if not title or not link:
                logger.warning("skipping malformed news entry: missing title/link: %r", entry)
                continue
            published_at: datetime | None = None
            published_parsed = entry.get("published_parsed")
            if published_parsed is not None:
                # feedparser normalises published_parsed to a UTC struct_time.
                published_at = datetime.fromtimestamp(
                    calendar.timegm(published_parsed), tz=timezone.utc  # noqa: UP017
                )
            items.append(
                RawNewsItem(
                    source=source,
                    title=title,
                    url=link,
                    published_at=published_at,
                    tickers=extract_tickers(title, symbols),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("skipping malformed news entry: %s: %r", exc, entry)
    return items
