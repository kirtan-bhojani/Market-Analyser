"""Phase 11: real Supabase JWT auth wired into the routes.

Real Bearer tokens are verified in EVERY environment; the X-Dev-User stub
survives only in non-prod. Prod rejects anonymous, stub-only, and bad-token
requests with 401.
"""

import time
import uuid

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import get_settings

SECRET = "test-jwt-secret-for-auth-tests-0123456789"

VALID_RULE = {
    "name": "RSI dip + volume spike",
    "definition": {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    },
}


def mint_token(
    sub: str,
    *,
    secret: str = SECRET,
    aud: str = "authenticated",
    exp_offset: int = 3600,
) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "aud": aud, "exp": now + exp_offset, "iat": now},
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def jwt_settings(monkeypatch):
    """Point the cached settings singleton at an HS256 test secret."""
    s = get_settings()
    monkeypatch.setattr(s, "jwt_secret", SECRET)
    monkeypatch.setattr(s, "jwt_audience", "authenticated")
    monkeypatch.setattr(s, "jwt_issuer", "")
    monkeypatch.setattr(s, "supabase_jwks_url", "")
    return s


@pytest.fixture
def prod_settings(monkeypatch, jwt_settings):
    monkeypatch.setattr(jwt_settings, "env", "prod")
    return jwt_settings


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_dev_stub_still_works_in_test_env(
    client: AsyncClient, auth_headers: dict, other_user_headers: dict
):
    # env is non-prod by default in the suite: X-Dev-User keeps working and
    # rules stay scoped to that user.
    resp = await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    assert resp.status_code == 201
    mine = await client.get("/api/scanner/rules", headers=auth_headers)
    assert len(mine.json()) == 1
    theirs = await client.get("/api/scanner/rules", headers=other_user_headers)
    assert theirs.json() == []


@pytest.mark.asyncio
async def test_real_bearer_works_in_test_env_with_cross_user_isolation(
    client: AsyncClient, jwt_settings
):
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())

    created = await client.post(
        "/api/scanner/rules", json=VALID_RULE, headers=bearer(mint_token(user_a))
    )
    assert created.status_code == 201

    mine = await client.get("/api/scanner/rules", headers=bearer(mint_token(user_a)))
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    theirs = await client.get("/api/scanner/rules", headers=bearer(mint_token(user_b)))
    assert theirs.status_code == 200
    assert theirs.json() == []


@pytest.mark.asyncio
async def test_prod_anonymous_rejected(client: AsyncClient, prod_settings):
    resp = await client.get("/api/scanner/rules")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_prod_ignores_dev_stub_header(client: AsyncClient, prod_settings):
    resp = await client.get(
        "/api/scanner/rules", headers={"X-Dev-User": str(uuid.uuid4())}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_prod_rejects_expired_and_tampered_bearer(client: AsyncClient, prod_settings):
    sub = str(uuid.uuid4())

    expired = mint_token(sub, exp_offset=-3600)
    resp = await client.get("/api/scanner/rules", headers=bearer(expired))
    assert resp.status_code == 401

    tampered = mint_token(sub, secret="wrong-secret-wrong-secret-wrong-secret!!")
    resp = await client.get("/api/scanner/rules", headers=bearer(tampered))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_prod_valid_bearer_accepted(client: AsyncClient, prod_settings):
    resp = await client.get(
        "/api/scanner/rules", headers=bearer(mint_token(str(uuid.uuid4())))
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_raw_uuid_bearer_accepted_in_non_prod(client: AsyncClient):
    """Non-prod HTTP auth mirrors the WS path: a raw-UUID Bearer (the e2e
    seeded session token) is accepted and scoped to that user. Prod never is
    (see test_prod_rejects_raw_uuid_bearer)."""
    uid_a = str(uuid.uuid4())
    uid_b = str(uuid.uuid4())
    created = await client.post("/api/scanner/rules", json=VALID_RULE, headers=bearer(uid_a))
    assert created.status_code == 201
    mine = await client.get("/api/scanner/rules", headers=bearer(uid_a))
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    theirs = await client.get("/api/scanner/rules", headers=bearer(uid_b))
    assert theirs.status_code == 200
    assert theirs.json() == []


@pytest.mark.asyncio
async def test_non_uuid_bearer_rejected_in_non_prod(client: AsyncClient):
    resp = await client.get("/api/scanner/rules", headers=bearer("not-a-jwt-not-a-uuid"))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_prod_rejects_raw_uuid_bearer(client: AsyncClient, prod_settings):
    resp = await client.get("/api/scanner/rules", headers=bearer(str(uuid.uuid4())))
    assert resp.status_code == 401
