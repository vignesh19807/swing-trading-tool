"""
Financial Filing Validation & Market Session Engine
===================================================

Phase P2.5 Module: Validates filing provenance and calculates the
deterministic Effective Trading Date using Indian market operating hours.

Rules:
- Normal trading session: 09:15 to 15:30 IST on official trading days.
- Pre-market (< 09:00 IST): Effective Same Day at Open.
- After-market (> 15:30 IST): Effective Next Trading Day at Open.
- Weekends & Holidays: Effective Next Trading Day at Open.
- Ambiguous / Date-only: Conservative fallback to Next Trading Day at Open.
"""

from datetime import datetime, date, time
from typing import Dict, Any, Optional, Set

# Known Official NSE/BSE Trading Holidays for 2024 (Asia/Kolkata)
NSE_HOLIDAYS_2024: Set[str] = {
    "2024-01-22",  # Special Holiday
    "2024-01-26",  # Republic Day
    "2024-03-08",  # Mahashivratri
    "2024-03-25",  # Holi
    "2024-03-29",  # Good Friday
    "2024-04-11",  # Id-Ul-Fitr
    "2024-04-17",  # Shri Ram Navami
    "2024-05-01",  # Maharashtra Day
    "2024-05-20",  # General Parliamentary Elections
    "2024-06-17",  # Bakri Id
    "2024-07-17",  # Muharram
    "2024-08-15",  # Independence Day
    "2024-10-02",  # Mahatma Gandhi Jayanti
    "2024-11-01",  # Diwali Laxmi Pujan (Muhurat trading evening only)
    "2024-11-15",  # Gurunanak Jayanti
    "2024-11-20",  # Maharashtra Assembly Elections
    "2024-12-25",  # Christmas
}


def is_trading_day(dt: date, holidays: Set[str] = NSE_HOLIDAYS_2024) -> bool:
    """Check if calendar date is an official regular NSE trading session."""
    if dt.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return False
    if dt.strftime("%Y-%m-%d") in holidays:
        return False
    return True


def get_next_trading_day(start_date: date, holidays: Set[str] = NSE_HOLIDAYS_2024) -> date:
    """Find the next regular trading day strictly after start_date."""
    from datetime import timedelta
    current = start_date + timedelta(days=1)
    while not is_trading_day(current, holidays):
        current += timedelta(days=1)
    return current


def calculate_effective_trading_date(
    publication_timestamp_str: str,
    market_close_cutoff: str = "15:30:00",
    market_open_cutoff: str = "09:00:00",
    holidays: Set[str] = NSE_HOLIDAYS_2024
) -> str:
    """
    Deterministically map exchange publication timestamp (Asia/Kolkata) to Effective Trading Date.
    Format input: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
    """
    raw_str = publication_timestamp_str.strip()
    
    # Check for date-only format -> Conservative fallback to Next Trading Day
    if len(raw_str) == 10:
        pub_date = datetime.strptime(raw_str, "%Y-%m-%d").date()
        next_day = get_next_trading_day(pub_date, holidays)
        return next_day.strftime("%Y-%m-%d")

    # Full timestamp parsing
    dt = datetime.strptime(raw_str, "%Y-%m-%d %H:%M:%S")
    pub_date = dt.date()
    pub_time = dt.time()
    
    close_time = datetime.strptime(market_close_cutoff, "%H:%M:%S").time()
    open_time = datetime.strptime(market_open_cutoff, "%H:%M:%S").time()

    if not is_trading_day(pub_date, holidays):
        # Weekend or Holiday -> next regular trading session
        return get_next_trading_day(pub_date, holidays).strftime("%Y-%m-%d")

    # It is a trading day
    if pub_time < open_time:
        # Before market open -> executable same day at open
        return pub_date.strftime("%Y-%m-%d")
    elif pub_time <= close_time:
        # Continuous trading session -> executable same day closing
        return pub_date.strftime("%Y-%m-%d")
    else:
        # After continuous market close (> 15:30:00) -> executable next trading session
        return get_next_trading_day(pub_date, holidays).strftime("%Y-%m-%d")

