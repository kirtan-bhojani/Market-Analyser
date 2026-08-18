from typing import Literal, TypedDict

import pandas as pd

Bucket = Literal["dow", "month", "hour"]

_DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTH_LABELS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
_HOUR_LABELS = [f"{h:02d}" for h in range(24)]


class Seasonality(TypedDict):
    bucket: str
    labels: list[str]
    avg_return: list[float]
    count: list[int]


def compute_seasonality(
    candles: pd.DataFrame, bucket: Bucket, tz: str = "UTC"
) -> Seasonality:
    if bucket == "dow":
        labels = _DOW_LABELS
    elif bucket == "month":
        labels = _MONTH_LABELS
    elif bucket == "hour":
        labels = _HOUR_LABELS
    else:
        raise ValueError(f"unknown bucket {bucket!r}")

    df = candles.sort_values("ts").copy()
    ret = df["c"].pct_change()
    ts = pd.DatetimeIndex(df["ts"])

    if bucket == "dow":
        keys = ts.weekday
    elif bucket == "month":
        keys = ts.month - 1
    else:
        # Hour-of-day is only meaningful in the exchange-local timezone: a UTC
        # hour bucket smears an NSE session across the wrong hours. Localize
        # naive timestamps to UTC first, then convert to the exchange tz.
        local = ts if ts.tz is not None else ts.tz_localize("UTC")
        keys = local.tz_convert(tz).hour

    frame = pd.DataFrame({"key": keys, "ret": ret.to_numpy()}).dropna(subset=["ret"])
    grouped_mean = frame.groupby("key")["ret"].mean()
    grouped_count = frame.groupby("key")["ret"].count()

    n = len(labels)
    avg_return = [
        round(float(grouped_mean[i]), 8) if i in grouped_mean.index else 0.0
        for i in range(n)
    ]
    count = [
        int(grouped_count[i]) if i in grouped_count.index else 0 for i in range(n)
    ]

    return {
        "bucket": bucket,
        "labels": labels,
        "avg_return": avg_return,
        "count": count,
    }
