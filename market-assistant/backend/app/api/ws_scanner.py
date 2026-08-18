from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from redis.asyncio.client import PubSub

from app.core.auth import authenticate_ws
from app.core.deps import get_redis

router = APIRouter()


async def _forward(pubsub: PubSub, websocket: WebSocket) -> None:
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        data = message["data"]
        # decode_responses=True yields str; guard bytes defensively.
        if isinstance(data, bytes):
            data = data.decode()
        await websocket.send_text(data)


@router.websocket("/ws/scanner/hits")
async def scanner_hits_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    user_id = await authenticate_ws(websocket, token)
    if user_id is None:
        return  # authenticate_ws already closed the handshake (1008).
    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"scan_hits:{user_id}"
    await pubsub.subscribe(channel)
    try:
        await _forward(pubsub, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()  # type: ignore[no-untyped-call]
