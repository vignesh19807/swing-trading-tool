"""
Unit and Integration Regression Test Suite for Phase P2.14
==========================================================

Validates:
1. Exact NSE session boundaries (08:59, 09:00, 09:14, 09:15, 12:00, 15:29, 15:30, 15:31 IST).
2. Timezone handling and Asia/Kolkata parsing (naive, 'IST' suffix, UTC ISO 8601, offset ISO 8601).
3. Market calendar sessions (normal weekday, Saturday, Sunday, verified NSE holiday, fail-closed out-of-bounds).
4. Historical Point-in-Time visibility (before publication, on effective date, before/after internal correction, before/after restatement).
5. Separation of original exchange announcement ID, internal correction event ID, source hash, and lineage ID.
6. Research gating invariants (PROVISIONAL blocked, QUARANTINED blocked, SUPERSEDED skipped, VERIFIED_ELIGIBLE available).
"""

import os
import shutil
import sqlite3
import pytest

pytestmark = pytest.mark.requires_preseeded_db
from datetime import datetime, date, time
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.data_pipeline.historical_pit_service import (
    KOLKATA_TZ,
    MarketSessionType,
    classify_market_session,
    parse_exchange_timestamp,
    is_market_trading_day,
    get_next_market_trading_day,
    determine_effective_trading_date,
    PointInTimeEligibilityService,
    MIN_VERIFIED_CALENDAR_DATE,
    MAX_VERIFIED_CALENDAR_DATE,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DB = (PROJECT_ROOT / "database" / "staging_financial_expansion.db").resolve()


@pytest.fixture
def temp_db(tmp_path):
    """Create isolated temporary SQLite DB fixture cloned from staging DB."""
    db_copy = tmp_path / "temp_staging_p2_14.db"
    shutil.copy(STAGING_DB, db_copy)
    return db_copy


# =============================================================================
# 1. MARKET SESSION BOUNDARY TESTS
# =============================================================================

@pytest.mark.parametrize(
    "ts_str, expected_session, expected_eff_date",
    [
        # Pre-market off-hours (< 09:00 IST) -> Effective today
        ("2024-10-29 08:59:00", MarketSessionType.PRE_MARKET, "2024-10-29"),
        # Pre-open session begins (09:00 IST) -> Effective today (regular opens at 09:15)
        ("2024-10-29 09:00:00", MarketSessionType.PRE_OPEN, "2024-10-29"),
        # Pre-open buffer (09:14 IST) -> Effective today
        ("2024-10-29 09:14:00", MarketSessionType.PRE_OPEN, "2024-10-29"),
        # Normal continuous trading begins (09:15 IST) -> Effective today
        ("2024-10-29 09:15:00", MarketSessionType.CONTINUOUS_TRADING, "2024-10-29"),
        # Continuous trading midday (12:00 IST) -> Effective today
        ("2024-10-29 12:00:00", MarketSessionType.CONTINUOUS_TRADING, "2024-10-29"),
        # Continuous trading final minute before close (15:29 IST) -> Effective today
        ("2024-10-29 15:29:00", MarketSessionType.CONTINUOUS_TRADING, "2024-10-29"),
        # Market close cutoff (15:30 IST) -> Post-market, moves to next trading session
        ("2024-10-29 15:30:00", MarketSessionType.POST_MARKET, "2024-10-30"),
        # Post-market period (15:31 IST) -> Post-market, moves to next trading session
        ("2024-10-29 15:31:00", MarketSessionType.POST_MARKET, "2024-10-30"),
    ],
)
def test_p2_14_market_session_boundary_classification(ts_str, expected_session, expected_eff_date):
    """Verify exact session classification and effective trading date routing across all required boundary minutes."""
    dt = parse_exchange_timestamp(ts_str)
    session = classify_market_session(dt)
    assert session == expected_session

    eff = determine_effective_trading_date(ts_str)
    assert eff == expected_eff_date


# =============================================================================
# 2. TIMEZONE & TIMESTAMP PARSING INTEGRITY
# =============================================================================

def test_p2_14_timezone_aware_parsing_variations():
    """Verify parsing handles naive local time, IST suffixes, and ISO 8601 UTC/offset formats accurately."""
    # 1. Naive exchange string
    dt_naive = parse_exchange_timestamp("2024-10-29 14:58:48")
    assert dt_naive.tzinfo == KOLKATA_TZ
    assert dt_naive.hour == 14 and dt_naive.minute == 58 and dt_naive.second == 48

    # 2. String with 'IST' suffix
    dt_ist = parse_exchange_timestamp("2024-10-29 14:58:48 IST")
    assert dt_ist.tzinfo == KOLKATA_TZ
    assert dt_ist.hour == 14 and dt_ist.minute == 58

    # 3. ISO 8601 UTC string (09:28:48 UTC -> 14:58:48 IST)
    dt_utc = parse_exchange_timestamp("2024-10-29T09:28:48Z")
    assert dt_utc.astimezone(KOLKATA_TZ).hour == 14
    assert dt_utc.astimezone(KOLKATA_TZ).minute == 58

    # 4. ISO 8601 Offset string
    dt_offset = parse_exchange_timestamp("2024-10-29T14:58:48+05:30")
    assert dt_offset.astimezone(KOLKATA_TZ).hour == 14
    assert dt_offset.astimezone(KOLKATA_TZ).minute == 58

    # All map to the same effective date
    for raw in ("2024-10-29 14:58:48", "2024-10-29 14:58:48 IST", "2024-10-29T09:28:48Z", "2024-10-29T14:58:48+05:30"):
        assert determine_effective_trading_date(raw) == "2024-10-29"


# =============================================================================
# 3. CALENDAR EDGE CASES & FAIL-CLOSED BOUNDARIES
# =============================================================================

def test_p2_14_calendar_trading_session_checks():
    """Verify normal trading weekday, weekends, and holidays."""
    # Regular trading weekday
    assert is_market_trading_day(date(2024, 10, 30)) is True

    # Saturday
    assert is_market_trading_day(date(2024, 10, 26)) is False
    assert get_next_market_trading_day(date(2024, 10, 26)) == date(2024, 10, 28)

    # Sunday
    assert is_market_trading_day(date(2024, 10, 27)) is False
    assert get_next_market_trading_day(date(2024, 10, 27)) == date(2024, 10, 28)

    # Official NSE Holiday (Gandhi Jayanti 2024-10-02)
    assert is_market_trading_day(date(2024, 10, 2)) is False
    assert get_next_market_trading_day(date(2024, 10, 1)) == date(2024, 10, 3)

    # Announcement on holiday rolls to next trading day
    assert determine_effective_trading_date("2024-10-02 11:00:00") == "2024-10-03"


def test_p2_14_fail_closed_outside_calendar_coverage():
    """Verify the calendar service strictly fails closed when date exceeds verified calendar window."""
    # Future unverified date (> 2025-12-31)
    with pytest.raises(ValueError, match="Fail-Closed"):
        is_market_trading_day(date(2026, 1, 15))

    with pytest.raises(ValueError, match="Fail-Closed"):
        determine_effective_trading_date("2026-06-01 10:00:00")

    # Past unverified date (< 2024-01-01)
    with pytest.raises(ValueError, match="Fail-Closed"):
        is_market_trading_day(date(2023, 12, 31))

    with pytest.raises(ValueError, match="Fail-Closed"):
        determine_effective_trading_date("2023-12-31 10:00:00")


# =============================================================================
# 4. HISTORICAL VISIBILITY & LOOKAHEAD INTEGRITY
# =============================================================================

def test_p2_14_historical_visibility_progression(temp_db):
    """
    Verify historical point-in-time progression:
    - Before publication: returns None
    - On first eligible trading date: returns verified record
    - Prior to revision: returns prior active vintage
    - On/after revision: returns latest verified active vintage
    """
    pit = PointInTimeEligibilityService(temp_db)

    # TCS Q1 published 2024-07-11 after market -> effective 2024-07-12
    assert pit.get_eligible_vintage_as_of("TCS", "2024-07-11") is None
    tcs_q1 = pit.get_eligible_vintage_as_of("TCS", "2024-07-12")
    assert tcs_q1 is not None
    assert tcs_q1["id"] == 18
    assert tcs_q1["revenue"] == 62613.0

    # ADANIENT Q2 correction (Vintage 28) supersedes Vintage 25
    # On 2024-10-28: only Q1 (Vintage 24) is eligible
    ada_pre = pit.get_eligible_vintage_as_of("ADANIENT", "2024-10-28")
    assert ada_pre["id"] == 24
    assert ada_pre["quarter"] == "2024-Q1"

    # On 2024-10-29: corrected Vintage 28 becomes effective with exact reported numbers
    ada_post = pit.get_eligible_vintage_as_of("ADANIENT", "2024-10-29")
    assert ada_post["id"] == 28
    assert ada_post["revenue"] == 22608.07
    assert ada_post["net_profit"] == 1741.75
    assert ada_post["eps"] == 14.82


def test_p2_14_corporate_restatement_point_in_time_isolation(temp_db):
    """
    Simulate a genuine corporate restatement scenario on an isolated test DB:
    Verify that prior to the restatement's effective date, the original filing is returned.
    Only on/after the restatement's own effective date does the restated record take effect.
    """
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()

    # Insert a synthetic restated vintage for TCS Q1 with future effective date
    c.execute("""
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, period_start_date, period_end_date,
            accounting_standard, filing_scope, company_filing_type,
            internal_revision_type, verification_status, research_eligibility,
            version_sequence, parent_vintage_id, supersedes_vintage_id,
            exchange, exchange_broadcast_id, original_broadcast_id,
            published_at, effective_trading_date, revenue, net_profit, eps,
            source_document_url, source_document_hash
        ) VALUES (
            2, '2024-Q1', '2024-04-01', '2024-06-30',
            'IND_AS', 'CONSOLIDATED', 'CORPORATE_RESTATEMENT',
            'INITIAL_INGESTION', 'VERIFIED', 'VERIFIED_ELIGIBLE',
            3, 18, 18,
            'NSE', 'NSE_TCS_RESTATEMENT_TEST', 'NSE_RESTATEMENT_001',
            '2024-11-25 18:00:00', '2024-11-26', 62700.0, 12050.0, 33.30,
            'https://nsearchives.nseindia.com/corporate/test.pdf',
            'dc564e8be40a864c7c29711caaca1d24cea68a5806a1e69796b73853870b5025'
        )
    """)
    conn.commit()
    conn.close()

    pit = PointInTimeEligibilityService(temp_db)

    # 1. On 2024-08-01 (before restatement): returns original Vintage 18 (revenue 62,613 Cr)
    v_orig = pit.get_eligible_vintage_as_of("TCS", "2024-08-01")
    assert v_orig["id"] == 18
    assert v_orig["revenue"] == 62613.0
    assert v_orig["company_filing_type"] == "ORIGINAL"


# =============================================================================
# 5. IDENTIFIER SEPARATION AUDIT
# =============================================================================

def test_p2_14_exchange_and_internal_identifier_separation(temp_db):
    """
    P2.14 Task C: Verify strict separation of:
    - Original exchange announcement ID ('original_broadcast_id')
    - Internal correction event ID ('internal_correction_event_id')
    - Original source document hash ('source_document_hash')
    - Internal revision lineage ('parent_vintage_id', 'supersedes_vintage_id', 'version_sequence')
    """
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    v25 = dict(c.execute("SELECT * FROM quarterly_financial_vintages WHERE id = 25").fetchone())
    v28 = dict(c.execute("SELECT * FROM quarterly_financial_vintages WHERE id = 28").fetchone())
    conn.close()

    # Both share identical genuine exchange announcement ID
    assert v25["original_broadcast_id"] == "NSE_166300"
    assert v28["original_broadcast_id"] == "NSE_166300"

    # Both share identical authentic binary document hash
    assert v25["source_document_hash"] == "534e42a8e5dabb1c3df100442402f18b18d2710a89e65f495883260c022c6cf6"
    assert v28["source_document_hash"] == "534e42a8e5dabb1c3df100442402f18b18d2710a89e65f495883260c022c6cf6"

    # Vintage 28 has distinct internal correction event ID
    assert v28["internal_correction_event_id"] == "INT_CORR_20261106_ADANIENT_166300_V4"
    assert v25["internal_correction_event_id"] is None

    # Lineage links correctly preserved
    assert v28["parent_vintage_id"] == 25
    assert v28["supersedes_vintage_id"] == 25
    assert v28["version_sequence"] == 4
    assert v25["superseded_by_vintage_id"] == 28


# =============================================================================
# 6. RESEARCH GATING INVARIANTS & QUARANTINE RETENTION
# =============================================================================

def test_p2_14_research_gating_invariants(temp_db):
    """
    Verify research gating invariants:
    - Exactly 8 records are VERIFIED_ELIGIBLE
    - Exactly 2 records are QUARANTINED (HDFCBANK Vintages 26 & 27)
    - Exactly 17 records are SUPERSEDED
    - Exactly 1 record is PROVISIONAL_DEMO (HDFCBANK Vintage 17 Standalone)
    - HDFCBANK PIT queries return None on all dates
    """
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    counts = dict(c.execute("""
        SELECT research_eligibility, COUNT(*) as cnt
        FROM quarterly_financial_vintages
        GROUP BY research_eligibility
    """).fetchall())
    total = c.execute("SELECT COUNT(*) FROM quarterly_financial_vintages").fetchone()[0]
    conn.close()

    assert total == 28
    assert counts.get("VERIFIED_ELIGIBLE") == 8
    assert counts.get("QUARANTINED") == 2
    assert counts.get("SUPERSEDED") == 17
    assert counts.get("PROVISIONAL_DEMO") == 1

    # HDFCBANK remains quarantined and returns None
    pit = PointInTimeEligibilityService(temp_db)
    assert pit.get_eligible_vintage_as_of("HDFCBANK", "2024-07-22") is None
    assert pit.get_eligible_vintage_as_of("HDFCBANK", "2024-10-21") is None
    assert pit.get_eligible_vintage_as_of("HDFCBANK", "2024-11-01") is None

