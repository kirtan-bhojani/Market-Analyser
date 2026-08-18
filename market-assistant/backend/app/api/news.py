from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.models.news_item import NewsItem
from app.schemas.news import NewsItemOut

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("")
async def list_news(
    symbol: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[NewsItemOut]:
    query = select(NewsItem)
    if symbol:
        query = query.where(NewsItem.tickers.contains([symbol]))
    query = query.order_by(NewsItem.published_at.desc()).limit(limit)
    result = await session.execute(query)
    return [NewsItemOut.model_validate(n) for n in result.scalars().all()]
