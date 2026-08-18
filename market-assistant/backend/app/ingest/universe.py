from typing import Any, Protocol


class SupportsFetchTickers(Protocol):
    async def fetch_tickers(self) -> dict[str, dict[str, Any]]: ...


async def get_top_n_by_volume(
    exchange: SupportsFetchTickers, n: int, quote_asset: str
) -> list[str]:
    """Return up to n symbols quoted in quote_asset, sorted by 24h quoteVolume desc."""
    tickers = await exchange.fetch_tickers()
    candidates = [
        (symbol, data.get("quoteVolume") or 0)
        for symbol, data in tickers.items()
        if symbol.endswith(f"/{quote_asset}")
    ]
    candidates.sort(key=lambda pair: pair[1], reverse=True)
    return [symbol for symbol, _ in candidates[:n]]
