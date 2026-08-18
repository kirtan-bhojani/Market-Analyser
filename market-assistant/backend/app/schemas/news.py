from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str | None = None
    title: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    sentiment: float | None = None
    tickers: list[str] | None = None
