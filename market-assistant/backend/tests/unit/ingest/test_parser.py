import logging
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.ingest.candle import Candle
from app.ingest.parser import parse_binance_kline
from tests.fixtures.binance_klines import (
    MISSING_FIELD_KLINE,
    NON_NUMERIC_KLINE,
    UNCLOSED_KLINE,
    VALID_CLOSED_KLINE,
    WRONG_EVENT_TYPE,
)


def test_parses_valid_closed_kline_to_candle():
    candle = parse_binance_kline(VALID_CLOSED_KLINE)
    assert candle == Candle(
        symbol="BTC/USDT",
        tf="1m",
        ts=datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),  # noqa: UP017
        o=Decimal("35000.10"),
        h=Decimal("35020.00"),
        l=Decimal("34990.00"),
        c=Decimal("35010.50"),
        v=Decimal("12.34500000"),
    )


def test_unclosed_kline_returns_none():
    assert parse_binance_kline(UNCLOSED_KLINE) is None


def test_wrong_event_type_returns_none():
    assert parse_binance_kline(WRONG_EVENT_TYPE) is None


def test_missing_field_rejected_and_logged_not_raised(caplog):
    with caplog.at_level(logging.WARNING):
        result = parse_binance_kline(MISSING_FIELD_KLINE)
    assert result is None
    assert "malformed kline" in caplog.text.lower()


def test_non_numeric_field_rejected_and_logged_not_raised(caplog):
    with caplog.at_level(logging.WARNING):
        result = parse_binance_kline(NON_NUMERIC_KLINE)
    assert result is None
    assert "malformed kline" in caplog.text.lower()


@pytest.mark.parametrize("bad_msg", [[], None, "not-a-dict"])
def test_non_dict_message_rejected_and_logged_not_raised(bad_msg, caplog):
    with caplog.at_level(logging.WARNING):
        result = parse_binance_kline(bad_msg)
    assert result is None
    assert "malformed kline" in caplog.text.lower()
