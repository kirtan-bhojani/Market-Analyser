from datetime import datetime
from decimal import Decimal
from typing import Any

from app.ingest.candle import Candle
from app.ingest.nse_calendar import is_trading_day

_TF_TO_YF_INTERVAL = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "60m",
    "1d": "1d",
}


def normalize_symbol(symbol: str) -> str:
    if symbol.startswith("^") or "." in symbol:
        return symbol
    return f"{symbol}.NS"


def to_yf_interval(tf: str) -> str:
    try:
        return _TF_TO_YF_INTERVAL[tf]
    except KeyError:
        raise ValueError(f"unsupported timeframe: {tf!r}") from None


def fetch_candles(
    symbol: str,
    tf: str,
    start: datetime,
    end: datetime,
    client: Any = None,
) -> list[Candle]:
    """Fetch OHLCV candles for `symbol` between start/end. Never fabricates
    bars: a holiday or a session with no trades yields an empty list."""
    if not is_trading_day(start.date()):
        return []

    yf_symbol = normalize_symbol(symbol)
    interval = to_yf_interval(tf)

    if client is None:
        import yfinance as yf

        client = yf.Ticker(yf_symbol)

    history_df = client.history(interval=interval, start=start, end=end)
    if history_df is None or history_df.empty:
        return []

    candles: list[Candle] = []
    for ts, row in history_df.iterrows():
        candles.append(
            Candle(
                symbol=yf_symbol,
                tf=tf,
                ts=ts.to_pydatetime(),
                o=Decimal(str(row["Open"])),
                h=Decimal(str(row["High"])),
                l=Decimal(str(row["Low"])),
                c=Decimal(str(row["Close"])),
                v=Decimal(str(row["Volume"])),
            )
        )
    return candles
