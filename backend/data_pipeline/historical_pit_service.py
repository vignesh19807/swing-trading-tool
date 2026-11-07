"""
Historical Point-in-Time (PIT) Financial Eligibility & Market Calendar Service
=============================================================================

Phase P2.9 Component:
- Maps corporate disclosure announcements to executable market trading dates.
- Handles:
    - Pre-market announcements (< 09:00 IST -> same trading day)
    - During-market announcements (09:00 - 15:30 IST -> same trading day close / next day open)
    - After-market announcements (> 15:30 IST -> next trading day open)
    - Weekends (Saturday/Sunday -> next regular trading session)
    - Exchange holidays (official NSE holidays -> next regular trading session)
    - Missing publication timestamps (conservative fallback to next regular trading session)
    - Internal extraction corrections vs revised company disclosures vs genuine restatements
- Point-in-Time (PIT) Visibility Rules:
    - Later company restatements are NEVER visible prior to their own effective trading date.
    - An internal extraction correction may maintain the original effective trading date ONLY
      when verified against the original source document.
    - Research Eligibility Gating:
        - PROVISIONAL_DEMO: Blocked from production research and backtesting.
        - QUARANTINED: Blocked from financial scoring and trade decisions.
        - SUPERSEDED: Blocked from current research selection.
        - VERIFIED_ELIGIBLE: Available ONLY on or after effective_trading_date.
"""

import sqlite3
from datetime import datetime, date, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

# Exchange local timezone for NSE/BSE India
KOLKATA_TZ: ZoneInfo = ZoneInfo("Asia/Kolkata")

# Official NSE/BSE Trading Holidays for 2024 and 2025 (Asia/Kolkata)
MIN_VERIFIED_CALENDAR_DATE: date = date(2024, 1, 1)
MAX_VERIFIED_CALENDAR_DATE: date = date(2025, 12, 31)

NSE_HOLIDAYS: Set[str] = {
    # 2024 Holidays
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
    # 2025 Holidays
    "2025-02-26",  # Mahashivratri
    "2025-03-14",  # Holi
    "2025-03-31",  # Id-Ul-Fitr
    "2025-04-10",  # Mahavir Jayanti
    "2025-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2025-04-18",  # Good Friday
    "2025-05-01",  # Maharashtra Day
    "2025-08-15",  # Independence Day
    "2025-08-27",  # Ganesh Chaturthi
    "2025-10-02",  # Mahatma Gandhi Jayanti / Dussehra
    "2025-10-21",  # Diwali
    "2025-10-22",  # Diwali Balipratipada
    "2025-11-05",  # Prakash Gurpurb
    "2025-12-25",  # Christmas
}


class MarketSessionType(str, Enum):
    """
    Official NSE Equities Market Session Types (Asia/Kolkata):
    - PRE_MARKET: Off-hours prior to pre-open (< 09:00:00 IST)
    - PRE_OPEN: Order entry, modification, and price discovery (09:00:00 - 09:14:59 IST)
    - CONTINUOUS_TRADING: Normal regular trading session (09:15:00 - 15:29:59 IST)
    - POST_MARKET: Closing price auction, calculation, and post-close (>= 15:30:00 IST)
    - WEEKEND: Saturday or Sunday (no regular continuous trading)
    - EXCHANGE_HOLIDAY: Officially notified exchange closure
    """
    PRE_MARKET = "PRE_MARKET"
    PRE_OPEN = "PRE_OPEN"
    CONTINUOUS_TRADING = "CONTINUOUS_TRADING"
    POST_MARKET = "POST_MARKET"
    WEEKEND = "WEEKEND"
    EXCHANGE_HOLIDAY = "EXCHANGE_HOLIDAY"


def parse_exchange_timestamp(ts_str: str) -> datetime:
    """
    Parse exchange publication timestamp string to timezone-aware datetime in Asia/Kolkata.
    Supports:
    - 'YYYY-MM-DD HH:MM:SS' (interpreted as Asia/Kolkata exchange local time)
    - 'YYYY-MM-DD HH:MM:SS IST'
    - ISO 8601 strings (e.g. '2024-10-29T14:58:48+05:30' or '2024-10-29T09:28:48Z')
    """
    raw = ts_str.strip()
    if raw.endswith(" IST"):
        raw = raw[:-4].strip()

    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=KOLKATA_TZ)
        return dt.astimezone(KOLKATA_TZ)
    except Exception:
        pass

    clean = raw.replace("T", " ")
    if "." in clean:
        clean = clean.split(".")[0]
    dt = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=KOLKATA_TZ)


def classify_market_session(
    dt: datetime,
    holidays: Set[str] = NSE_HOLIDAYS,
    enforce_coverage: bool = True,
) -> MarketSessionType:
    """
    Classify a datetime into an official NSE market session under Asia/Kolkata local time.
    Fails closed if the evaluation date falls outside verified calendar coverage.
    """
    if dt.tzinfo is not None:
        local_dt = dt.astimezone(KOLKATA_TZ)
    else:
        local_dt = dt.replace(tzinfo=KOLKATA_TZ)

    d = local_dt.date()
    t = local_dt.time()

    if enforce_coverage and (d < MIN_VERIFIED_CALENDAR_DATE or d > MAX_VERIFIED_CALENDAR_DATE):
        raise ValueError(
            f"Fail-Closed: Date {d} falls outside verified exchange calendar coverage "
            f"[{MIN_VERIFIED_CALENDAR_DATE} to {MAX_VERIFIED_CALENDAR_DATE}]."
        )

    if d.weekday() >= 5:
        return MarketSessionType.WEEKEND

    if d.strftime("%Y-%m-%d") in holidays:
        return MarketSessionType.EXCHANGE_HOLIDAY

    if t < time(9, 0, 0):
        return MarketSessionType.PRE_MARKET
    elif t < time(9, 15, 0):
        return MarketSessionType.PRE_OPEN
    elif t < time(15, 30, 0):
        return MarketSessionType.CONTINUOUS_TRADING
    else:
        return MarketSessionType.POST_MARKET


def is_market_trading_day(
    dt: date,
    holidays: Set[str] = NSE_HOLIDAYS,
    enforce_coverage: bool = True
) -> bool:
    """
    Check if date is an active regular weekday NSE trading session.
    Fails closed if the evaluation date falls outside verified calendar coverage.
    """
    if enforce_coverage and (dt < MIN_VERIFIED_CALENDAR_DATE or dt > MAX_VERIFIED_CALENDAR_DATE):
        raise ValueError(
            f"Fail-Closed: Date {dt} falls outside verified exchange calendar coverage "
            f"[{MIN_VERIFIED_CALENDAR_DATE} to {MAX_VERIFIED_CALENDAR_DATE}]. "
            f"Cannot treat unverified dates as trading sessions without authenticated holiday schedule."
        )
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    if dt.strftime("%Y-%m-%d") in holidays:
        return False
    return True


def get_next_market_trading_day(
    start_date: date,
    holidays: Set[str] = NSE_HOLIDAYS,
    enforce_coverage: bool = True
) -> date:
    """
    Find the first trading session strictly after start_date.
    Fails closed if start_date or search exceeds verified calendar window.
    """
    if enforce_coverage and (start_date < MIN_VERIFIED_CALENDAR_DATE or start_date >= MAX_VERIFIED_CALENDAR_DATE):
        raise ValueError(
            f"Fail-Closed: Start date {start_date} is outside verified exchange calendar window "
            f"[{MIN_VERIFIED_CALENDAR_DATE} to {MAX_VERIFIED_CALENDAR_DATE}]."
        )
    current = start_date + timedelta(days=1)
    while not is_market_trading_day(current, holidays, enforce_coverage=enforce_coverage):
        current += timedelta(days=1)
    return current


def determine_effective_trading_date(
    publication_timestamp_str: Optional[str],
    market_open: str = "09:00:00",
    market_close: str = "15:30:00",
    holidays: Set[str] = NSE_HOLIDAYS,
    enforce_coverage: bool = True,
) -> str:
    """
    Map exchange publication timestamp to canonical effective trading date.

    Platform Point-in-Time (PIT) Policy:
    - PRE_MARKET (< 09:00:00 IST): Broadcast prior to market open. Effective today.
    - PRE_OPEN (09:00:00 - 09:14:59 IST): Broadcast during pre-open discovery.
      Normal continuous trading begins at 09:15:00 IST. Effective today.
    - CONTINUOUS_TRADING (09:15:00 - 15:29:59 IST): Broadcast during active continuous session.
      Actionable before market close / closing session. Effective today.
    - POST_MARKET (>= 15:30:00 IST): Broadcast after continuous trading termination.
      Actionable next trading session.
    - WEEKEND / EXCHANGE_HOLIDAY: Market closed. Actionable next trading session.
    - Date-only fallback: Conservative fallback to next regular trading session.
    - Outside verified calendar window: Fails closed.
    """
    if not publication_timestamp_str or not publication_timestamp_str.strip():
        # Fallback to tomorrow if no timestamp provided
        return get_next_market_trading_day(date.today(), holidays, enforce_coverage=enforce_coverage).strftime("%Y-%m-%d")

    raw_str = publication_timestamp_str.strip()

    # Date-only string (e.g. '2024-07-20') -> conservative fallback
    if len(raw_str) == 10 and raw_str.count("-") == 2:
        pub_date = datetime.strptime(raw_str, "%Y-%m-%d").date()
        if enforce_coverage and (pub_date < MIN_VERIFIED_CALENDAR_DATE or pub_date > MAX_VERIFIED_CALENDAR_DATE):
            raise ValueError(
                f"Fail-Closed: Publication date {pub_date} falls outside verified exchange calendar coverage "
                f"[{MIN_VERIFIED_CALENDAR_DATE} to {MAX_VERIFIED_CALENDAR_DATE}]."
            )
        return get_next_market_trading_day(pub_date, holidays, enforce_coverage=enforce_coverage).strftime("%Y-%m-%d")

    dt = parse_exchange_timestamp(raw_str)
    pub_date = dt.date()

    if enforce_coverage and (pub_date < MIN_VERIFIED_CALENDAR_DATE or pub_date > MAX_VERIFIED_CALENDAR_DATE):
        raise ValueError(
            f"Fail-Closed: Publication date {pub_date} falls outside verified exchange calendar coverage "
            f"[{MIN_VERIFIED_CALENDAR_DATE} to {MAX_VERIFIED_CALENDAR_DATE}]."
        )

    session = classify_market_session(dt, holidays=holidays, enforce_coverage=enforce_coverage)

    if session in (MarketSessionType.PRE_MARKET, MarketSessionType.PRE_OPEN, MarketSessionType.CONTINUOUS_TRADING):
        return pub_date.strftime("%Y-%m-%d")
    else:
        # POST_MARKET, WEEKEND, or EXCHANGE_HOLIDAY
        return get_next_market_trading_day(pub_date, holidays, enforce_coverage=enforce_coverage).strftime("%Y-%m-%d")


class PointInTimeEligibilityService:
    """
    Evaluates Point-in-Time (PIT) financial record availability for backtesting,
    scoring, and live production screening.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).resolve()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_eligible_vintage_as_of(
        self,
        symbol: str,
        as_of_date: str,
        filing_scope: str = "CONSOLIDATED",
        enforce_coverage: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest active financial vintage for a company that was legally
        and operationally knowable on or before `as_of_date`.

        Strict Invariants:
        1. Effective Trading Date must be <= as_of_date.
        2. Must have research_eligibility = 'VERIFIED_ELIGIBLE'.
        3. Records with 'PROVISIONAL_DEMO', 'QUARANTINED', or 'SUPERSEDED' are excluded.
        4. If a later revision exists, it only applies on or after ITS OWN effective date.
        5. Fails closed if as_of_date falls outside verified calendar coverage.
        """
        if enforce_coverage:
            as_of_dt = datetime.strptime(as_of_date.strip(), "%Y-%m-%d").date()
            if as_of_dt < MIN_VERIFIED_CALENDAR_DATE or as_of_dt > MAX_VERIFIED_CALENDAR_DATE:
                raise ValueError(
                    f"Fail-Closed: as_of_date '{as_of_date}' falls outside verified exchange calendar coverage "
                    f"[{MIN_VERIFIED_CALENDAR_DATE} to {MAX_VERIFIED_CALENDAR_DATE}]."
                )

        query = """
        SELECT v.*, c.symbol
        FROM quarterly_financial_vintages v
        JOIN companies c ON c.id = v.company_id
        WHERE c.symbol = ?
          AND v.filing_scope = ?
          AND v.effective_trading_date <= ?
          AND v.research_eligibility = 'VERIFIED_ELIGIBLE'
          AND v.verification_status = 'VERIFIED'
        ORDER BY v.period_end_date DESC, v.version_sequence DESC
        LIMIT 1
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (symbol.upper().strip(), filing_scope.upper().strip(), as_of_date))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def audit_vintage_visibility_timeline(
        self,
        symbol: str,
        quarter: str,
        scope: str = "CONSOLIDATED",
    ) -> List[Dict[str, Any]]:
        """
        Trace the historical visibility timeline for all vintages of a specific filing,
        including original filings, revisions, and restatements.
        """
        query = """
        SELECT v.id, v.quarter, v.filing_scope, v.version_sequence,
               v.company_filing_type, v.internal_revision_type,
               v.verification_status, v.research_eligibility,
               v.published_at, v.effective_trading_date,
               v.revenue, v.net_profit, v.eps,
               v.parent_vintage_id, v.superseded_by_vintage_id
        FROM quarterly_financial_vintages v
        JOIN companies c ON c.id = v.company_id
        WHERE c.symbol = ?
          AND v.quarter = ?
          AND v.filing_scope = ?
        ORDER BY v.version_sequence ASC
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (symbol.upper().strip(), quarter.upper().strip(), scope.upper().strip()))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

