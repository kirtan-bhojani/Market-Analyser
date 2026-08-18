from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from app.chat.providers.base import ProviderChunk
from app.core.config import get_settings
from app.schemas.chat import ToolCall


def _to_anthropic(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Translate the orchestrator's OpenAI-style transcript to Anthropic shape.

    - "system" messages are lifted out to the top-level ``system`` param.
    - An assistant turn carrying ``tool_calls`` becomes an assistant message
      whose content is a list of (optional text +) ``tool_use`` blocks.
    - A "tool" result message becomes a ``tool_result`` block inside a "user"
      message, keyed by the same ``tool_call_id`` so Anthropic can pair them.
    """
    system_parts: list[str] = []
    convo: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(m["content"])
        elif role == "assistant" and m.get("tool_calls"):
            blocks: list[dict[str, Any]] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m["tool_calls"]:
                fn = tc["function"]
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": fn["name"],
                        "input": json.loads(fn["arguments"] or "{}"),
                    }
                )
            convo.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            convo.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id", ""),
                            "content": m.get("content", ""),
                        }
                    ],
                }
            )
        else:
            convo.append({"role": role, "content": m.get("content", "")})
    return "\n\n".join(system_parts), convo


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t["parameters"],
            }
            for t in tools
        ]
        system, convo = _to_anthropic(messages)
        async with client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=cast(Any, convo),
            tools=cast(Any, anthropic_tools),
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield ProviderChunk(type="token", text=event.delta.text)
                elif event.type == "content_block_stop" and (
                    getattr(event.content_block, "type", None) == "tool_use"
                ):
                    block: Any = event.content_block
                    yield ProviderChunk(
                        type="tool_call",
                        tool_call=ToolCall(
                            name=block.name, arguments=dict(block.input), id=block.id
                        ),
                    )
