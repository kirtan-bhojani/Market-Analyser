from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)

# NSE trading holidays (add per calendar year as published by NSE).
NSE_HOLIDAYS: set[date] = {
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Eid-Ul-Fitr
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti / Dussehra
    date(2025, 10, 21),  # Diwali Laxmi Pujan
    date(2025, 10, 22),  # Diwali Balipratipada
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
    # -- 2026 --
    # Full weekday trading-holiday list reconciled from the official NSE 2026
    # holiday circular (cross-checked against Zerodha + ClearTax published
    # calendars, which agree exactly). Holidays that fall on weekends
    # (Mahashivratri 15-Feb, Eid-ul-Fitr 21-Mar, Independence Day 15-Aug,
    # Diwali Laxmi Pujan 08-Nov) are already non-trading via the weekend
    # guard and are intentionally NOT listed here.
    date(2026, 1, 15),   # Municipal Corporation Elections, Maharashtra (Thu)
    date(2026, 1, 26),   # Republic Day (Mon)
    date(2026, 3, 3),    # Holi (Tue)
    date(2026, 3, 26),   # Shri Ram Navami (Thu)
    date(2026, 3, 31),   # Shri Mahavir Jayanti (Tue)
    date(2026, 4, 3),    # Good Friday (Fri)
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti (Tue)
    date(2026, 5, 1),    # Maharashtra Day (Fri)
    date(2026, 5, 28),   # Bakri Eid (Thu)
    date(2026, 6, 26),   # Muharram (Fri)
    date(2026, 9, 14),   # Ganesh Chaturthi (Mon)
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti (Fri)
    date(2026, 10, 20),  # Dussehra (Tue)
    date(2026, 11, 10),  # Diwali Balipratipada (Tue)
    date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev (Tue)
    date(2026, 12, 25),  # Christmas (Fri)
}

# Last calendar year whose NSE holiday list is fully populated above. Dates
# beyond this are rejected rather than silently assumed to be trading days:
# NSE only publishes its holiday circular one year ahead, and variable
# religious holidays (Holi, Diwali, Eid, ...) cannot be derived, so guessing
# would mislabel every unlisted holiday as open. Extend NSE_HOLIDAYS with the
# next year's official circular and this bumps automatically.
LAST_KNOWN_HOLIDAY_YEAR = max(h.year for h in NSE_HOLIDAYS)


def is_trading_day(day: date) -> bool:
    if day.year > LAST_KNOWN_HOLIDAY_YEAR:
        raise ValueError(
            f"NSE holiday calendar unknown for {day.year}: last known year is "
            f"{LAST_KNOWN_HOLIDAY_YEAR}. Add the official NSE {day.year} holiday "
            "list to NSE_HOLIDAYS before trading dates in that year."
        )
    if day.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return day not in NSE_HOLIDAYS


def session_window(day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, SESSION_OPEN, tzinfo=IST),
        datetime.combine(day, SESSION_CLOSE, tzinfo=IST),
    )


def is_in_session(dt: datetime) -> bool:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(IST)
    if not is_trading_day(local.date()):
        return False
    open_dt, close_dt = session_window(local.date())
    return open_dt <= local <= close_dt
