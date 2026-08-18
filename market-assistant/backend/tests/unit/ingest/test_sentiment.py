
from app.ingest import sentiment
from app.ingest.sentiment import score_batch


def _fake_pipeline(titles):
    out = []
    for title in titles:
        lowered = title.lower()
        if "surge" in lowered or "rally" in lowered:
            out.append(
                [
                    {"label": "positive", "score": 0.90},
                    {"label": "negative", "score": 0.05},
                    {"label": "neutral", "score": 0.05},
                ]
            )
        else:
            out.append(
                [
                    {"label": "positive", "score": 0.04},
                    {"label": "negative", "score": 0.91},
                    {"label": "neutral", "score": 0.05},
                ]
            )
    return out


def test_score_batch_sign_and_order_preserved(monkeypatch):
    monkeypatch.setattr(sentiment, "_get_pipeline", lambda: _fake_pipeline)

    titles = ["Bitcoin surges to record high", "Ethereum crashes on outage"]
    scores = score_batch(titles)

    assert len(scores) == 2
    assert scores[0] > 0  # positive headline
    assert scores[1] < 0  # negative headline
    # order preserved: reversing the input reverses the output
    reversed_scores = score_batch(list(reversed(titles)))
    assert reversed_scores == list(reversed(scores))


def test_empty_batch_returns_empty(monkeypatch):
    monkeypatch.setattr(sentiment, "_get_pipeline", lambda: _fake_pipeline)
    assert score_batch([]) == []


def test_importing_sentiment_does_not_import_transformers():
    # The heavy ML libraries must be loaded lazily inside _get_pipeline, so a
    # bare import of the module must not drag transformers/torch into the
    # interpreter. Checked in a FRESH subprocess so other tests that legitimately
    # load transformers/torch earlier in this session (e.g. the KB embedder) can't
    # pollute the global sys.modules this assertion inspects.
    import subprocess
    import sys as _sys

    code = (
        "import sys; import app.ingest.sentiment;"
        " assert 'transformers' not in sys.modules, 'transformers imported eagerly';"
        " assert 'torch' not in sys.modules, 'torch imported eagerly'"
    )
    result = subprocess.run([_sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
