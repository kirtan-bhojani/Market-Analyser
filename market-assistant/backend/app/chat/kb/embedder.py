"""Local sentence-transformers embeddings (bge-small-en, 384-dim)."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, cast


@lru_cache(maxsize=1)
def _model() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("BAAI/bge-small-en")


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = _model().encode(texts, normalize_embeddings=True).tolist()
    return cast(list[list[float]], vectors)


async def embed_texts_async(texts: list[str]) -> list[list[float]]:
    """Off-load the CPU-bound encode to a thread so it doesn't block the event
    loop during a chat turn (mirrors signal_tools' run_signal_backtest offload).
    """
    return await asyncio.to_thread(embed_texts, texts)
