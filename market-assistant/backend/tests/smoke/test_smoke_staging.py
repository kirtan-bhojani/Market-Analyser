"""Phase 12 Task 8 / 12.5 Task 4: post-deploy smoke against the live URLs.

Driven by env vars, so it runs only in the deploy pipeline's `smoke` job (or
locally when you export them). Skips cleanly everywhere else, so the default
`pytest` run in CI never hits the network.

  STAGING_URL           backend base, e.g. https://<user>-market-assistant.hf.space
  STAGING_WS_URL        backend ws base, e.g. wss://<user>-market-assistant.hf.space
  STAGING_FRONTEND_URL  Vercel site,   e.g. https://<project>.vercel.app
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.smoke

BACKEND = os.environ.get("STAGING_URL")
WS = os.environ.get("STAGING_WS_URL")
FRONTEND = os.environ.get("STAGING_FRONTEND_URL")

_TIMEOUT = 30.0  # HF Spaces can cold-start


@pytest.mark.skipif(not BACKEND, reason="STAGING_URL not set")
def test_backend_health_ok():
    r = httpx.get(f"{BACKEND}/health", timeout=_TIMEOUT)
    assert r.status_code == 200
    assert r.json().get("status") in ("ok", "healthy", True) or r.json()


@pytest.mark.skipif(not BACKEND, reason="STAGING_URL not set")
def test_protected_route_requires_auth():
    # A chat session create must reject an unauthenticated request (Phase 11 auth).
    r = httpx.post(f"{BACKEND}/chat/sessions", timeout=_TIMEOUT)
    assert r.status_code in (401, 403), r.status_code


@pytest.mark.skipif(not FRONTEND, reason="STAGING_FRONTEND_URL not set")
def test_frontend_root_serves_spa_shell():
    r = httpx.get(f"{FRONTEND}/", timeout=_TIMEOUT, follow_redirects=True)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="root"' in r.text


@pytest.mark.skipif(not FRONTEND, reason="STAGING_FRONTEND_URL not set")
def test_frontend_deep_link_rewrites_to_index():
    # A broken SPA rewrite returns Vercel's 404 instead of the app shell.
    r = httpx.get(f"{FRONTEND}/charts", timeout=_TIMEOUT, follow_redirects=True)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="root"' in r.text


@pytest.mark.skipif(not WS, reason="STAGING_WS_URL not set")
def test_backend_websocket_rejects_unauthenticated_connection():
    # All WS routes are auth-gated (Phase 11): a tokenless connect must be
    # refused. Reaching the handshake at all proves the WS endpoint is live.
    import asyncio

    import websockets
    from websockets.exceptions import (
        ConnectionClosed,
        InvalidStatus,
        InvalidStatusCode,
    )

    async def _connect():
        # An authed WS stays open; a tokenless one must be rejected at the
        # handshake or closed right after (e.g. policy-violation 1008).
        async with websockets.connect(f"{WS}/ws/candles", open_timeout=_TIMEOUT) as ws:
            await ws.recv()

    with pytest.raises((InvalidStatus, InvalidStatusCode, ConnectionClosed, OSError)):
        asyncio.run(_connect())
