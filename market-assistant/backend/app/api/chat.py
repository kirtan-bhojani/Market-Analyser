"""Chat API: session CRUD + an SSE turn-streaming endpoint.

Sessions are scoped to the current user (Phase-11 auth stub via
``get_current_user_id``). The turn endpoint runs the orchestrator, then streams
tool-activity and token events as ``text/event-stream``.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat import orchestrator
from app.chat.quota import LlmQuotaGuard
from app.chat.rate_limit import check_rate_limit
from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.deps import get_redis, get_session
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import ChatMessageOut, ChatSessionOut, ChatTurnRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", status_code=201, response_model=ChatSessionOut)
async def create_session(
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ChatSession:
    row = ChatSession(user_id=user_id)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[ChatSession]:
    rows = (
        await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_messages(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[ChatMessage]:
    owner = await session.get(ChatSession, session_id)
    if owner is None or owner.user_id != user_id:
        return []
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        )
    ).scalars().all()
    return list(rows)


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/sessions/{session_id}/turns")
async def stream_turn(
    session_id: uuid.UUID,
    body: ChatTurnRequest,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> StreamingResponse:
    # Ownership check FIRST: a caller must not learn (via a 429) that a session
    # they don't own exists, nor burn their rate-limit budget on foreign ids.
    owner = await session.get(ChatSession, session_id)
    if owner is None or owner.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    if not await check_rate_limit(str(user_id)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again later.")

    quota_guard = LlmQuotaGuard(
        redis_client=get_redis(), daily_quota=get_settings().llm_daily_quota
    )

    async def event_stream() -> AsyncIterator[str]:
        try:
            result = await orchestrator.run_chat_turn(
                session, str(session_id), body.message, quota_guard=quota_guard
            )
        except Exception:
            # Provider outage / missing API key / unexpected failure: surface a
            # clean error event instead of an aborted stream so the UI can react.
            logger.exception("Chat turn failed for session %s", session_id)
            yield _sse(
                {
                    "type": "error",
                    "payload": {"message": "The assistant is unavailable right now."},
                }
            )
            return
        for event in result.tool_events:
            yield _sse({"type": "tool_call", "payload": {"name": event.name, "ok": event.ok}})
        for token in result.answer.split(" "):
            yield _sse({"type": "token", "payload": {"text": token + " "}})
        yield _sse({"type": "done", "payload": {"answer": result.answer}})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
