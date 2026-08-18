"""Supabase JWT verification.

Pure verification logic + schema mapping. No FastAPI request/dependency
wiring lives here (Task 3 builds the dependency on top of this).

Two verification paths, selected by config:
  * ``jwks_url`` set  -> RS256/ES256 via JWKS (modern Supabase / OIDC).
  * ``secret`` set    -> HS256 shared secret (Supabase legacy / local dev / tests).

Signature and ``exp`` are always verified; ``sub`` and ``exp`` are required.
Any verification failure surfaces as ``HTTPException(401)``; a missing
verifier (no secret and no JWKS URL) is a server misconfiguration (500).
"""

from __future__ import annotations

import jwt
from fastapi import HTTPException
from jwt.types import Options

from app.core.config import Settings
from app.schemas.auth import AuthenticatedUser, TokenPayload

# Cache one PyJWKClient per JWKS URL so keys are fetched/cached by the client
# rather than refetched on every verification call.
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url)
        _jwks_clients[jwks_url] = client
    return client


def decode_and_verify_jwt(
    token: str,
    *,
    secret: str = "",
    audience: str = "authenticated",
    issuer: str = "",
    jwks_url: str = "",
) -> TokenPayload:
    """Decode and verify a Supabase-issued JWT, returning its claims.

    Raises ``HTTPException(401)`` on any verification failure and
    ``HTTPException(500)`` when no verifier is configured.
    """
    options: Options = {"require": ["exp", "sub"], "verify_aud": bool(audience)}

    if jwks_url:
        algorithms = ["RS256", "ES256"]
        try:
            key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc
    elif secret:
        algorithms = ["HS256"]
        key = secret
    else:
        raise HTTPException(status_code=500, detail="Auth not configured")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=audience if audience else None,
            issuer=issuer if issuer else None,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    return TokenPayload(**claims)


def verify_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Verify a token using application settings and map it to a user."""
    payload = decode_and_verify_jwt(
        token,
        secret=settings.jwt_secret,
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        jwks_url=settings.effective_jwks_url,
    )
    return AuthenticatedUser(id=payload.sub, email=payload.email)
