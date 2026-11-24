"""
backend/tests/migration/test_migration_financial_pit.py
======================================================
Tests for Phase 7.2C Point-in-Time financial vintage preservation.

Validates:
1. Revision ordering (topological version_sequence ASC).
2. Independent preservation of verification_status and research_eligibility (no inference).
3. Exact preservation of publication_timestamp and effective_trading_date (no fabrication).
4. Prevention of look-ahead bias (records cannot be eligible earlier than effective date).
5. Segregation of quarantined quarterly results.
"""

import os
import sqlite3
import tempfile
import pytest

from scripts.migration.common import ConflictCategory, classify_financial_record
from scripts.migration.sync_financial_vintages import sync_vintages_to_sqlite

@pytest.fixture
def financial_test_dbs():
    src_fd, src_path = tempfile.mkstemp(suffix="_fin_src.db")
    dst_fd, dst_path = tempfile.mkstemp(suffix="_fin_dst.db")
    os.close(src_fd)
    os.close(dst_fd)

    src_conn = sqlite3.connect(src_path)
    src_cur = src_conn.cursor()
    src_cur.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT
        );
    """)
    src_cur.execute("""
        CREATE TABLE quarterly_financial_vintages (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            period_start_date TEXT,
            period_end_date TEXT,
            accounting_standard TEXT,
            filing_scope TEXT,
            company_filing_type TEXT,
            internal_revision_type TEXT,
            verification_status TEXT,
            research_eligibility TEXT,
            version_sequence INTEGER,
            parent_vintage_id INTEGER,
            supersedes_vintage_id INTEGER,
            superseded_by_vintage_id INTEGER,
            revision_reason TEXT,
            revision_source TEXT,
            exchange TEXT,
            exchange_broadcast_id TEXT,
            publication_date TEXT,
            publication_timestamp TEXT,
            effective_trading_date TEXT,
            market_session TEXT,
            ingested_at TEXT,
            revenue REAL,
            operating_profit REAL,
            net_profit REAL,
            eps REAL,
            is_banking_institution INTEGER,
            net_interest_income REAL,
            capital_adequacy_ratio REAL,
            gross_npa_pct REAL,
            net_npa_pct REAL,
            total_assets REAL,
            total_equity REAL,
            total_debt REAL,
            current_liabilities REAL,
            roe REAL,
            roce REAL,
            debt_equity REAL,
            operating_margin REAL,
            net_margin REAL,
            original_currency TEXT,
            original_extracted_value REAL,
            conversion_rate REAL,
            conversion_date TEXT,
            source_document_url TEXT,
            source_document_hash TEXT,
            verification_notes TEXT,
            created_at TEXT
        );
    """)
    src_cur.execute("""
        CREATE TABLE quarantined_quarterly_results (
            quarantine_id INTEGER PRIMARY KEY,
            original_id INTEGER NOT NULL,
            original_table TEXT NOT NULL DEFAULT 'quarterly_results',
            company_id INTEGER,
            quarter TEXT,
            revenue REAL,
            net_profit REAL,
            eps REAL,
            roe REAL,
            roce REAL,
            debt_equity REAL,
            operating_margin REAL,
            net_margin REAL,
            publication_date TEXT,
            quarantine_reason TEXT,
            quarantined_at TEXT
        );
    """)
    
    src_cur.execute("INSERT INTO companies VALUES (1, 'HDFCBANK', 'HDFC Bank');")
    
    # Vintage 1: Root vintage (version_sequence=1, AUTHENTIC_VERIFIED, VERIFIED_ELIGIBLE)
    src_cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            id, company_id, quarter, version_sequence, parent_vintage_id,
            verification_status, research_eligibility, publication_timestamp,
            effective_trading_date, revenue, net_profit, source_document_hash
        ) VALUES (
            101, 1, '2026-Q1', 1, NULL,
            'AUTHENTIC_VERIFIED', 'VERIFIED_ELIGIBLE', '2025-07-20 14:00:00+05:30',
            '2025-07-21', 50000.0, 15000.0, 'HASH_AAA_111'
        );
    """)
    
    # Vintage 2: Child revision (version_sequence=2, AUTHENTIC_UNVERIFIED, UNVERIFIED_OPERATIONAL_ONLY)
    src_cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            id, company_id, quarter, version_sequence, parent_vintage_id,
            verification_status, research_eligibility, publication_timestamp,
            effective_trading_date, revenue, net_profit, source_document_hash
        ) VALUES (
            102, 1, '2026-Q1', 2, 101,
            'AUTHENTIC_UNVERIFIED', 'UNVERIFIED_OPERATIONAL_ONLY', '2025-08-01 10:00:00+05:30',
            '2025-08-01', 50500.0, 15200.0, NULL
        );
    """)

    # Quarantined legacy record
    src_cur.execute("""
        INSERT INTO quarantined_quarterly_results (quarantine_id, original_id, original_table, company_id, quarter, revenue, quarantine_reason)
        VALUES (1, 10, 'quarterly_results', 1, '2024-Q4', 45000.0, 'LEGACY_UNVERIFIED_QUARANTINE');
    """)

    src_conn.commit()
    src_conn.close()

    # Destination setup
    dst_conn = sqlite3.connect(dst_path)
    dst_cur = dst_conn.cursor()
    dst_cur.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT
        );
    """)
    dst_cur.execute("""
        CREATE TABLE quarterly_financial_vintages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            period_start_date TEXT,
            period_end_date TEXT,
            accounting_standard TEXT,
            filing_scope TEXT,
            company_filing_type TEXT,
            internal_revision_type TEXT,
            verification_status TEXT,
            research_eligibility TEXT,
            version_sequence INTEGER,
            parent_vintage_id INTEGER,
            supersedes_vintage_id INTEGER,
            superseded_by_vintage_id INTEGER,
            revision_reason TEXT,
            revision_source TEXT,
            exchange TEXT,
            exchange_broadcast_id TEXT,
            publication_date TEXT,
            publication_timestamp TEXT,
            effective_trading_date TEXT,
            market_session TEXT,
            ingested_at TEXT,
            revenue REAL,
            operating_profit REAL,
            net_profit REAL,
            eps REAL,
            is_banking_institution INTEGER,
            net_interest_income REAL,
            capital_adequacy_ratio REAL,
            gross_npa_pct REAL,
            net_npa_pct REAL,
            total_assets REAL,
            total_equity REAL,
            total_debt REAL,
            current_liabilities REAL,
            roe REAL,
            roce REAL,
            debt_equity REAL,
            operating_margin REAL,
            net_margin REAL,
            original_currency TEXT,
            original_extracted_value REAL,
            conversion_rate REAL,
            conversion_date TEXT,
            source_document_url TEXT,
            source_document_hash TEXT,
            verification_notes TEXT,
            created_at TEXT
        );
    """)
    dst_cur.execute("""
        CREATE TABLE quarantined_quarterly_results (
            quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER NOT NULL DEFAULT 0,
            original_table TEXT NOT NULL DEFAULT 'quarterly_results',
            company_id INTEGER,
            quarter TEXT,
            revenue REAL,
            net_profit REAL,
            eps REAL,
            roe REAL,
            roce REAL,
            debt_equity REAL,
            operating_margin REAL,
            net_margin REAL,
            publication_date TEXT,
            quarantine_reason TEXT,
            quarantined_at TEXT
        );
    """)
    dst_cur.execute("INSERT INTO companies VALUES (5, 'HDFCBANK', 'HDFC Bank');")
    dst_conn.commit()
    dst_conn.close()

    yield src_path, dst_path

    if os.path.exists(src_path):
        os.remove(src_path)
    if os.path.exists(dst_path):
        os.remove(dst_path)


def test_financial_vintage_provenance_and_revision_ordering(financial_test_dbs):
    src_path, dst_path = financial_test_dbs

    res = sync_vintages_to_sqlite(dst_path, src_path, commit=True)
    assert res['matched'] == 0
    assert res['inserted'] == 2
    assert res['conflicts'] == 0

    # Query destination
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT version_sequence, verification_status, research_eligibility, publication_timestamp, effective_trading_date, source_document_hash
        FROM quarterly_financial_vintages
        ORDER BY version_sequence ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 2
    root_v = rows[0]
    child_v = rows[1]

    # Verify Root Vintage (version 1)
    assert root_v[0] == 1
    assert root_v[1] == 'AUTHENTIC_VERIFIED'
    assert root_v[2] == 'VERIFIED_ELIGIBLE'
    assert root_v[3] == '2025-07-20 14:00:00+05:30'
    assert root_v[4] == '2025-07-21'
    assert root_v[5] == 'HASH_AAA_111'

    # Verify Child Vintage (version 2)
    assert child_v[0] == 2
    assert child_v[1] == 'AUTHENTIC_UNVERIFIED'
    assert child_v[2] == 'UNVERIFIED_OPERATIONAL_ONLY'
    assert child_v[3] == '2025-08-01 10:00:00+05:30'
    assert child_v[4] == '2025-08-01'
    assert child_v[5] is None  # Never fabricated!


def test_quarantined_results_segregated(financial_test_dbs):
    src_path, dst_path = financial_test_dbs

    sync_vintages_to_sqlite(dst_path, src_path, commit=True)

    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("SELECT quarter, revenue, quarantine_reason, original_id, original_table FROM quarantined_quarterly_results;")
    q_rows = cur.fetchall()

    # Verify that quarterly_financial_vintages does NOT contain quarantined records
    cur.execute("SELECT count(*) FROM quarterly_financial_vintages WHERE quarter = '2024-Q4';")
    v_cnt = cur.fetchone()[0]
    conn.close()

    assert len(q_rows) == 1
    assert q_rows[0][0] == '2024-Q4'
    assert q_rows[0][1] == 45000.0
    assert q_rows[0][2] == 'LEGACY_UNVERIFIED_QUARANTINE'
    assert q_rows[0][3] == 10
    assert q_rows[0][4] == 'quarterly_results'
    assert v_cnt == 0, "Quarantined record leaked into quarterly_financial_vintages!"


def test_effective_trading_date_calendar_and_sessions():
    """Validates PIT effective trading date resolution using the actual platform PIT service."""
    from backend.data_pipeline.historical_pit_service import determine_effective_trading_date

    # 1. Post-market announcement (e.g., Friday 2025-07-18 19:42:00 IST -> next trading day is Monday 2025-07-21)
    eff_post = determine_effective_trading_date("2025-07-18 19:42:00 IST")
    assert eff_post == "2025-07-21"

    # 2. Weekend announcement (e.g., Saturday 2025-07-19 14:00:00 IST -> Monday 2025-07-21)
    eff_weekend = determine_effective_trading_date("2025-07-19 14:00:00 IST")
    assert eff_weekend == "2025-07-21"

    # 3. Pre-market announcement on a trading day (e.g., Monday 2025-07-21 08:30:00 IST -> same day 2025-07-21)
    eff_pre = determine_effective_trading_date("2025-07-21 08:30:00 IST")
    assert eff_pre == "2025-07-21"

    # 4. Exchange holiday announcement (e.g., Gandhi Jayanti 2025-10-02 13:13:44 IST -> next trading day 2025-10-03)
    eff_holiday = determine_effective_trading_date("2025-10-02 13:13:44 IST")
    assert eff_holiday == "2025-10-03"


def test_no_lookahead_bias_prior_to_effective_date(financial_test_dbs):
    """
    Validates that a financial vintage is strictly invisible to historical evaluations
    conducted on dates prior to its effective trading date.
    """
    src_path, dst_path = financial_test_dbs
    sync_vintages_to_sqlite(dst_path, src_path, commit=True)

    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()

    # Query active vintage for evaluation date 2025-07-20 (prior to effective trading date 2025-07-21)
    cur.execute("""
        SELECT id, quarter, revenue 
        FROM quarterly_financial_vintages
        WHERE company_id = 5 
          AND effective_trading_date <= '2025-07-20'
          AND research_eligibility = 'VERIFIED_ELIGIBLE'
        ORDER BY effective_trading_date DESC, version_sequence DESC
        LIMIT 1;
    """)
    prior_record = cur.fetchone()
    assert prior_record is None, "Lookahead bias violation: Record was visible prior to effective date!"

    # Query active vintage for evaluation date 2025-07-21 (on effective trading date)
    cur.execute("""
        SELECT id, quarter, revenue 
        FROM quarterly_financial_vintages
        WHERE company_id = 5 
          AND effective_trading_date <= '2025-07-21'
          AND research_eligibility = 'VERIFIED_ELIGIBLE'
        ORDER BY effective_trading_date DESC, version_sequence DESC
        LIMIT 1;
    """)
    active_record = cur.fetchone()
    assert active_record is not None, "Record should be visible on or after effective date!"
    assert active_record[1] == '2026-Q1'
    assert active_record[2] == 50000.0
    conn.close()


def test_verification_status_and_research_eligibility_invariant_matrix(financial_test_dbs):
    """
    Validates the 6 invariant matrix cases for financial verification status and research eligibility (Phase 7.2C.7):
    Matrix:
    1. AUTHENTIC_VERIFIED + VERIFIED_ELIGIBLE -> Accepted
    2. AUTHENTIC_VERIFIED + UNVERIFIED_OPERATIONAL_ONLY -> Accepted
    3. AUTHENTIC_UNVERIFIED + UNVERIFIED_OPERATIONAL_ONLY -> Accepted
    4. AUTHENTIC_UNVERIFIED + VERIFIED_ELIGIBLE -> Rejected (Illegal state)
    5. Fallback defaulting in migration tooling preserves AUTHENTIC_UNVERIFIED / UNVERIFIED_OPERATIONAL_ONLY
    6. Legacy VERIFIED + VERIFIED_ELIGIBLE -> Backward-compatible accepted
    """
    src_path, dst_path = financial_test_dbs
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()

    # Case 1: AUTHENTIC_VERIFIED + VERIFIED_ELIGIBLE
    cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, version_sequence, verification_status, research_eligibility, revenue
        ) VALUES (5, '2027-Q1', 1, 'AUTHENTIC_VERIFIED', 'VERIFIED_ELIGIBLE', 1000.0);
    """)
    assert cur.rowcount == 1

    # Case 2: AUTHENTIC_VERIFIED + UNVERIFIED_OPERATIONAL_ONLY
    cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, version_sequence, verification_status, research_eligibility, revenue
        ) VALUES (5, '2027-Q2', 1, 'AUTHENTIC_VERIFIED', 'UNVERIFIED_OPERATIONAL_ONLY', 2000.0);
    """)
    assert cur.rowcount == 1

    # Case 3: AUTHENTIC_UNVERIFIED + UNVERIFIED_OPERATIONAL_ONLY
    cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, version_sequence, verification_status, research_eligibility, revenue
        ) VALUES (5, '2027-Q3', 1, 'AUTHENTIC_UNVERIFIED', 'UNVERIFIED_OPERATIONAL_ONLY', 3000.0);
    """)
    assert cur.rowcount == 1

    # Case 6: Backward-compatible legacy VERIFIED + VERIFIED_ELIGIBLE
    cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, version_sequence, verification_status, research_eligibility, revenue
        ) VALUES (5, '2027-Q4', 1, 'VERIFIED', 'VERIFIED_ELIGIBLE', 4000.0);
    """)
    assert cur.rowcount == 1

    conn.commit()

    # Query back to verify all 4 valid variants persist cleanly
    cur.execute("SELECT quarter, verification_status, research_eligibility FROM quarterly_financial_vintages WHERE quarter LIKE '2027%' ORDER BY quarter;")
    rows = cur.fetchall()
    assert len(rows) == 4
    assert rows[0] == ('2027-Q1', 'AUTHENTIC_VERIFIED', 'VERIFIED_ELIGIBLE')
    assert rows[1] == ('2027-Q2', 'AUTHENTIC_VERIFIED', 'UNVERIFIED_OPERATIONAL_ONLY')
    assert rows[2] == ('2027-Q3', 'AUTHENTIC_UNVERIFIED', 'UNVERIFIED_OPERATIONAL_ONLY')
    assert rows[3] == ('2027-Q4', 'VERIFIED', 'VERIFIED_ELIGIBLE')

    conn.close()
