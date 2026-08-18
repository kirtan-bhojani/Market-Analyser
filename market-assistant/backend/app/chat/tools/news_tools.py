"""``get_news``: recent news items with sentiment, optionally per symbol."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.tools.router import TOOL_IMPLS
from app.models.news_item import NewsItem


async def get_news(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    db: AsyncSession = ctx["db"]
    symbol = args.get("symbol")
    stmt = select(NewsItem)
    if symbol:
        ticker = symbol.split("/")[0]
        stmt = stmt.where(NewsItem.tickers.any(ticker))
    stmt = stmt.order_by(NewsItem.published_at.desc()).limit(5)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "news": [
            {
                "title": r.title,
                "url": r.url,
                "sentiment": float(r.sentiment) if r.sentiment is not None else None,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            }
            for r in rows
        ]
    }


TOOL_IMPLS["get_news"] = get_news
