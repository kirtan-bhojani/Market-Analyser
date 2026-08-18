"""Split a markdown doc into word-bounded chunks for embedding."""

from __future__ import annotations


def chunk_markdown(doc: str, text: str, max_tokens: int = 200) -> list[dict[str, str]]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[dict[str, str]] = []
    buffer: list[str] = []
    count = 0
    for para in paragraphs:
        words = para.split()
        if count + len(words) > max_tokens and buffer:
            chunks.append({"doc": doc, "chunk": " ".join(buffer)})
            buffer, count = [], 0
        buffer.extend(words)
        count += len(words)
    if buffer:
        chunks.append({"doc": doc, "chunk": " ".join(buffer)})
    return chunks
