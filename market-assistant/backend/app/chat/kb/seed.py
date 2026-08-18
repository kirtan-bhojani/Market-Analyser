"""Chunk → embed → upsert the curated KB docs into ``kb_chunks``.

Run as a module against the async DB: ``python -m app.chat.kb.seed``.
"""

from __future__ import annotations

import asyncio
import pathlib

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.kb.chunker import chunk_markdown
from app.chat.kb.embedder import embed_texts
from app.models.chat import KBChunk

DOCS_DIR = pathlib.Path(__file__).parent / "seed_docs"


async def seed_kb(session: AsyncSession) -> int:
    await session.execute(delete(KBChunk))
    total = 0
    for path in sorted(DOCS_DIR.glob("*.md")):
        chunks = chunk_markdown(path.stem, path.read_text())
        vectors = embed_texts([c["chunk"] for c in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            session.add(KBChunk(doc=chunk["doc"], chunk=chunk["chunk"], embedding=vector))
            total += 1
    await session.commit()
    return total


async def _main() -> None:
    from app.core.deps import get_sessionmaker

    async with get_sessionmaker()() as session:
        n = await seed_kb(session)
        print(f"Seeded {n} KB chunks")


if __name__ == "__main__":
    asyncio.run(_main())
