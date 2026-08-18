import pandas as pd

TRADING_DAY_HISTORY = pd.DataFrame(
    {
        "Open": [2900.0, 2905.0],
        "High": [2910.0, 2912.0],
        "Low": [2895.0, 2900.0],
        "Close": [2905.0, 2908.0],
        "Volume": [120000, 98000],
    },
    index=pd.to_datetime(
        ["2025-06-09 09:15:00+05:30", "2025-06-09 09:30:00+05:30"]
    ),
)

EMPTY_HOLIDAY_HISTORY = pd.DataFrame(
    columns=["Open", "High", "Low", "Close", "Volume"]
)


class FakeTicker:
    def __init__(self, history_df: pd.DataFrame):
        self._history_df = history_df

    def history(self, interval: str, start, end):
        return self._history_df
