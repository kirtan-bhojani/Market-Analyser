"""The live crypto ingestion pipeline (`run_ingest`) must be reachable as a
process: `python -m app.ingest.runner` for a dedicated `ingest` process type,
and launched alongside web+worker in single-container (`all`) mode. Before this,
`run_ingest` was defined but never called by any entrypoint, so no deployment
ever populated candles.
"""

from pathlib import Path

import app.ingest.runner as runner

ENTRYPOINT = Path(__file__).parents[3] / "docker-entrypoint.sh"


def test_main_invokes_run_ingest(monkeypatch):
    called: dict[str, bool] = {}

    async def fake_run_ingest(**_kwargs) -> None:
        called["ran"] = True

    monkeypatch.setattr(runner, "run_ingest", fake_run_ingest)
    runner.main()
    assert called.get("ran") is True


def test_entrypoint_dispatches_ingest_process_type():
    txt = ENTRYPOINT.read_text()
    assert "ingest)" in txt, "docker-entrypoint.sh has no PROCESS_TYPE=ingest case"
    assert "app.ingest.runner" in txt


def test_all_mode_launches_ingester():
    txt = ENTRYPOINT.read_text()
    all_block = txt.split("all)", 1)[1].split(";;", 1)[0]
    assert "app.ingest.runner" in all_block, "'all' mode does not start the ingester"
