import asyncio
import contextlib

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


@router.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket, token: str = Query(...)) -> None:
    # Channels are keyed by symbol:tf (not per-user), so any valid token admits
    # the connection; we only need to authenticate before accepting.
    if await authenticate_ws(websocket, token) is None:
        return  # authenticate_ws already closed the handshake (1008).
    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    forward_task: asyncio.Task[None] | None = None
    try:
        while True:
            msg = await websocket.receive_json()
            # A non-object frame (array/number/string) has no `.get`; skip it
            # rather than letting it crash the receive loop and drop the socket.
            if not isinstance(msg, dict):
                continue
            channel = msg.get("subscribe")
            if not channel:
                continue
            # C3: only `signals:*` channels are public per-symbol feeds. Reject
            # any other prefix (e.g. another user's `scan_hits:<uuid>`) so an
            # authed client can never subscribe its way into private data.
            if not channel.startswith("signals:"):
                await websocket.close(code=1008)
                break
            if forward_task is not None:
                # Await the cancelled forwarder before reusing the pubsub, else
                # the old _forward can still be mid-listen() on the same pubsub
                # when we unsubscribe/resubscribe -> two readers racing on it.
                forward_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await forward_task
                await pubsub.unsubscribe()
            await pubsub.subscribe(channel)
            forward_task = asyncio.create_task(_forward(pubsub, websocket))
    except WebSocketDisconnect:
        pass
    finally:
        if forward_task is not None:
            forward_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await forward_task
        await pubsub.aclose()  # type: ignore[no-untyped-call]
