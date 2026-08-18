from app.chat.kb.chunker import chunk_markdown


def test_chunk_markdown_splits_long_doc_into_multiple_chunks():
    text = "Paragraph one. " * 60 + "\n\n" + "Paragraph two. " * 60
    chunks = chunk_markdown("orb.md", text, max_tokens=50)
    assert len(chunks) >= 2
    assert all(c["doc"] == "orb.md" for c in chunks)


def test_chunk_markdown_short_doc_single_chunk():
    chunks = chunk_markdown(
        "glossary.md", "RSI measures momentum on a 0-100 scale.", max_tokens=200
    )
    assert len(chunks) == 1
