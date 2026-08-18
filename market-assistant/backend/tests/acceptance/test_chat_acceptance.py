import uuid

import pytest

from app.chat.orchestrator import run_chat_turn
from app.chat.providers.base import ProviderChunk
from app.models.chat import ChatSession
from app.schemas.chat import ToolCall
from tests.support.scripted_provider import ScriptedProvider

pytestmark = pytest.mark.acceptance


async def _new_session(db_session) -> str:
    session = ChatSession(user_id=uuid.uuid4())
    db_session.add(session)
    await db_session.flush()
    return str(session.id)


async def test_btc_1h_cites_tools_and_recommends_with_disclaimer(db_session, monkeypatch):
    from app.chat.tools.router import TOOL_IMPLS

    async def fake_indicators(args, ctx):
        return {"symbol": "BTC/USDT", "tf": "1h", "rsi": 58.2, "ema_9": 65200.0,
                "ema_21": 64950.0, "vwap": 65100.0, "atr": 300.0, "adx": 24.0}

    async def fake_regime(args, ctx):
        return {"symbol": "BTC/USDT", "regime": "trend_up", "adx": 24.0, "atr_pct": 0.46}

    monkeypatch.setitem(TOOL_IMPLS, "get_indicators", fake_indicators)
    monkeypatch.setitem(TOOL_IMPLS, "get_regime", fake_regime)

    provider = ScriptedProvider(rounds=[
        [ProviderChunk(type="tool_call",
                       tool_call=ToolCall(name="get_indicators",
                                          arguments={"symbol": "BTC/USDT", "tf": "1h"}))],
        [ProviderChunk(type="tool_call",
                       tool_call=ToolCall(name="get_regime", arguments={"symbol": "BTC/USDT"}))],
        [ProviderChunk(type="token", text=(
            "BTC/USDT on 1h has RSI 58.2 with ADX 24.0, consistent with an early uptrend "
            "regime. A trend-following preset such as EMA(9/21)+VWAP filter fits this "
            "configuration; historically such setups favor pullback entries over chasing "
            "breakouts. Educational analysis. Not investment advice. Past performance ≠ "
            "future results."
        ))],
    ])

    result = await run_chat_turn(
        db_session, await _new_session(db_session),
        "how is BTC looking on 1h and what strategy fits?", provider=provider,
    )
    disclaimer = "Educational analysis. Not investment advice. Past performance ≠ future results."
    assert "rsi" in result.answer.lower()
    assert any(e.name in ("get_indicators", "get_regime") for e in result.tool_events)
    assert disclaimer in result.answer


async def test_doge_buy_now_gives_educational_framing_no_imperative(db_session):
    provider = ScriptedProvider(rounds=[[ProviderChunk(type="token", text=(
        "Educational note: 'buying right now' framing isn't something this assistant can "
        "act on. Looking at DOGE's typical setup characteristics, meme-coin assets carry "
        "elevated volatility risk and thinner liquidity than majors, so position sizing and "
        "stop-loss discipline matter more here. Educational analysis. Not investment advice. "
        "Past performance ≠ future results."
    ))]])
    result = await run_chat_turn(
        db_session, await _new_session(db_session), "should I buy DOGE right now?",
        provider=provider,
    )
    lowered = result.answer.lower()
    assert "you should buy" not in lowered
    assert "guaranteed" not in lowered
    assert "risk" in lowered


async def test_unknown_symbol_returns_no_data(db_session):
    provider = ScriptedProvider(
        rounds=[[ProviderChunk(type="token", text="I don't have that data.")]]
    )
    result = await run_chat_turn(
        db_session, await _new_session(db_session), "how is ZZZFAKECOIN doing?",
        provider=provider,
    )
    assert "don't have that data" in result.answer.lower()
