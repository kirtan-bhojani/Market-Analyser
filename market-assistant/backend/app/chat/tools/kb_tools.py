"""``search_kb``: pgvector cosine-similarity lookup over the knowledge base."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.kb.embedder import embed_texts_async
from app.chat.tools.router import TOOL_IMPLS
from app.models.chat import KBChunk


async def search_kb(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    query = args["query"]
    k = int(args.get("k", 4))
    db: AsyncSession = ctx["db"]
    vector = (await embed_texts_async([query]))[0]
    stmt = select(KBChunk).order_by(KBChunk.embedding.cosine_distance(vector)).limit(k)
    rows = (await db.execute(stmt)).scalars().all()
    return {"chunks": [{"doc": r.doc, "chunk": r.chunk} for r in rows]}


TOOL_IMPLS["search_kb"] = search_kb
