from __future__ import annotations

from typing import cast

from app.chat.providers.anthropic_provider import AnthropicProvider
from app.chat.providers.base import LLMProvider
from app.chat.providers.gemini_provider import GeminiProvider
from app.chat.providers.groq_provider import GroqProvider
from app.core.config import get_settings

_PROVIDERS: dict[str, type] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}


def get_provider() -> LLMProvider:
    name = get_settings().LLM_PROVIDER
    if name not in _PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {name!r}, expected one of {list(_PROVIDERS)}"
        )
    return cast(LLMProvider, _PROVIDERS[name]())
