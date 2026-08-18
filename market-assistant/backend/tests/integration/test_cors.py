"""CORS lockdown: only configured origins get Access-Control-Allow-Origin."""

ALLOWED_ORIGIN = "http://localhost:5173"
EVIL_ORIGIN = "https://evil.example.com"


async def test_preflight_allows_configured_origin(test_client):
    resp = await test_client.options(
        "/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


async def test_preflight_rejects_unlisted_origin(test_client):
    resp = await test_client.options(
        "/health",
        headers={
            "Origin": EVIL_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != EVIL_ORIGIN
    assert "access-control-allow-origin" not in resp.headers


async def test_simple_get_echoes_allowed_origin(test_client):
    resp = await test_client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
    assert resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
