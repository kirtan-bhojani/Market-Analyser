from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

from app.schemas.chat import ToolCall


@dataclass
class ProviderChunk:
    type: Literal["token", "tool_call"]
    text: str | None = None
    tool_call: ToolCall | None = None


@runtime_checkable
class LLMProvider(Protocol):
    def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]: ...
