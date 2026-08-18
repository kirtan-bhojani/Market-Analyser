"""Phase 12 Task 3: free-tier universe cap enforcement.

Two guards keep the live system inside its free quotas:
  * crypto  — at most ``settings.max_universe_size`` symbols;
  * equity  — restricted to the NIFTY-50 allowlist (normalized ".NS" form).

Called by the ingestion bootstrap before subscribing to any WS/poll target.
"""

from typing import Literal

from app.core.config import Settings
from app.ingest.universe_equity import NIFTY50_SYMBOLS
from app.ingest.yfinance_adapter import normalize_symbol

AssetClass = Literal["crypto", "equity"]

# Normalized allowlist (bare "RELIANCE" -> "RELIANCE.NS"), computed once.
_NIFTY50_ALLOWED: frozenset[str] = frozenset(normalize_symbol(s) for s in NIFTY50_SYMBOLS)


class UniverseCapExceeded(Exception):
    """Raised when a requested universe exceeds its free-tier cap."""


def enforce_universe_cap(
    requested_symbols: list[str],
    asset_class: AssetClass,
    settings: Settings,
) -> list[str]:
    if asset_class == "crypto":
        cap = settings.max_universe_size
        if len(requested_symbols) > cap:
            raise UniverseCapExceeded(
                f"requested {len(requested_symbols)} crypto symbols, cap is {cap}"
            )
        return requested_symbols

    if asset_class == "equity":
        disallowed = [s for s in requested_symbols if s not in _NIFTY50_ALLOWED]
        if disallowed:
            raise UniverseCapExceeded(
                f"equity universe is capped to NIFTY-50; rejected: {disallowed}"
            )
        return requested_symbols

    raise ValueError(f"unknown asset_class: {asset_class!r}")
