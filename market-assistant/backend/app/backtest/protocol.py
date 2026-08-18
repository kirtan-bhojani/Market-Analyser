from typing import Any, Protocol

import pandas as pd


class Strategy(Protocol):
    def generate_signals(self, candles: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        """Return a DataFrame indexed like `candles` with boolean
        columns 'entries' and 'exits'. Must never set both True on the
        same row."""
        ...
