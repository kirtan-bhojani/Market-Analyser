from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from app.chat.providers.base import ProviderChunk
from app.core.config import get_settings
from app.schemas.chat import ToolCall


def _to_gemini(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Translate the orchestrator's OpenAI-style transcript to Gemini shape.

    Gemini uses ``system_instruction`` (returned separately), roles "user" /
    "model", and typed parts: ``function_call`` for a tool request and
    ``function_response`` for its result. Pairing is by name, not id.
    """
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(m["content"])
        elif role == "assistant" and m.get("tool_calls"):
            parts: list[Any] = []
            if m.get("content"):
                parts.append(m["content"])
            for tc in m["tool_calls"]:
                fn = tc["function"]
                parts.append(
                    {
                        "function_call": {
                            "name": fn["name"],
                            "args": json.loads(fn["arguments"] or "{}"),
                        }
                    }
                )
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": m.get("name", "tool"),
                                "response": {"result": m.get("content", "")},
                            }
                        }
                    ],
                }
            )
        else:
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [m.get("content", "")]})
    return "\n\n".join(system_parts), contents


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or get_settings().GEMINI_API_KEY
        self.model = model

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ProviderChunk]:
        import google.generativeai as _genai

        genai: Any = _genai
        genai.configure(api_key=self.api_key)
        system, contents = _to_gemini(messages)
        model = genai.GenerativeModel(
            self.model, tools=tools, system_instruction=system or None
        )
        response = await model.generate_content_async(contents, stream=True)
        async for chunk in response:
            if getattr(chunk, "text", None):
                yield ProviderChunk(type="token", text=chunk.text)
            for call in getattr(chunk, "function_calls", None) or []:
                yield ProviderChunk(
                    type="tool_call",
                    tool_call=ToolCall(name=call.name, arguments=dict(call.args)),
                )
