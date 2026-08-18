"""JSON-schema tool definitions exposed to the LLM."""

from __future__ import annotations

from typing import Any

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_price",
        "description": "Latest price for a platform symbol.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "get_candles",
        "description": "Recent OHLCV candles for a symbol and timeframe.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "tf": {"type": "string"},
                "n": {"type": "integer", "default": 100},
            },
            "required": ["symbol", "tf"],
        },
    },
    {
        "name": "get_indicators",
        "description": "RSI/EMA/VWAP/ATR/ADX snapshot for a symbol+timeframe.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}, "tf": {"type": "string"}},
            "required": ["symbol", "tf"],
        },
    },
    {
        "name": "get_regime",
        "description": "Current market regime label for a symbol.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}, "tf": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "get_breadth",
        "description": "Universe-wide market breadth snapshot.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_recent_signals",
        "description": "Recent strategy signals, optionally for one symbol.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "get_scan_hits",
        "description": "Recent scanner rule hits, optionally for one rule.",
        "parameters": {
            "type": "object",
            "properties": {"rule": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "run_quick_backtest",
        "description": "Bounded (max 1y, cached) backtest of a preset strategy.",
        "parameters": {
            "type": "object",
            "properties": {
                "strategy": {"type": "string"},
                "symbol": {"type": "string"},
                "tf": {"type": "string", "default": "1h"},
                "params": {"type": "object"},
            },
            "required": ["strategy", "symbol"],
        },
    },
    {
        "name": "search_kb",
        "description": "Search the trading-education knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 4},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_news",
        "description": "Recent news with sentiment, optionally for one symbol.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": [],
        },
    },
]
