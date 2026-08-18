"""Phase 12 Task 3: free-tier universe cap.

Crypto is capped to settings.max_universe_size; equity is locked to the NIFTY-50
allowlist (normalized to yfinance ".NS" form). enforce_universe_cap runs before
ingestion subscribes to any WS/poll target.
"""

import pytest

from app.core.config import Settings
from app.core.universe import UniverseCapExceeded, enforce_universe_cap
from app.ingest.universe_equity import NIFTY50_SYMBOLS
from app.ingest.yfinance_adapter import normalize_symbol


def _settings(**overrides) -> Settings:
    return Settings(env="test", **overrides)


def test_exactly_max_crypto_symbols_passes_through_unchanged():
    s = _settings(max_universe_size=25)
    symbols = [f"SYM{i}/USDT" for i in range(25)]
    assert enforce_universe_cap(symbols, "crypto", s) == symbols


def test_over_cap_crypto_raises_universe_cap_exceeded():
    s = _settings(max_universe_size=25)
    symbols = [f"SYM{i}/USDT" for i in range(26)]
    with pytest.raises(UniverseCapExceeded):
        enforce_universe_cap(symbols, "crypto", s)


def test_custom_cap_is_respected():
    s = _settings(max_universe_size=10)
    with pytest.raises(UniverseCapExceeded):
        enforce_universe_cap([f"SYM{i}/USDT" for i in range(11)], "crypto", s)


def test_non_nifty50_equity_symbol_rejected():
    s = _settings()
    with pytest.raises(UniverseCapExceeded):
        enforce_universe_cap(["RANDOMCO.NS"], "equity", s)


def test_full_nifty50_equity_list_passes():
    s = _settings()
    symbols = [normalize_symbol(x) for x in NIFTY50_SYMBOLS]
    assert enforce_universe_cap(symbols, "equity", s) == symbols


def test_unknown_asset_class_raises_value_error():
    s = _settings()
    with pytest.raises(ValueError):
        enforce_universe_cap([], "forex", s)  # type: ignore[arg-type]
