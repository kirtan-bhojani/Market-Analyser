import uuid

from sqlalchemy import select

from app.chat.orchestrator import run_chat_turn
from app.chat.providers.base import ProviderChunk
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import ToolCall
from tests.support.scripted_provider import ScriptedProvider


async def test_full_chat_turn_calls_tools_and_persists_grounded_answer(db_session, monkeypatch):
    session = ChatSession(user_id=uuid.uuid4())
    db_session.add(session)
    await db_session.flush()

    async def fake_get_indicators(args, ctx):
        return {
            "symbol": "BTC/USDT",
            "tf": "1h",
            "rsi": 62.4,
            "ema_9": 65120.0,
            "ema_21": 64890.0,
            "vwap": 65000.0,
            "atr": 320.5,
            "adx": 28.1,
        }

    from app.chat.tools.router import TOOL_IMPLS

    monkeypatch.setitem(TOOL_IMPLS, "get_indicators", fake_get_indicators)

    provider = ScriptedProvider(
        rounds=[
            [
                ProviderChunk(
                    type="tool_call",
                    tool_call=ToolCall(
                        name="get_indicators", arguments={"symbol": "BTC/USDT", "tf": "1h"}
                    ),
                )
            ],
            [
                ProviderChunk(
                    type="token",
                    text=(
                        "BTC/USDT on 1h has RSI 62.4 and ADX 28.1, indicating a developing "
                        "trend. Educational analysis. Not investment advice. Past performance "
                        "≠ future results."
                    ),
                )
            ],
        ]
    )

    result = await run_chat_turn(
        db_session, str(session.id), "how is BTC looking on 1h?", provider=provider
    )

    assert "RSI 62.4" in result.answer
    assert "Educational analysis" in result.answer
    messages = (
        await db_session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id)
        )
    ).scalars().all()
    assert [m.role for m in messages] == ["user", "tool", "assistant"]


async def test_ungrounded_answer_falls_back(db_session):
    session = ChatSession(user_id=uuid.uuid4())
    db_session.add(session)
    await db_session.flush()

    # No tool calls, but a fabricated price -> grounding fails both times -> fallback.
    provider = ScriptedProvider(
        rounds=[[ProviderChunk(type="token", text="BTC is at $99999.99 right now.")]]
    )
    result = await run_chat_turn(db_session, str(session.id), "price?", provider=provider)
    assert result.answer == "I don't have that data."
    assert result.regenerated is True
