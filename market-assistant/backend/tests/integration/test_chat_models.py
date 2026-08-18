import uuid

from app.models.chat import ChatMessage, ChatSession, KBChunk


async def test_chat_session_and_message_round_trip(db_session):
    session = ChatSession(user_id=uuid.uuid4())
    db_session.add(session)
    await db_session.flush()

    msg = ChatMessage(
        session_id=session.id,
        role="user",
        content="how is BTC looking on 1h?",
        tool_calls=None,
    )
    db_session.add(msg)
    await db_session.flush()

    fetched = await db_session.get(ChatMessage, msg.id)
    assert fetched.role == "user"
    assert fetched.session_id == session.id


async def test_kb_chunk_stores_384dim_embedding(db_session):
    chunk = KBChunk(doc="glossary.md", chunk="RSI measures momentum...", embedding=[0.0] * 384)
    db_session.add(chunk)
    await db_session.flush()
    fetched = await db_session.get(KBChunk, chunk.id)
    assert len(fetched.embedding) == 384
