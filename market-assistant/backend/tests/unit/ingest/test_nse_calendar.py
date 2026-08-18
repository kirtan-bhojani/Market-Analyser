from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.ingest.nse_calendar import NSE_HOLIDAYS, is_in_session, is_trading_day, session_window

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    "day,expected",
    [
        (date(2025, 1, 26), False),   # Republic Day (NSE holiday)
        (date(2025, 8, 15), False),   # Independence Day (NSE holiday)
        (date(2025, 12, 25), False),  # Christmas (NSE holiday)
        (date(2025, 6, 7), False),    # Saturday
        (date(2025, 6, 8), False),    # Sunday
        (date(2025, 6, 9), True),     # ordinary Monday trading day
    ],
)
def test_is_trading_day(day: date, expected: bool) -> None:
    assert is_trading_day(day) is expected


def test_session_window_bounds() -> None:
    open_dt, close_dt = session_window(date(2025, 6, 9))
    assert open_dt == datetime(2025, 6, 9, 9, 15, tzinfo=IST)
    assert close_dt == datetime(2025, 6, 9, 15, 30, tzinfo=IST)


@pytest.mark.parametrize(
    "dt,expected",
    [
        (datetime(2025, 6, 9, 9, 14, tzinfo=IST), False),
        (datetime(2025, 6, 9, 9, 15, tzinfo=IST), True),
        (datetime(2025, 6, 9, 12, 0, tzinfo=IST), True),
        (datetime(2025, 6, 9, 15, 30, tzinfo=IST), True),
        (datetime(2025, 6, 9, 15, 31, tzinfo=IST), False),
        (datetime(2025, 1, 26, 11, 0, tzinfo=IST), False),  # holiday, mid-day
    ],
)
def test_is_in_session(dt: datetime, expected: bool) -> None:
    assert is_in_session(dt) is expected


def test_holiday_table_has_entry_for_current_year() -> None:
    """Guard against holiday-blindness: fail loudly if NSE_HOLIDAYS has no
    entries for the current calendar year, instead of silently mis-gating
    the equity session (e.g. treating every day as a trading day)."""
    current_year = date.today().year
    assert any(d.year == current_year for d in NSE_HOLIDAYS), (
        f"NSE_HOLIDAYS has no entries for {current_year}; the holiday table "
        "is stale and must be updated from the official NSE circular."
    )


def test_is_in_session_naive_datetime_assumed_utc() -> None:
    # A naive datetime must be treated as UTC, not system-local time.
    # 2025-06-09 04:00 UTC == 09:30 IST, inside the trading session.
    naive_utc = datetime(2025, 6, 9, 4, 0)
    assert is_in_session(naive_utc) is True

    aware_equivalent = datetime(2025, 6, 9, 4, 0, tzinfo=ZoneInfo("UTC"))
    assert is_in_session(naive_utc) is is_in_session(aware_equivalent)
