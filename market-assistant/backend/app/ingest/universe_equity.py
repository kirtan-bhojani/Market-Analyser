from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.yfinance_adapter import normalize_symbol
from app.models.instrument import Instrument

NIFTY50_SYMBOLS: list[str] = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
    "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK",
    "BAJFINANCE", "ASIANPAINT", "MARUTI", "HCLTECH", "SUNPHARMA",
    "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND", "M&M", "TATAMOTORS",
    "TATASTEEL", "POWERGRID", "NTPC", "TECHM", "ADANIENT", "JSWSTEEL",
    "HDFCLIFE", "SBILIFE", "BAJAJFINSV", "GRASIM", "INDUSINDBK",
    "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
    "HEROMOTOCO", "BRITANNIA", "APOLLOHOSP", "BPCL", "ADANIPORTS",
    "ONGC", "TATACONSUM", "UPL", "BAJAJ-AUTO", "HINDALCO", "LTIM",
]


async def ensure_equity_instruments(session: AsyncSession) -> list[Instrument]:
    result = await session.execute(
        select(Instrument).where(Instrument.asset_class == "equity")
    )
    existing = {i.symbol: i for i in result.scalars().all()}

    # Free-tier survival: assert the equity universe stays within the NIFTY-50 cap.
    from app.core.config import get_settings
    from app.core.universe import enforce_universe_cap

    normalized = [normalize_symbol(s) for s in NIFTY50_SYMBOLS]
    enforce_universe_cap(normalized, "equity", get_settings())

    instruments: list[Instrument] = []
    for raw_symbol in NIFTY50_SYMBOLS:
        symbol = normalize_symbol(raw_symbol)
        if symbol in existing:
            instruments.append(existing[symbol])
            continue
        instrument = Instrument(
            symbol=symbol, asset_class="equity", exchange="NSE", active=True
        )
        session.add(instrument)
        instruments.append(instrument)

    await session.flush()
    return instruments
