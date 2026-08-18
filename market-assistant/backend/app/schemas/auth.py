from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: UUID
    email: str | None = None
    exp: int
    iat: int | None = None
    aud: str | list[str] | None = None
    iss: str | None = None
    role: str | None = None


class AuthenticatedUser(BaseModel):
    id: UUID
    email: str | None = None
