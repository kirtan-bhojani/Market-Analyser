import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.core.config import get_settings
from app.ingest.candle import Candle

logger = logging.getLogger(__name__)

_REQUIRED_KLINE_FIELDS = ("t", "i", "o", "h", "l", "c", "v", "x")


def _binance_symbol_to_pair(raw_symbol: str) -> str:
    # Binance sends "BTCUSDT" with no separator; split on the configured quote
    # asset (universe.py selects symbols by the same setting) so the parser
    # stays consistent if the universe's quote asset ever changes.
    quote = get_settings().UNIVERSE_QUOTE_ASSET
    if raw_symbol.endswith(quote):
        return f"{raw_symbol[: -len(quote)]}/{quote}"
    return raw_symbol


def parse_binance_kline(msg: object) -> Candle | None:
    """Parse a raw Binance combined-stream kline message into a Candle.

    Returns None and logs a warning for any malformed or non-final
    (unclosed) kline instead of raising, per Phase 2 spec.
    """
    if not isinstance(msg, dict):
        # Live WS streams also carry pings, error frames, and garbled
        # (non-object) frames; reject them without raising.
        logger.warning("malformed kline: message is not a dict: %r", msg)
        return None

    if msg.get("e") != "kline":
        return None

    k = msg.get("k")
    if not isinstance(k, dict):
        logger.warning("malformed kline: missing 'k' object: %r", msg)
        return None

    if not k.get("x", False):
        # Kline not yet closed; ingestion only persists closed bars.
        return None

    missing = [f for f in _REQUIRED_KLINE_FIELDS if f not in k]
    if missing:
        logger.warning("malformed kline: missing fields %s: %r", missing, msg)
        return None

    try:
        return Candle(
            symbol=_binance_symbol_to_pair(k["s"]),
            tf=k["i"],
            ts=datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),  # noqa: UP017
            o=Decimal(k["o"]),
            h=Decimal(k["h"]),
            l=Decimal(k["l"]),
            c=Decimal(k["c"]),
            v=Decimal(k["v"]),
        )
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        logger.warning("malformed kline: %s: %r", exc, msg)
        return None
