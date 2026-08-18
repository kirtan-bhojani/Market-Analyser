import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ingest.rss import RawNewsItem, fetch_feed
from app.ingest.sentiment import score_batch
from app.models.instrument import Instrument
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)


async def run_news_ingest(ctx: dict[str, Any]) -> int:
    """arq cron job (conceptually every 15 min): fetch configured RSS feeds,
    score sentiment, and insert deduped rows into ``news_items``.

    Dedupe is idempotent via ``INSERT ... ON CONFLICT (url) DO NOTHING``, so a
    re-run over the same feeds inserts nothing new. Returns the number of rows
    actually inserted.
    """
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] = ctx[
        "session_factory"
    ]
    feed_urls: list[str] = ctx.get("feed_urls") or get_settings().NEWS_FEED_URLS

    async with session_factory() as session:
        result = await session.execute(
            select(Instrument.symbol).where(Instrument.active.is_(True))
        )
        symbols = [row[0] for row in result.all()]

    raw_items: list[RawNewsItem] = []
    for url in feed_urls:
        raw_items.extend(fetch_feed(url, symbols=symbols))

    if not raw_items:
        return 0

    scores = score_batch([item.title for item in raw_items])

    rows = [
        {
            "source": item.source,
            "title": item.title,
            "url": item.url,
            "published_at": item.published_at,
            "sentiment": Decimal(str(score)),
            "tickers": item.tickers or None,
        }
        for item, score in zip(raw_items, scores, strict=True)
    ]

    async with session_factory() as session:
        stmt = insert(NewsItem).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=[NewsItem.url])
        exec_result = cast("CursorResult[Any]", await session.execute(stmt))
        await session.commit()
        inserted = exec_result.rowcount

    logger.info("news ingest: %d new items from %d feed(s)", inserted, len(feed_urls))
    return inserted
