import pytest

from app.chat.providers.anthropic_provider import AnthropicProvider
from app.chat.providers.factory import get_provider
from app.chat.providers.groq_provider import GroqProvider
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_factory_returns_groq_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    get_settings.cache_clear()
    assert isinstance(get_provider(), GroqProvider)


def test_factory_returns_anthropic_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
    assert isinstance(get_provider(), AnthropicProvider)


def test_factory_raises_on_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "does_not_exist")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_provider()
