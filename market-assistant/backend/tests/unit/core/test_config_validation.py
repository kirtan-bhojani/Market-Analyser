"""Phase 12 Task 1: fail-fast config validation.

Reconciled with Phase 11's env-aware design: defaults are retained (local/CI
rely on them) but an env-aware prod guard makes a misconfigured *prod* deploy
fail at construction time instead of degrading silently on localhost defaults.
The whole suite runs under ENV=test (tests/conftest), so the guard is inert here
except in the tests below that explicitly set ENV=prod.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# A fully-populated prod environment: every critical secret set to a non-default.
VALID_PROD = {
    "env": "prod",
    "database_url": "postgresql+asyncpg://u:p@db.example.com:5432/market",
    "redis_url": "rediss://default:token@host.upstash.io:6379/0",
    "jwt_secret": "a-real-32-char-minimum-secret-value!!",
    "jwt_issuer": "https://ref.supabase.co/auth/v1",
    "LLM_PROVIDER": "groq",
    "GROQ_API_KEY": "gsk_realkey",
    "telegram_bot_token": "123:abc",
    "cors_allowed_origins": "https://app.example.com",
}


def test_survival_knobs_exist_with_documented_defaults():
    s = Settings(env="test")
    assert s.max_universe_size == 25
    assert s.candle_retention_days == 60
    assert s.llm_daily_quota == 500


def test_prod_raises_when_database_url_is_localhost_default():
    env = VALID_PROD.copy()
    env["database_url"] = "postgresql+asyncpg://market:market@localhost:5434/market_assistant"
    with pytest.raises(ValidationError) as exc:
        Settings(**env)
    assert "database_url" in str(exc.value).lower()


def test_prod_raises_when_jwt_secret_empty_and_no_jwks():
    env = VALID_PROD.copy()
    env["jwt_secret"] = ""
    # Pin the JWKS sources empty so an ambient .env SUPABASE_URL can't derive a
    # JWKS and satisfy the auth requirement — this test is about neither existing.
    env["supabase_url"] = ""
    env["supabase_jwks_url"] = ""
    with pytest.raises(ValidationError) as exc:
        Settings(**env)
    assert "jwt" in str(exc.value).lower()


def test_prod_raises_when_no_llm_key_for_provider():
    env = VALID_PROD.copy()
    del env["GROQ_API_KEY"]
    with pytest.raises(ValidationError) as exc:
        Settings(**env)
    assert "llm" in str(exc.value).lower() or "key" in str(exc.value).lower()


def test_prod_raises_when_jwt_issuer_empty():
    # 1.3: with jwt_issuer unset the JWT `iss` claim is never checked, so a token
    # from any issuer that shares the key/JWKS is accepted. Prod must require it.
    env = VALID_PROD.copy()
    env["jwt_issuer"] = ""
    with pytest.raises(ValidationError) as exc:
        Settings(**env)
    assert "jwt_issuer" in str(exc.value).lower() or "iss" in str(exc.value).lower()


def test_prod_succeeds_without_telegram_token():
    # Alert delivery is optional: a missing telegram_bot_token must NOT block a
    # prod boot. The alert worker degrades (no Telegram push); the app runs.
    env = VALID_PROD.copy()
    env["telegram_bot_token"] = ""
    s = Settings(**env)
    assert s.env == "prod"
    assert s.telegram_bot_token == ""


def test_prod_succeeds_with_full_valid_environment():
    s = Settings(**VALID_PROD)
    assert s.env == "prod"
    assert s.max_universe_size == 25


def test_jwks_url_satisfies_jwt_requirement_in_prod():
    env = VALID_PROD.copy()
    env["jwt_secret"] = ""
    env["supabase_jwks_url"] = "https://ref.supabase.co/auth/v1/keys"
    s = Settings(**env)  # JWKS is an acceptable alternative to a shared secret
    assert s.supabase_jwks_url


def test_dev_and_test_env_keep_permissive_defaults():
    # The guard is inert outside prod: local/CI construct Settings with defaults.
    for e in ("dev", "test"):
        s = Settings(env=e)
        assert s.database_url  # localhost default is fine here
