from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.deps import get_engine, get_redis

router = APIRouter()


@router.get("/health")
async def health(response: Response) -> dict[str, str | bool]:
    db_ok = False
    redis_ok = False

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        r = get_redis()
        redis_ok = bool(await r.ping())
    except Exception:
        redis_ok = False

    healthy = db_ok and redis_ok
    # A load balancer / uptime probe must see a non-2xx when a dependency is
    # down; a 200 with db:false silently masks an unhealthy instance.
    response.status_code = (
        status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return {"status": "ok" if healthy else "degraded", "db": db_ok, "redis": redis_ok}
