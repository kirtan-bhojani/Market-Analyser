"""ORM models over the Phase-1 kb_chunks / chat_sessions / chat_messages tables.

These tables are created by ``alembic/versions/0001_initial_schema.py`` (raw
DDL, incl. ``embedding VECTOR(384)``); no new migration is needed here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    doc: Mapped[str] = mapped_column(Text, nullable=False)
    chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user | assistant | tool
    content: Mapped[str | None] = mapped_column(Text)
    tool_calls: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
