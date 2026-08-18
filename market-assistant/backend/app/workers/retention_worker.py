"""Phase 12 Task 4: daily arq job dropping 1m candles past the retention window."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.deps import get_sessionmaker
from app.core.retention import drop_old_candles

logger = logging.getLogger(__name__)


async def retention_job(ctx: dict[str, Any]) -> int:
    settings = get_settings()
    session_factory = ctx.get("session_factory") or get_sessionmaker()
    async with session_factory() as session:
        deleted = await drop_old_candles(
            session,
            tf="1m",
            older_than_days=settings.candle_retention_days,
            now=datetime.now(UTC),
        )
    logger.info("retention_job deleted %d old 1m candle rows", deleted)
    return deleted
