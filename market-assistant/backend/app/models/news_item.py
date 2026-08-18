from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, Text
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, unique=True)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    sentiment: Mapped[Decimal | None] = mapped_column(Numeric)
    tickers: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
