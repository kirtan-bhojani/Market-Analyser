from __future__ import annotations

import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core import security
from app.core.security import decode_and_verify_jwt, verify_token

SECRET = "unit-test-shared-secret-at-least-32b!"
AUD = "authenticated"
ISS = "https://ref.supabase.co/auth/v1"


def _hs256(claims: dict, secret: str = SECRET) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def _base_claims(**overrides: object) -> dict:
    now = int(time.time())
    claims: dict = {
        "sub": str(uuid4()),
        "email": "trader@example.com",
        "aud": AUD,
        "iss": ISS,
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
    }
    claims.update(overrides)
    return claims


# --- HS256 branch ---------------------------------------------------------


def test_valid_hs256_token_decodes() -> None:
    uid = str(uuid4())
    token = _hs256(_base_claims(sub=uid))
    payload = decode_and_verify_jwt(token, secret=SECRET, audience=AUD)
    assert str(payload.sub) == uid
    assert payload.email == "trader@example.com"


def test_expired_token_401() -> None:
    now = int(time.time())
    token = _hs256(_base_claims(iat=now - 7200, exp=now - 3600))
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret=SECRET, audience=AUD)
    assert exc.value.status_code == 401


def test_tampered_wrong_secret_401() -> None:
    token = _hs256(_base_claims(), secret="a-different-secret-at-least-32-bytes!")
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret=SECRET, audience=AUD)
    assert exc.value.status_code == 401


def test_wrong_audience_401() -> None:
    token = _hs256(_base_claims(aud="other"))
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret=SECRET, audience=AUD)
    assert exc.value.status_code == 401


def test_wrong_issuer_401() -> None:
    token = _hs256(_base_claims(iss="https://evil.example.com"))
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret=SECRET, audience=AUD, issuer=ISS)
    assert exc.value.status_code == 401


def test_issuer_ignored_when_empty() -> None:
    token = _hs256(_base_claims(iss="https://anything.example.com"))
    payload = decode_and_verify_jwt(token, secret=SECRET, audience=AUD, issuer="")
    assert payload.iss == "https://anything.example.com"


def test_correct_issuer_passes() -> None:
    token = _hs256(_base_claims())
    payload = decode_and_verify_jwt(token, secret=SECRET, audience=AUD, issuer=ISS)
    assert payload.iss == ISS


def test_missing_sub_401() -> None:
    claims = _base_claims()
    del claims["sub"]
    token = _hs256(claims)
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret=SECRET, audience=AUD)
    assert exc.value.status_code == 401


def test_missing_exp_401() -> None:
    claims = _base_claims()
    del claims["exp"]
    token = _hs256(claims)
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret=SECRET, audience=AUD)
    assert exc.value.status_code == 401


def test_audience_empty_disables_aud_check() -> None:
    token = _hs256(_base_claims(aud="whatever"))
    payload = decode_and_verify_jwt(token, secret=SECRET, audience="")
    assert payload.email == "trader@example.com"


def test_not_configured_raises_500() -> None:
    token = _hs256(_base_claims())
    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(token, secret="", audience=AUD, jwks_url="")
    assert exc.value.status_code == 500


# --- RS256 / JWKS branch --------------------------------------------------


class _FakeSigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


def test_rs256_via_jwks_decodes(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    uid = str(uuid4())
    token = jwt.encode(_base_claims(sub=uid), private_key, algorithm="RS256")

    def fake_get_signing_key(self: object, tok: str) -> _FakeSigningKey:
        return _FakeSigningKey(public_key)

    monkeypatch.setattr(
        jwt.PyJWKClient, "get_signing_key_from_jwt", fake_get_signing_key
    )
    # avoid cross-test cache reuse of clients
    security._jwks_clients.clear()

    payload = decode_and_verify_jwt(
        token,
        audience=AUD,
        jwks_url="https://ref.supabase.co/auth/v1/.well-known/jwks.json",
    )
    assert str(payload.sub) == uid


def test_rs256_tampered_401(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_public = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    ).public_key()
    token = jwt.encode(_base_claims(), private_key, algorithm="RS256")

    def fake_get_signing_key(self: object, tok: str) -> _FakeSigningKey:
        return _FakeSigningKey(other_public)

    monkeypatch.setattr(
        jwt.PyJWKClient, "get_signing_key_from_jwt", fake_get_signing_key
    )
    security._jwks_clients.clear()

    with pytest.raises(HTTPException) as exc:
        decode_and_verify_jwt(
            token,
            audience=AUD,
            jwks_url="https://ref.supabase.co/auth/v1/.well-known/jwks.json",
        )
    assert exc.value.status_code == 401


def test_jwks_client_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    security._jwks_clients.clear()
    created: list[str] = []
    real_init = jwt.PyJWKClient.__init__

    def counting_init(self: jwt.PyJWKClient, uri: str, *a: object, **k: object) -> None:
        created.append(uri)
        real_init(self, uri, *a, **k)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    token = jwt.encode(_base_claims(), private_key, algorithm="RS256")

    monkeypatch.setattr(jwt.PyJWKClient, "__init__", counting_init)
    monkeypatch.setattr(
        jwt.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, tok: _FakeSigningKey(public_key),
    )

    url = "https://ref.supabase.co/auth/v1/.well-known/jwks.json"
    decode_and_verify_jwt(token, audience=AUD, jwks_url=url)
    decode_and_verify_jwt(token, audience=AUD, jwks_url=url)
    assert created.count(url) == 1


# --- verify_token convenience --------------------------------------------


def test_verify_token_returns_authenticated_user() -> None:
    from app.core.config import Settings

    uid = str(uuid4())
    token = _hs256(_base_claims(sub=uid))
    settings = Settings(jwt_secret=SECRET, jwt_audience=AUD)
    user = verify_token(token, settings)
    assert str(user.id) == uid
    assert user.email == "trader@example.com"


# --- effective_jwks_url derivation + precedence ---------------------------


def test_effective_jwks_url_derived_from_supabase_url() -> None:
    from app.core.config import Settings

    settings = Settings(supabase_url="https://ref.supabase.co")
    assert (
        settings.effective_jwks_url
        == "https://ref.supabase.co/auth/v1/.well-known/jwks.json"
    )


def test_effective_jwks_url_explicit_overrides_derived() -> None:
    from app.core.config import Settings

    settings = Settings(
        supabase_url="https://ref.supabase.co",
        supabase_jwks_url="https://explicit.example.com/jwks.json",
    )
    assert settings.effective_jwks_url == "https://explicit.example.com/jwks.json"


def test_effective_jwks_url_empty_when_neither_set() -> None:
    from app.core.config import Settings

    assert Settings(jwt_secret=SECRET).effective_jwks_url == ""


def test_verify_token_prefers_jwks_over_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When supabase_url is set (ES256 world), JWKS wins even if jwt_secret is
    also present — a stale HS256 secret must never shadow asymmetric verification.
    """
    from cryptography.hazmat.primitives.asymmetric import ec

    from app.core.config import Settings

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    uid = str(uuid4())
    token = jwt.encode(_base_claims(sub=uid), private_key, algorithm="ES256")

    monkeypatch.setattr(
        jwt.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, tok: _FakeSigningKey(public_key),
    )
    security._jwks_clients.clear()

    # Both a (stale) HS256 secret and a supabase_url are configured.
    settings = Settings(
        jwt_secret=SECRET, jwt_audience=AUD, supabase_url="https://ref.supabase.co"
    )
    user = verify_token(token, settings)
    assert str(user.id) == uid
