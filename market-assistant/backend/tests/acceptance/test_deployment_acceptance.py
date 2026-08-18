"""Phase 12 Task 9: deployment acceptance — the phase-exit gate.

Asserts both live public URLs are reachable and the core smoke assertions hold
end-to-end. Runs post-deploy (needs STAGING_URL + STAGING_FRONTEND_URL); skips
otherwise so it never breaks the default CI run.
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.acceptance

BACKEND = os.environ.get("STAGING_URL")
FRONTEND = os.environ.get("STAGING_FRONTEND_URL")
_TIMEOUT = 30.0


@pytest.mark.skipif(
    not (BACKEND and FRONTEND),
    reason="STAGING_URL and STAGING_FRONTEND_URL required for deployment acceptance",
)
def test_backend_and_frontend_are_live():
    backend = httpx.get(f"{BACKEND}/health", timeout=_TIMEOUT)
    assert backend.status_code == 200, f"backend /health -> {backend.status_code}"

    frontend = httpx.get(f"{FRONTEND}/", timeout=_TIMEOUT, follow_redirects=True)
    assert frontend.status_code == 200, f"frontend / -> {frontend.status_code}"
    assert "text/html" in frontend.headers.get("content-type", "")
    assert 'id="root"' in frontend.text


@pytest.mark.skipif(
    not FRONTEND, reason="STAGING_FRONTEND_URL required"
)
def test_spa_deep_link_resolves():
    r = httpx.get(f"{FRONTEND}/scanner", timeout=_TIMEOUT, follow_redirects=True)
    assert r.status_code == 200 and 'id="root"' in r.text
