from __future__ import annotations

from typing import Any

import httpx

DISCLAIMER = "Educational analysis. Not investment advice. Past performance ≠ future results."


def format_hit_message(hit: dict[str, Any]) -> str:
    payload_str = ", ".join(f"{k}={v}" for k, v in (hit.get("payload") or {}).items())
    return (
        f"Scan hit: {hit['symbol']}\n"
        f"Rule: {hit['rule_name']}\n"
        f"Time: {hit['ts']}\n"
        f"Values: {payload_str}"
    )


def format_signal_message(signal: dict[str, Any]) -> str:
    lines = [
        f"Signal: {signal['symbol']} ({signal['strategy']}, {signal['direction']})",
        f"Time: {signal['ts']}",
        f"Ref entry={signal['ref_entry']} SL={signal['ref_sl']} TP={signal['ref_tp']}",
    ]
    if signal.get("confidence") is not None:
        lines.append(f"confidence={signal['confidence']}")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


class TelegramSendResult:
    def __init__(self, ok: bool, status_code: int, description: str = "") -> None:
        self.ok = ok
        self.status_code = status_code
        self.description = description


async def send_telegram_message(
    bot_token: str, target: str, text: str, client: httpx.AsyncClient | None = None
) -> TelegramSendResult:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": target, "text": text}
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=5.0)
    try:
        resp = await http_client.post(url, json=payload)
        data = resp.json()
        return TelegramSendResult(
            ok=bool(data.get("ok", False)),
            status_code=resp.status_code,
            description=str(data.get("description", "")),
        )
    finally:
        if owns_client:
            await http_client.aclose()
