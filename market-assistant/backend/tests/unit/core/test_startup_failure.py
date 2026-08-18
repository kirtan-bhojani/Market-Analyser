"""Phase 12 Task 1: the app factory fails fast at construction, not on first request.

Under ENV=prod with an incomplete environment, create_app() must raise a
pydantic ValidationError during construction (before returning the ASGI app),
so a misconfigured deploy crashes at startup with a readable, field-named error
instead of binding a port and serving 500s.
"""

import pytest
from pydantic import ValidationError


def test_create_app_raises_before_returning_asgi_app_when_prod_env_incomplete(monkeypatch):
    # Force a prod environment missing every critical secret.
    monkeypatch.setenv("ENV", "prod")
    for k in ("JWT_SECRET", "GROQ_API_KEY", "GEMINI_API_KEY",
              "ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    # Leave DATABASE_URL at its localhost default (also disallowed in prod).
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import app.core.config as config_module

    config_module.get_settings.cache_clear()
    from app.main import create_app

    with pytest.raises(ValidationError):
        create_app()

    config_module.get_settings.cache_clear()
