from __future__ import annotations

import httpx
import pytest

from app.alerts.telegram import (
    DISCLAIMER,
    format_hit_message,
    format_signal_message,
    send_telegram_message,
)


def test_format_hit_message_includes_symbol_rule_ts_and_payload() -> None:
    hit = {
        "symbol": "BTC/USDT",
        "rule_name": "RSI(5m)<30 AND relVol>2",
        "ts": "2026-07-11T12:00:00Z",
        "payload": {"rsi": 27.4, "rel_volume": 2.3},
    }
    msg = format_hit_message(hit)
    assert "BTC/USDT" in msg
    assert "RSI(5m)<30 AND relVol>2" in msg
    assert "2026-07-11T12:00:00Z" in msg
    assert "rsi=27.4" in msg
    assert "rel_volume=2.3" in msg


def test_format_signal_message_with_confidence() -> None:
    signal = {
        "symbol": "BTC/USDT",
        "strategy": "orb",
        "direction": "long",
        "ts": "2026-07-11T12:05:00Z",
        "ref_entry": 65000.0,
        "ref_sl": 64500.0,
        "ref_tp": 66000.0,
        "confidence": 0.72,
    }
    msg = format_signal_message(signal)
    assert "BTC/USDT" in msg
    assert "orb" in msg
    assert "long" in msg
    assert "2026-07-11T12:05:00Z" in msg
    assert "entry=65000.0" in msg
    assert "SL=64500.0" in msg
    assert "TP=66000.0" in msg
    assert "confidence=0.72" in msg
    assert DISCLAIMER in msg
    assert "Past performance ≠ future results." in msg


def test_format_signal_message_without_confidence_omits_confidence_line() -> None:
    signal = {
        "symbol": "ETH/USDT",
        "strategy": "orb",
        "direction": "short",
        "ts": "2026-07-11T12:10:00Z",
        "ref_entry": 3500.0,
        "ref_sl": 3550.0,
        "ref_tp": 3400.0,
        "confidence": None,
    }
    msg = format_signal_message(signal)
    assert "confidence=" not in msg
    assert DISCLAIMER in msg


@pytest.mark.asyncio
async def test_send_telegram_message_posts_to_expected_url_and_payload() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = httpx.Request(
            request.method, request.url, content=request.content
        ).read()
        return httpx.Response(200, json={"ok": True, "description": ""})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await send_telegram_message(
            bot_token="TESTTOKEN",
            target="12345",
            text="hello",
            client=client,
        )

    assert result.ok is True
    assert result.status_code == 200
    assert captured["url"] == "https://api.telegram.org/botTESTTOKEN/sendMessage"


@pytest.mark.asyncio
async def test_send_telegram_message_reports_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "Bad Request"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await send_telegram_message(
            bot_token="TESTTOKEN",
            target="12345",
            text="hello",
            client=client,
        )

    assert result.ok is False
    assert result.status_code == 400
    assert result.description == "Bad Request"
