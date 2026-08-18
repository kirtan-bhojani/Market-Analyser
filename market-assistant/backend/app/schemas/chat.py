"""Pydantic wire schemas for the chat/RAG assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: UUID
    role: Literal["user", "assistant", "tool"]
    content: str | None
    tool_calls: list[dict[str, Any]] | dict[str, Any] | None
    created_at: datetime


class ChatTurnRequest(BaseModel):
    message: str


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
    # Provider-assigned call id, used to pair the assistant tool_use turn with
    # its tool result across rounds. Synthesized by the orchestrator if a
    # provider does not supply one.
    id: str | None = None


class ToolResult(BaseModel):
    name: str
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class ChatStreamEvent(BaseModel):
    type: Literal["token", "tool_call", "tool_result", "done", "error"]
    payload: dict[str, Any]
