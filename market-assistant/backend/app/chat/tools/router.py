"""Tool dispatch: maps a tool name to a thin wrapper over existing internals.

Tool implementations register themselves into ``TOOL_IMPLS`` on import (see
``market_tools``/``signal_tools``/``kb_tools``/``news_tools``). Dispatch never
raises: an unknown tool or a failing tool becomes a safe ``ToolResult`` so the
orchestrator's tool-calling loop can continue.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.schemas.chat import ToolCall, ToolResult

logger = logging.getLogger(__name__)

ToolImpl = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]

TOOL_IMPLS: dict[str, ToolImpl] = {}


async def dispatch_tool_call(call: ToolCall, ctx: dict[str, Any]) -> ToolResult:
    impl = TOOL_IMPLS.get(call.name)
    if impl is None:
        return ToolResult(name=call.name, ok=False, error=f"Unknown tool: {call.name}")
    try:
        data = await impl(call.arguments, ctx)
        return ToolResult(name=call.name, ok=True, data=data)
    except Exception:
        logger.exception("Tool %s failed", call.name)
        return ToolResult(
            name=call.name, ok=False, error="That data source is temporarily unavailable."
        )
