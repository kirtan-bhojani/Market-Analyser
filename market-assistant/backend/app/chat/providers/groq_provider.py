from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from app.chat.providers.base import ProviderChunk
from app.core.config import get_settings
from app.schemas.chat import ToolCall


class GroqProvider:
    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or get_settings().GROQ_API_KEY
        self.model = model

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=self.api_key)
        stream = await client.chat.completions.create(
            model=self.model,
            messages=cast(Any, messages),
            tools=cast(Any, [{"type": "function", "function": t} for t in tools]),
            stream=True,
        )
        # OpenAI-style streaming splits a single tool call across deltas: the id
        # and name arrive first, then the JSON arguments in fragments. Buffer by
        # call index and emit once the stream finishes so arguments are complete.
        pending: dict[int, dict[str, str]] = {}
        async for event in cast(Any, stream):
            delta = event.choices[0].delta
            if delta.content:
                yield ProviderChunk(type="token", text=delta.content)
            for tc in delta.tool_calls or []:
                buf = pending.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    buf["id"] = tc.id
                fn = tc.function
                if fn is not None:
                    if fn.name:
                        buf["name"] = fn.name
                    if fn.arguments:
                        buf["arguments"] += fn.arguments
        for buf in pending.values():
            if not buf["name"]:
                continue
            yield ProviderChunk(
                type="tool_call",
                tool_call=ToolCall(
                    name=buf["name"],
                    arguments=json.loads(buf["arguments"] or "{}"),
                    id=buf["id"] or None,
                ),
            )
