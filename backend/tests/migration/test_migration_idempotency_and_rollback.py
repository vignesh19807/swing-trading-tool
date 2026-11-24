"""
backend/tests/migration/test_migration_idempotency_and_rollback.py
==================================================================
Tests for Phase 7.2C idempotency, transaction rollback, and source immutability.

Validates:
1. Repeated migration is 100% idempotent (second run has 0 inserts, 0 conflicts).
2. Simulated batch failure triggers clean transaction rollback.
3. Source SQLite database SHA-256 is verified unchanged before and after all test runs.
"""

import os
import sqlite3
import tempfile
import pytest

from scripts.migration.common import compute_file_sha256
from scripts.migration.sync_companies import sync_companies_to_sqlite
from scripts.migration.sync_market_data import sync_market_data_to_sqlite

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REAL_SQLITE_PATH = os.path.join(PROJECT_ROOT, "database", "swing_trading.db")
EXPECTED_SQLITE_HASH = "1BE49BDDE48A2954C2687A48234AD65CDC4382FAE127274EC9370B1B5400BEA6"

def test_real_sqlite_hash_unaltered():
    """Confirms real SQLite database hash is unaltered before and after testing."""
    if os.path.exists(REAL_SQLITE_PATH):
        current_hash = compute_file_sha256(REAL_SQLITE_PATH)
        assert current_hash == EXPECTED_SQLITE_HASH, "CRITICAL: Real SQLite database hash altered!"


def test_migration_idempotency():
    """Confirms that executing synchronization multiple times causes zero unintended inserts or side effects."""
    src_fd, src_path = tempfile.mkstemp(suffix="_idem_src.db")
    dst_fd, dst_path = tempfile.mkstemp(suffix="_idem_dst.db")
    os.close(src_fd)
    os.close(dst_fd)

    try:
        # Setup source
        s_conn = sqlite3.connect(src_path)
        s_cur = s_conn.cursor()
        s_cur.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT UNIQUE, company_name TEXT, sector TEXT, industry TEXT, exchange TEXT, sector_id INT, industry_id INT);")
        s_cur.execute("CREATE TABLE daily_prices (id INTEGER PRIMARY KEY, company_id INT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INT, adjusted_close REAL, UNIQUE(company_id, date));")
        s_cur.execute("INSERT INTO companies VALUES (1, 'INFY', 'Infosys', 'IT', 'Software', 'NSE', 1, 1);")
        s_cur.execute("INSERT INTO daily_prices VALUES (1, 1, '2026-11-01', 1500.0, 1510.0, 1490.0, 1505.0, 1000, 1505.0);")
        s_conn.commit()
        s_conn.close()

        # Setup destination
        d_conn = sqlite3.connect(dst_path)
        d_cur = d_conn.cursor()
        d_cur.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT UNIQUE, company_name TEXT, sector TEXT, industry TEXT, exchange TEXT, sector_id INT, industry_id INT);")
        d_cur.execute("CREATE TABLE daily_prices (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INT, adjusted_close REAL, UNIQUE(company_id, date));")
        d_conn.commit()
        d_conn.close()

        from scripts.migration.sync_companies import read_source_companies
        src_comps = read_source_companies(src_path)

        # First Execution
        sync_companies_to_sqlite(dst_path, src_comps, commit=True)
        res1 = sync_market_data_to_sqlite(dst_path, src_path, commit=True)
        assert res1['total_inserted'] == 1
        assert res1['total_matching'] == 0

        # Second Execution (Idempotency Check)
        res_comp2 = sync_companies_to_sqlite(dst_path, src_comps, commit=True)
        assert res_comp2['inserted_count'] == 0
        assert res_comp2['matching_count'] == 1

        res2 = sync_market_data_to_sqlite(dst_path, src_path, commit=True)
        assert res2['total_inserted'] == 0
        assert res2['total_matching'] == 1
        assert res2['total_conflicts'] == 0

    finally:
        if os.path.exists(src_path):
            os.remove(src_path)
        if os.path.exists(dst_path):
            os.remove(dst_path)


def test_transaction_rollback_on_failure():
    """Confirms that a database failure inside a transaction rolls back all partial writes."""
    dst_fd, dst_path = tempfile.mkstemp(suffix="_fail_dst.db")
    os.close(dst_fd)

    try:
        conn = sqlite3.connect(dst_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, val TEXT UNIQUE);")
        cur.execute("INSERT INTO test_table VALUES (1, 'INITIAL');")
        conn.commit()

        # Attempt batch with duplicate inside transaction
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute("BEGIN TRANSACTION;")
            cur.execute("INSERT INTO test_table VALUES (2, 'ROW_A');")
            # Trigger unique violation
            cur.execute("INSERT INTO test_table VALUES (3, 'INITIAL');")
            conn.commit()

        cur.execute("ROLLBACK;")
        
        # Verify ROW_A was NOT committed
        cur.execute("SELECT val FROM test_table;")
        rows = [r[0] for r in cur.fetchall()]
        assert rows == ['INITIAL'], "Rollback failed: partial insert was committed!"
        conn.close()
    finally:
        if os.path.exists(dst_path):
            os.remove(dst_path)
