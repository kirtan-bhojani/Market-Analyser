"""Phase 12 Task 7: deploy.yml wires the expected test -> deploy -> smoke graph.

Config-validation "test" for a workflow file (no runtime to exercise). Targets
the Phase 12.5 topology: backend -> Hugging Face Space, frontend -> Vercel, and
no Cloudflare artifacts remain.
"""

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).parents[5] / ".github" / "workflows" / "deploy.yml"


def _load():
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def test_deploy_workflow_exists():
    assert WORKFLOW_PATH.exists(), f"{WORKFLOW_PATH} does not exist"


def test_job_dependency_graph():
    jobs = _load()["jobs"]
    for name in ("test", "deploy-backend", "deploy-frontend", "smoke"):
        assert name in jobs, f"missing job: {name}"
    assert jobs["deploy-backend"]["needs"] == "test"
    assert jobs["deploy-frontend"]["needs"] == "test"
    smoke_needs = jobs["smoke"]["needs"]
    needs = smoke_needs if isinstance(smoke_needs, list) else [smoke_needs]
    assert set(needs) == {"deploy-backend", "deploy-frontend"}


def test_targets_hf_space_and_vercel_not_cloudflare():
    raw = WORKFLOW_PATH.read_text().lower()
    assert "huggingface_hub" in raw or "hf_space_id" in raw  # backend -> HF Space
    assert "vercel" in raw  # frontend -> Vercel
    assert "cloudflare" not in raw
    assert "wrangler" not in raw


def test_production_jobs_are_push_gated():
    jobs = _load()["jobs"]
    # Prod deploys must not run on pull_request events.
    for name in ("test", "deploy-backend", "deploy-frontend", "smoke"):
        assert "github.event_name == 'push'" in str(jobs[name].get("if", ""))
