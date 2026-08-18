"""Per-user fixed-window chat rate limiting via Redis."""

from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def check_rate_limit(
    user_id: str,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> bool:
    """Return True if the user is under the cap, False if they've exceeded it.

    Fail-closed: this limiter guards the (paid, finite) LLM budget, so if Redis
    is unreachable we DENY rather than allow unbounded, un-metered chat.
    """
    from app.core.deps import get_redis

    settings = get_settings()
    limit = settings.CHAT_RATE_LIMIT if limit is None else limit
    window_seconds = settings.CHAT_RATE_WINDOW_SECONDS if window_seconds is None else window_seconds

    key = f"chat_rate_limit:{user_id}"
    try:
        redis = get_redis()
        count = await redis.incr(key)
        # H6: EXPIRE NX on every call keeps the window fixed and self-heals a
        # counter left TTL-less by a crash between INCR and EXPIRE.
        await redis.expire(key, window_seconds, nx=True)
    except Exception:
        logger.warning("chat rate-limit Redis error; failing closed", exc_info=True)
        return False
    return bool(count <= limit)
