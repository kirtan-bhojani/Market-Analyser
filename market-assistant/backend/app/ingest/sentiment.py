import logging
from functools import lru_cache
from typing import Protocol, TypedDict, cast

logger = logging.getLogger(__name__)

_MODEL_NAME = "ProsusAI/finbert"
_BATCH_SIZE = 16


class _LabelScore(TypedDict):
    label: str
    score: float


class _Pipeline(Protocol):
    def __call__(self, inputs: list[str]) -> list[list[_LabelScore]]: ...


@lru_cache(maxsize=1)
def _get_pipeline() -> _Pipeline:
    """Lazily build (and cache) the FinBERT text-classification pipeline.

    The heavy ``transformers``/``torch`` import lives INSIDE this function so
    that merely importing this module never drags the ML stack into memory.
    Tests patch this function, so the suite runs without those libs installed.
    """
    from transformers import pipeline  # lazy heavy import (kept out of module import)

    logger.info("loading FinBERT sentiment model %s (CPU)", _MODEL_NAME)
    return cast(
        _Pipeline,
        pipeline(
            "text-classification",
            model=_MODEL_NAME,
            top_k=None,
            device=-1,
            batch_size=_BATCH_SIZE,
        ),
    )


def score_batch(titles: list[str]) -> list[float]:
    """Score headlines with FinBERT, returning a signed sentiment in [-1, 1].

    Each score is ``P(positive) - P(negative)`` for that headline. Output order
    matches input order.
    """
    if not titles:
        return []

    raw = _get_pipeline()(titles)
    scores: list[float] = []
    for per_title in raw:
        label_to_score = {ls["label"].lower(): float(ls["score"]) for ls in per_title}
        scores.append(label_to_score.get("positive", 0.0) - label_to_score.get("negative", 0.0))
    return scores
