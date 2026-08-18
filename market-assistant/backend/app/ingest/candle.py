from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    tf: str
    ts: datetime
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal
