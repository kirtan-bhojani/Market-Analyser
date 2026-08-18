from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from app.analytics.seasonality import compute_seasonality


def _monday_up_series(days: int = 70) -> pd.DataFrame:
    # Daily closes: every Monday closes +5% vs the prior day, all other days flat.
    start = datetime(2024, 1, 1, tzinfo=UTC)  # 2024-01-01 is a Monday
    ts_list = []
    closes = []
    price = 100.0
    for i in range(days):
        ts = start + timedelta(days=i)
        if ts.weekday() == 0 and i > 0:  # Monday (not the very first bar)
            price = price * 1.05
        ts_list.append(ts)
        closes.append(price)
    return pd.DataFrame({"ts": ts_list, "c": closes})


def test_dow_monday_bucket_positive_others_flat():
    df = _monday_up_series()
    result = compute_seasonality(df, bucket="dow")
    assert result["bucket"] == "dow"
    assert result["labels"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert len(result["avg_return"]) == 7
    assert result["avg_return"][0] > 0  # Monday
    for i in range(1, 7):
        assert abs(result["avg_return"][i]) < 1e-9


def test_invalid_bucket_raises_value_error():
    df = _monday_up_series()
    with pytest.raises(ValueError):
        compute_seasonality(df, bucket="decade")  # type: ignore[arg-type]
