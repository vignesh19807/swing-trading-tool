"""
backend/tests/migration/test_migration_conflict_engine.py
=========================================================
Tests for Phase 7.2C migration conflict engine and company synchronization.

Validates:
1. Missing company insertion.
2. Duplicate company detection.
3. Foreign-key resolution by symbol.
4. Market data three-category conflict handling:
   - MISSING -> inserted.
   - MATCHING -> skipped.
   - CONFLICTING -> quarantined, NEVER overwritten.
"""

import os
import sqlite3
import tempfile
import pytest

from scripts.migration.common import (
    ConflictCategory,
    classify_market_record,
    classify_financial_record,
    classify_pilot_record,
    SyntheticDisposition
)
from scripts.migration.sync_companies import sync_companies_to_sqlite
from scripts.migration.sync_market_data import sync_market_data_to_sqlite

@pytest.fixture
def isolated_db_pair():
    """Creates a temporary source SQLite DB and destination SQLite DB."""
    src_fd, src_path = tempfile.mkstemp(suffix="_src.db")
    dst_fd, dst_path = tempfile.mkstemp(suffix="_dst.db")
    os.close(src_fd)
    os.close(dst_fd)

    # Setup source schema & data
    src_conn = sqlite3.connect(src_path)
    src_cur = src_conn.cursor()
    src_cur.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            sector TEXT,
            industry TEXT,
            exchange TEXT,
            sector_id INTEGER,
            industry_id INTEGER
        );
    """)
    src_cur.execute("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            adjusted_close REAL,
            UNIQUE(company_id, date)
        );
    """)
    src_cur.execute("INSERT INTO companies VALUES (1, 'INFY', 'Infosys Ltd', 'IT', 'Software', 'NSE', 1, 1);")
    src_cur.execute("INSERT INTO companies VALUES (2, 'TCS', 'Tata Consultancy', 'IT', 'Software', 'NSE', 1, 1);")
    src_cur.execute("INSERT INTO companies VALUES (3, 'RELIANCE', 'Reliance Industries', 'Energy', 'Oil', 'NSE', 2, 2);")
    
    # Prices: 2 bars for INFY, 1 bar for TCS
    src_cur.execute("INSERT INTO daily_prices VALUES (1, 1, '2026-11-01', 1500.0, 1520.0, 1490.0, 1510.0, 100000, 1510.0);")
    src_cur.execute("INSERT INTO daily_prices VALUES (2, 1, '2026-11-02', 1510.0, 1530.0, 1505.0, 1525.0, 120000, 1525.0);")
    src_cur.execute("INSERT INTO daily_prices VALUES (3, 2, '2026-11-01', 3500.0, 3550.0, 3490.0, 3520.0, 50000, 3520.0);")
    src_conn.commit()
    src_conn.close()

    # Setup destination schema with pilot state
    dst_conn = sqlite3.connect(dst_path)
    dst_cur = dst_conn.cursor()
    dst_cur.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            sector TEXT,
            industry TEXT,
            exchange TEXT,
            sector_id INTEGER,
            industry_id INTEGER,
            is_active BOOLEAN DEFAULT 1
        );
    """)
    dst_cur.execute("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            adjusted_close REAL,
            UNIQUE(company_id, date)
        );
    """)
    # Destination already has INFY (with ID 10) and pilot STOCK1
    dst_cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (10, 'INFY', 'Infosys Ltd');")
    dst_cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (20, 'STOCK1', 'Stock One Test');")
    
    # Destination has 1 matching bar for INFY on 2026-11-01
    dst_cur.execute("INSERT INTO daily_prices (company_id, date, open, high, low, close, volume, adjusted_close) VALUES (10, '2026-11-01', 1500.0, 1520.0, 1490.0, 1510.0, 100000, 1510.0);")
    # Destination has 1 CONFLICTING bar for INFY on 2026-11-02 (close is 9999.0 vs 1525.0 in source)
    dst_cur.execute("INSERT INTO daily_prices (company_id, date, open, high, low, close, volume, adjusted_close) VALUES (10, '2026-11-02', 1510.0, 1530.0, 1505.0, 9999.0, 120000, 9999.0);")
    dst_conn.commit()
    dst_conn.close()

    yield src_path, dst_path

    # Cleanup
    if os.path.exists(src_path):
        os.remove(src_path)
    if os.path.exists(dst_path):
        os.remove(dst_path)


def test_company_sync_and_duplicate_detection(isolated_db_pair):
    src_path, dst_path = isolated_db_pair
    from scripts.migration.sync_companies import read_source_companies

    src_comps = read_source_companies(src_path)
    assert len(src_comps) == 3

    # Run in commit mode
    res = sync_companies_to_sqlite(dst_path, src_comps, commit=True)
    assert res['matching_count'] == 1  # INFY already existed
    assert res['missing_count'] == 2   # TCS and RELIANCE
    assert res['inserted_count'] == 2

    # Verify destination now has 4 companies (INFY, STOCK1, TCS, RELIANCE)
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM companies ORDER BY symbol;")
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    assert symbols == ['INFY', 'RELIANCE', 'STOCK1', 'TCS']

    # Verify pilot record classification
    pilot_items = res['pilot_records_investigation']
    assert len(pilot_items) == 1
    assert pilot_items[0]['symbol'] == 'STOCK1'
    assert pilot_items[0]['disposition'] == SyntheticDisposition.CANDIDATE_FOR_REMOVAL


def test_market_data_three_way_conflict_handling(isolated_db_pair):
    src_path, dst_path = isolated_db_pair
    from scripts.migration.sync_companies import read_source_companies

    # First sync companies so destination knows TCS
    src_comps = read_source_companies(src_path)
    sync_companies_to_sqlite(dst_path, src_comps, commit=True)

    # Now sync market data
    res = sync_market_data_to_sqlite(dst_path, src_path, chunk_size=10, commit=True)

    # We expect:
    # 1 bar MATCHING (INFY 2026-11-01)
    # 1 bar CONFLICTING (INFY 2026-11-02, destination has 9999.0 vs 1525.0)
    # 1 bar MISSING (TCS 2026-11-01) -> inserted
    assert res['total_matching'] == 1
    assert res['total_conflicts'] == 1
    assert res['total_inserted'] == 1

    # CRITICAL INVARIANT: The conflicting bar (INFY 2026-11-02) MUST NOT have been overwritten!
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("SELECT close FROM daily_prices WHERE company_id = 10 AND date = '2026-11-02';")
    dst_close = cur.fetchone()[0]
    conn.close()
    assert dst_close == 9999.0  # Destination was preserved; conflict quarantined
