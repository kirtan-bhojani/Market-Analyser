import pytest


@pytest.fixture(scope="module")
def embed():
    """Load the local embedding model once; skip the module if it can't load
    (e.g. no network to fetch the model in a sandboxed CI runner)."""
    try:
        from app.chat.kb.embedder import embed_texts

        embed_texts(["warmup"])
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"embedding model unavailable: {exc}")
    return embed_texts


def test_embed_texts_returns_384_dim_vectors(embed):
    vectors = embed(["opening range breakout strategy"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 384


async def test_search_kb_returns_expected_doc_for_fixture_query(db_session, embed):
    from app.chat.tools.kb_tools import search_kb
    from app.models.chat import KBChunk

    db_session.add(
        KBChunk(
            doc="orb.md",
            chunk="Opening range breakout trades the first N bars' high and low.",
            embedding=embed(["Opening range breakout trades the first N bars' high and low."])[0],
        )
    )
    db_session.add(
        KBChunk(
            doc="glossary_indicators.md",
            chunk="RSI measures momentum on a 0-100 scale.",
            embedding=embed(["RSI measures momentum on a 0-100 scale."])[0],
        )
    )
    await db_session.flush()

    result = await search_kb(
        {"query": "what is an opening range breakout", "k": 1}, {"db": db_session}
    )
    assert result["chunks"][0]["doc"] == "orb.md"
