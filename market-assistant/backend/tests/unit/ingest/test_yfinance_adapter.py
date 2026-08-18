from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.ingest.candle import Candle
from app.ingest.yfinance_adapter import fetch_candles, normalize_symbol, to_yf_interval
from tests.fixtures.yfinance_fixtures import EMPTY_HOLIDAY_HISTORY, TRADING_DAY_HISTORY, FakeTicker

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("RELIANCE", "RELIANCE.NS"),
        ("TCS", "TCS.NS"),
        ("RELIANCE.NS", "RELIANCE.NS"),
        ("^NSEI", "^NSEI"),  # index symbols pass through unchanged
    ],
)
def test_normalize_symbol(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize(
    "tf,expected",
    [("1m", "1m"), ("5m", "5m"), ("15m", "15m"), ("1h", "60m"), ("1d", "1d")],
)
def test_to_yf_interval(tf, expected):
    assert to_yf_interval(tf) == expected


def test_to_yf_interval_rejects_unknown_tf():
    with pytest.raises(ValueError, match="unsupported timeframe"):
        to_yf_interval("3m")


def test_fetch_candles_on_trading_day_returns_normalized_candles():
    start = datetime(2025, 6, 9, 9, 15, tzinfo=IST)
    end = datetime(2025, 6, 9, 9, 45, tzinfo=IST)
    candles = fetch_candles(
        "RELIANCE", "1m", start, end, client=FakeTicker(TRADING_DAY_HISTORY)
    )
    assert len(candles) == 2
    assert all(isinstance(c, Candle) for c in candles)
    assert candles[0].symbol == "RELIANCE.NS"
    assert candles[0].tf == "1m"
    assert candles[0].o == pytest.approx(2900.0)
    assert candles[0].v == pytest.approx(120000)


def test_fetch_candles_on_holiday_returns_no_fabricated_candles():
    start = datetime(2025, 1, 26, 9, 15, tzinfo=IST)  # Republic Day
    end = datetime(2025, 1, 26, 15, 30, tzinfo=IST)
    candles = fetch_candles(
        "RELIANCE", "1m", start, end, client=FakeTicker(EMPTY_HOLIDAY_HISTORY)
    )
    assert candles == []
