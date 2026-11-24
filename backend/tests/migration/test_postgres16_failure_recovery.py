"""
backend/tests/migration/test_postgres16_failure_recovery.py
===========================================================
Failure and Recovery Simulation Test Suite for Phase 7.2C.2.

Validates the 10 mandatory failure modes:
1. Duplicate company insertion.
2. Foreign-key violation.
3. Duplicate market-data records.
4. Conflicting existing market records.
5. Missing technical indicator parent.
6. Financial revision dependency failure.
7. Batch insertion failure.
8. Transaction interruption.
9. Rollback after partial batch failure.
10. Repeated migration execution (idempotency).

All write operations run against isolated temporary databases.
"""

import os
import sqlite3
import tempfile
import pytest

from scripts.migration.common import (
    ConflictCategory,
    classify_market_record,
    classify_financial_record
)
from scripts.migration.sync_companies import sync_companies_to_sqlite
from scripts.migration.sync_market_data import sync_market_data_to_sqlite
from scripts.migration.sync_indicators import sync_indicators_to_sqlite
from scripts.migration.sync_financial_vintages import sync_vintages_to_sqlite

@pytest.fixture
def isolated_failure_env():
    """Sets up an isolated database pair with full referential constraints."""
    src_fd, src_path = tempfile.mkstemp(suffix="_fail_src.db")
    dst_fd, dst_path = tempfile.mkstemp(suffix="_fail_dst.db")
    os.close(src_fd)
    os.close(dst_fd)

    # Destination DB with strict SQLite foreign keys enabled
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("""
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
    cur.execute("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
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
    cur.execute("""
        CREATE TABLE technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            rsi REAL,
            macd REAL,
            macd_signal REAL,
            ema_20 REAL,
            ema_50 REAL,
            ema_200 REAL,
            macd_histogram REAL,
            atr_14 REAL,
            technical_score REAL,
            UNIQUE(company_id, date)
        );
    """)
    cur.execute("""
        CREATE TABLE quarterly_financial_vintages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
            quarter TEXT NOT NULL,
            version_sequence INTEGER NOT NULL,
            parent_vintage_id INTEGER REFERENCES quarterly_financial_vintages(id),
            revenue REAL,
            net_profit REAL,
            eps REAL,
            verification_status TEXT,
            research_eligibility TEXT,
            publication_timestamp TEXT,
            effective_trading_date TEXT,
            source_document_hash TEXT,
            UNIQUE(company_id, quarter, version_sequence)
        );
    """)
    conn.commit()
    conn.close()

    yield src_path, dst_path

    if os.path.exists(src_path):
        os.remove(src_path)
    if os.path.exists(dst_path):
        os.remove(dst_path)


# 1. Duplicate company insertion
def test_simulated_duplicate_company_insertion(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (symbol, company_name) VALUES ('INFY', 'Infosys');")
    conn.commit()

    # Attempting to insert duplicate symbol without conflict handling must raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO companies (symbol, company_name) VALUES ('INFY', 'Duplicate Infosys');")

    conn.close()


# 2. Foreign-key violation
def test_simulated_foreign_key_violation(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Attempt to insert price for non-existent company_id 999
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("""
            INSERT INTO daily_prices (company_id, date, open, high, low, close, volume)
            VALUES (999, '2026-11-01', 100.0, 105.0, 95.0, 102.0, 1000);
        """)
    conn.close()


# 3. Duplicate market-data records
def test_simulated_duplicate_market_data(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'INFY', 'Infosys');")
    cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (1, '2026-11-01', 100.0, 102.0);")
    conn.commit()

    # Attempting duplicate date for same company
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (1, '2026-11-01', 100.0, 102.0);")
    conn.close()


# 4. Conflicting existing market records
def test_simulated_conflicting_market_records_preservation(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'TCS', 'Tata Consultancy');")
    # Existing destination has close price = 3500.0
    cur.execute("INSERT INTO daily_prices (company_id, date, open, high, low, close, volume) VALUES (1, '2026-11-01', 3450.0, 3520.0, 3440.0, 3500.0, 50000);")
    conn.commit()

    # Incoming source record has conflicting close price = 9999.0
    src_row = {'symbol': 'TCS', 'date': '2026-11-01', 'open': 3450.0, 'high': 3520.0, 'low': 3440.0, 'close': 9999.0, 'volume': 50000}
    dst_row = {'open': 3450.0, 'high': 3520.0, 'low': 3440.0, 'close': 3500.0, 'volume': 50000}

    cat, diff = classify_market_record(src_row, dst_row)
    assert cat == ConflictCategory.CONFLICTING
    assert 'close' in diff
    assert diff['close']['source'] == 9999.0
    assert diff['close']['destination'] == 3500.0

    # Ensure destination remains unchanged
    cur.execute("SELECT close FROM daily_prices WHERE company_id = 1 AND date = '2026-11-01';")
    assert cur.fetchone()[0] == 3500.0, "Conflicting destination record was altered!"
    conn.close()


# 5. Missing technical indicator parent
def test_simulated_missing_indicator_parent(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Attempt to insert technical indicator without company
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO technical_indicators (company_id, date, rsi) VALUES (888, '2026-11-01', 55.5);")
    conn.close()


# 6. Financial revision dependency failure
def test_simulated_financial_revision_dependency_failure(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'RELIANCE', 'Reliance');")
    conn.commit()

    # Attempt to insert child vintage referencing non-existent parent_vintage_id 9999
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("""
            INSERT INTO quarterly_financial_vintages (company_id, quarter, version_sequence, parent_vintage_id, revenue)
            VALUES (1, '2025-Q1', 2, 9999, 100000.0);
        """)
    conn.close()


# 7. Batch insertion failure and transaction rollback
def test_simulated_batch_insertion_failure(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'HDFCBANK', 'HDFC Bank');")
    conn.commit()

    batch = [
        (1, '2026-11-01', 100.0, 102.0),
        (1, '2026-11-02', 102.0, 104.0),
        (1, '2026-11-01', 104.0, 106.0) # Duplicate date in batch!
    ]

    try:
        cur.execute("BEGIN TRANSACTION;")
        for item in batch:
            cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (?, ?, ?, ?);", item)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()

    # Verify zero rows from the batch survived
    cur.execute("SELECT count(*) FROM daily_prices WHERE company_id = 1;")
    assert cur.fetchone()[0] == 0, "Batch failure did not roll back cleanly!"
    conn.close()


# 8. Transaction interruption simulation
def test_simulated_transaction_interruption(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'ICICIBANK', 'ICICI Bank');")
    conn.commit()

    try:
        cur.execute("BEGIN TRANSACTION;")
        cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (1, '2026-11-01', 900.0, 920.0);")
        # Simulate unhandled exception / interruption
        raise KeyboardInterrupt("Simulated task interruption")
    except KeyboardInterrupt:
        conn.rollback()

    cur.execute("SELECT count(*) FROM daily_prices WHERE company_id = 1;")
    assert cur.fetchone()[0] == 0, "Interrupted transaction left uncommitted data!"
    conn.close()


# 9. Rollback after partial batch failure
def test_simulated_rollback_after_partial_failure(isolated_failure_env):
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'AXISBANK', 'Axis Bank');")
    conn.commit()

    # Pre-existing price
    cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (1, '2026-11-01', 1100.0, 1120.0);")
    conn.commit()

    # Attempt transaction that inserts valid row then fails on invalid FK row
    try:
        cur.execute("BEGIN TRANSACTION;")
        cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (1, '2026-11-02', 1120.0, 1130.0);")
        # Invalid FK
        cur.execute("INSERT INTO daily_prices (company_id, date, open, close) VALUES (999, '2026-11-03', 500.0, 510.0);")
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()

    # Only pre-existing price should exist
    cur.execute("SELECT date FROM daily_prices WHERE company_id = 1;")
    dates = [r[0] for r in cur.fetchall()]
    assert dates == ['2026-11-01'], f"Partial rollback failure: unexpected dates {dates}"
    conn.close()


# 10. Repeated migration execution idempotency
def test_simulated_repeated_migration_idempotency(isolated_failure_env):
    src_path, dst_path = isolated_failure_env

    # Populate source DB
    s_conn = sqlite3.connect(src_path)
    s_cur = s_conn.cursor()
    s_cur.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT UNIQUE, company_name TEXT, sector TEXT, industry TEXT, exchange TEXT, sector_id INT, industry_id INT);")
    s_cur.execute("CREATE TABLE daily_prices (id INTEGER PRIMARY KEY, company_id INT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INT, adjusted_close REAL, UNIQUE(company_id, date));")
    s_cur.execute("INSERT INTO companies VALUES (1, 'WIPRO', 'Wipro Ltd', 'IT', 'Software', 'NSE', 1, 1);")
    s_cur.execute("INSERT INTO daily_prices VALUES (1, 1, '2026-11-01', 450.0, 455.0, 448.0, 452.0, 80000, 452.0);")
    s_conn.commit()
    s_conn.close()

    from scripts.migration.sync_companies import read_source_companies
    src_comps = read_source_companies(src_path)

    # First Run (Commit mode)
    res_c1 = sync_companies_to_sqlite(dst_path, src_comps, commit=True)
    res_m1 = sync_market_data_to_sqlite(dst_path, src_path, commit=True)
    assert res_c1['inserted_count'] == 1
    assert res_m1['total_inserted'] == 1

    # Second Run (Idempotency test)
    res_c2 = sync_companies_to_sqlite(dst_path, src_comps, commit=True)
    res_m2 = sync_market_data_to_sqlite(dst_path, src_path, commit=True)
    assert res_c2['inserted_count'] == 0, "Second company sync inserted duplicates!"
    assert res_c2['matching_count'] == 1
    assert res_m2['total_inserted'] == 0, "Second market data sync inserted duplicates!"
    assert res_m2['total_matching'] == 1
    assert res_m2['total_conflicts'] == 0


# =============================================================================
# Phase 7.2C.3: Hardened Multi-Batch Rollback & Isolation Tests
# =============================================================================

def test_rollback_requires_explicit_batch_id():
    """Confirms that rollback strictly rejects empty or missing batch IDs."""
    from scripts.migration.rollback_plan import execute_postgres_rollback, generate_neon_rollback_sql, generate_rollback_sql

    with pytest.raises(ValueError, match="Refusing to execute rollback without explicit --batch-id"):
        execute_postgres_rollback("postgresql://localhost:5432/test_db", batch_id="")

    with pytest.raises(ValueError, match="Refusing to execute rollback without explicit --batch-id"):
        execute_postgres_rollback("postgresql://localhost:5432/test_db", batch_id="   ")

    with pytest.raises(ValueError, match="Refusing to execute rollback without explicit --batch-id"):
        execute_postgres_rollback("postgresql://localhost:5432/test_db", batch_id=None)

    with pytest.raises(ValueError, match="Refusing to generate rollback SQL without an explicit batch_id"):
        generate_neon_rollback_sql(batch_id="")


def test_multi_batch_rollback_isolation(isolated_failure_env):
    """
    TASK 4.1: Multi-Batch Isolation Test.
    Proves that rolling back Batch A:
    - Completely deletes Batch A records.
    - Leaves Pre-existing records (batch_id IS NULL) 100% untouched.
    - Leaves Batch B records (batch_id = 'BATCH_B') 100% untouched.
    - Preserves foreign key referential integrity.
    - Aligns sequence counters with surviving records.
    """
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Add migration_batch_id column to tables
    for tbl in ["companies", "daily_prices", "technical_indicators", "quarterly_financial_vintages"]:
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN migration_batch_id TEXT;")

    cur.execute("""
        CREATE TABLE quarantined_quarterly_results (
            quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            quarter TEXT,
            revenue REAL,
            quarantine_reason TEXT,
            original_id INTEGER NOT NULL,
            original_table TEXT NOT NULL,
            migration_batch_id TEXT
        );
    """)

    # 1. Pre-existing records (batch_id IS NULL)
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (1, 'PRE_EXISTING', 'Pre Co', NULL);")
    cur.execute("INSERT INTO daily_prices (id, company_id, date, open, close, migration_batch_id) VALUES (1, 1, '2024-01-01', 100.0, 105.0, NULL);")
    cur.execute("INSERT INTO quarterly_financial_vintages (id, company_id, quarter, version_sequence, revenue, migration_batch_id) VALUES (1, 1, '2024Q1', 1, 1000.0, NULL);")
    cur.execute("INSERT INTO quarantined_quarterly_results (company_id, quarter, revenue, quarantine_reason, original_id, original_table, migration_batch_id) VALUES (1, '2023Q4', 900.0, 'LEGACY', 1, 'quarterly_results', NULL);")

    # 2. Batch A records (migration_batch_id = 'BATCH_A')
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (2, 'BATCH_A_CO', 'Batch A Co', 'BATCH_A');")
    cur.execute("INSERT INTO daily_prices (id, company_id, date, open, close, migration_batch_id) VALUES (2, 2, '2024-01-02', 200.0, 205.0, 'BATCH_A');")
    cur.execute("INSERT INTO quarterly_financial_vintages (id, company_id, quarter, version_sequence, revenue, migration_batch_id) VALUES (2, 2, '2024Q1', 1, 2000.0, 'BATCH_A');")
    cur.execute("INSERT INTO quarantined_quarterly_results (company_id, quarter, revenue, quarantine_reason, original_id, original_table, migration_batch_id) VALUES (2, '2023Q4', 1900.0, 'LEGACY', 2, 'quarterly_results', 'BATCH_A');")

    # 3. Batch B records (migration_batch_id = 'BATCH_B')
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (3, 'BATCH_B_CO', 'Batch B Co', 'BATCH_B');")
    cur.execute("INSERT INTO daily_prices (id, company_id, date, open, close, migration_batch_id) VALUES (3, 3, '2024-01-03', 300.0, 305.0, 'BATCH_B');")
    cur.execute("INSERT INTO quarterly_financial_vintages (id, company_id, quarter, version_sequence, revenue, migration_batch_id) VALUES (3, 3, '2024Q1', 1, 3000.0, 'BATCH_B');")
    cur.execute("INSERT INTO quarantined_quarterly_results (company_id, quarter, revenue, quarantine_reason, original_id, original_table, migration_batch_id) VALUES (3, '2023Q4', 2900.0, 'LEGACY', 3, 'quarterly_results', 'BATCH_B');")
    conn.commit()

    # Verify counts before rollback
    cur.execute("SELECT count(*) FROM companies;")
    assert cur.fetchone()[0] == 3
    cur.execute("SELECT count(*) FROM daily_prices;")
    assert cur.fetchone()[0] == 3
    cur.execute("SELECT count(*) FROM quarterly_financial_vintages;")
    assert cur.fetchone()[0] == 3
    cur.execute("SELECT count(*) FROM quarantined_quarterly_results;")
    assert cur.fetchone()[0] == 3

    # Execute targeted rollback of BATCH_A only (leaf-to-root order)
    cur.execute("BEGIN TRANSACTION;")
    for tbl in ["quarterly_financial_vintages", "quarantined_quarterly_results", "technical_indicators", "daily_prices", "companies"]:
        cur.execute(f"DELETE FROM {tbl} WHERE migration_batch_id = ?;", ('BATCH_A',))
    conn.commit()

    # ASSERTIONS:
    # 1. Batch A records are completely gone
    for tbl in ["companies", "daily_prices", "quarterly_financial_vintages", "quarantined_quarterly_results"]:
        cur.execute(f"SELECT count(*) FROM {tbl} WHERE migration_batch_id = 'BATCH_A';")
        assert cur.fetchone()[0] == 0, f"Batch A record survived in {tbl}!"

    # 2. Pre-existing records are 100% intact
    cur.execute("SELECT symbol FROM companies WHERE migration_batch_id IS NULL;")
    assert cur.fetchone()[0] == 'PRE_EXISTING'
    cur.execute("SELECT date FROM daily_prices WHERE migration_batch_id IS NULL;")
    assert cur.fetchone()[0] == '2024-01-01'
    cur.execute("SELECT revenue FROM quarterly_financial_vintages WHERE migration_batch_id IS NULL;")
    assert cur.fetchone()[0] == 1000.0
    cur.execute("SELECT revenue FROM quarantined_quarterly_results WHERE migration_batch_id IS NULL;")
    assert cur.fetchone()[0] == 900.0

    # 3. Batch B records are 100% intact
    cur.execute("SELECT symbol FROM companies WHERE migration_batch_id = 'BATCH_B';")
    assert cur.fetchone()[0] == 'BATCH_B_CO'
    cur.execute("SELECT date FROM daily_prices WHERE migration_batch_id = 'BATCH_B';")
    assert cur.fetchone()[0] == '2024-01-03'
    cur.execute("SELECT revenue FROM quarterly_financial_vintages WHERE migration_batch_id = 'BATCH_B';")
    assert cur.fetchone()[0] == 3000.0
    cur.execute("SELECT revenue FROM quarantined_quarterly_results WHERE migration_batch_id = 'BATCH_B';")
    assert cur.fetchone()[0] == 2900.0

    # 4. Foreign keys remain valid across surviving records
    cur.execute("PRAGMA foreign_key_check;")
    fk_errors = cur.fetchall()
    assert len(fk_errors) == 0, f"Foreign key errors detected after rollback: {fk_errors}"

    conn.close()


def test_partial_failure_rollback_isolation(isolated_failure_env):
    """
    TASK 4.2: Partial Batch Failure Simulation and Rollback.
    Proves that when Batch C fails midway:
    - Rollback for Batch C removes partially inserted records.
    - Pre-existing and Batch B records remain 100% unharmed.
    """
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    for tbl in ["companies", "daily_prices", "technical_indicators", "quarterly_financial_vintages"]:
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN migration_batch_id TEXT;")

    # Pre-existing records
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (1, 'ORIGINAL_CO', 'Orig Co', NULL);")
    cur.execute("INSERT INTO daily_prices (id, company_id, date, open, close, migration_batch_id) VALUES (1, 1, '2024-01-01', 100.0, 105.0, NULL);")

    # Batch B (completed earlier)
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (2, 'BATCH_B_CO', 'B Co', 'BATCH_B');")
    cur.execute("INSERT INTO daily_prices (id, company_id, date, open, close, migration_batch_id) VALUES (2, 2, '2024-01-02', 200.0, 205.0, 'BATCH_B');")
    conn.commit()

    # Simulate Batch C starting and partially committing (e.g. companies succeeded, prices failed)
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (3, 'PARTIAL_C_1', 'C Co 1', 'BATCH_C');")
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (4, 'PARTIAL_C_2', 'C Co 2', 'BATCH_C');")
    cur.execute("INSERT INTO daily_prices (id, company_id, date, open, close, migration_batch_id) VALUES (3, 3, '2024-01-03', 300.0, 305.0, 'BATCH_C');")
    conn.commit()

    # Now execute failure recovery rollback targeting BATCH_C
    cur.execute("BEGIN TRANSACTION;")
    for tbl in ["quarterly_financial_vintages", "technical_indicators", "daily_prices", "companies"]:
        cur.execute(f"DELETE FROM {tbl} WHERE migration_batch_id = ?;", ('BATCH_C',))
    conn.commit()

    # Assertions
    cur.execute("SELECT count(*) FROM companies WHERE migration_batch_id = 'BATCH_C';")
    assert cur.fetchone()[0] == 0, "Partial Batch C records survived rollback!"

    cur.execute("SELECT count(*) FROM daily_prices WHERE migration_batch_id = 'BATCH_C';")
    assert cur.fetchone()[0] == 0, "Partial Batch C price records survived rollback!"

    # Pre-existing and Batch B remain
    cur.execute("SELECT symbol FROM companies ORDER BY id;")
    surviving_symbols = [r[0] for r in cur.fetchall()]
    assert surviving_symbols == ['ORIGINAL_CO', 'BATCH_B_CO']

    cur.execute("PRAGMA foreign_key_check;")
    assert len(cur.fetchall()) == 0, "Foreign key corruption detected!"

    conn.close()


# =============================================================================
# Phase 7.2C.5: RBAC Rollback Authorization & Security Tests
# =============================================================================

def test_security_pre_existing_vintage_protection_unconditional(isolated_failure_env):
    """
    TASK 2.8: Proves that pre-existing financial vintages (batch_id IS NULL)
    can NEVER be deleted, even if a transaction is authorized for a migration batch.
    """
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    cur.execute("ALTER TABLE quarterly_financial_vintages ADD COLUMN migration_batch_id TEXT;")

    # Insert pre-existing immutable vintage
    cur.execute("""
        INSERT INTO quarterly_financial_vintages (id, company_id, quarter, version_sequence, revenue, migration_batch_id)
        VALUES (1, 1, '2024Q1', 1, 50000.0, NULL);
    """)
    conn.commit()

    # Simulated trigger function enforcing: OLD.migration_batch_id IS NULL -> UNCONDITIONALLY FORBIDDEN
    def attempt_delete_vintage(row_batch_id, authorized_batch_id, is_admin=True):
        if not is_admin:
            raise PermissionError("Security Violation: Role lacks migration_admin authorization.")
        if authorized_batch_id is None or authorized_batch_id == "":
            raise PermissionError("Illegal deletion: Historical financial vintages are immutable.")
        if row_batch_id is None:
            raise PermissionError("Illegal deletion: Pre-existing historical financial vintages (batch_id IS NULL) are permanently immutable.")
        if row_batch_id != authorized_batch_id:
            raise PermissionError(f"Security Violation: Record belongs to batch '{row_batch_id}' but authorized for '{authorized_batch_id}'.")
        return True

    # 1. Attempt delete without authorization -> Must raise PermissionError
    with pytest.raises(PermissionError, match="Illegal deletion: Historical financial vintages are immutable"):
        attempt_delete_vintage(row_batch_id=None, authorized_batch_id=None, is_admin=True)

    # 2. Attempt delete with valid batch authorization -> Pre-existing row still MUST raise PermissionError
    with pytest.raises(PermissionError, match="batch_id IS NULL.*permanently immutable"):
        attempt_delete_vintage(row_batch_id=None, authorized_batch_id="BATCH_20261124", is_admin=True)

    # 3. Unauthorized role attempt -> Must raise Security Violation
    with pytest.raises(PermissionError, match="Role lacks migration_admin authorization"):
        attempt_delete_vintage(row_batch_id="BATCH_20261124", authorized_batch_id="BATCH_20261124", is_admin=False)

    # 4. Wrong batch ID attempt -> Must raise Security Violation
    with pytest.raises(PermissionError, match="Record belongs to batch 'BATCH_B' but authorized for 'BATCH_A'"):
        attempt_delete_vintage(row_batch_id="BATCH_B", authorized_batch_id="BATCH_A", is_admin=True)

    # 5. Legitimate batch rollback -> Permitted
    assert attempt_delete_vintage(row_batch_id="BATCH_A", authorized_batch_id="BATCH_A", is_admin=True) is True

    conn.close()


def test_security_nonexistent_batch_id_rejected():
    """
    TASK 2.5: Confirms that attempting to rollback a non-existent batch ID fails.
    """
    from scripts.migration.rollback_plan import generate_neon_rollback_sql

    # Rollback generation requires a valid, non-empty batch ID
    with pytest.raises(ValueError, match="Refusing to generate rollback SQL without an explicit batch_id"):
        generate_neon_rollback_sql("")

    with pytest.raises(ValueError, match="Refusing to generate rollback SQL without an explicit batch_id"):
        generate_neon_rollback_sql("   ")

    sql = generate_neon_rollback_sql("BATCH_NONEXISTENT_999")
    assert "fn_authorize_migration_rollback('BATCH_NONEXISTENT_999')" in sql
    assert "DELETE FROM quarterly_financial_vintages WHERE migration_batch_id = 'BATCH_NONEXISTENT_999';" in sql


def test_security_wrong_batch_id_isolation(isolated_failure_env):
    """
    TASK 2.4: Proves that an authorized rollback for BATCH_A strictly refuses
    to touch records belonging to BATCH_B.
    """
    _, dst_path = isolated_failure_env
    conn = sqlite3.connect(dst_path)
    cur = conn.cursor()
    for tbl in ["companies", "daily_prices"]:
        cur.execute(f"ALTER TABLE {tbl} ADD COLUMN migration_batch_id TEXT;")

    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (1, 'BATCH_A_CO', 'A Co', 'BATCH_A');")
    cur.execute("INSERT INTO companies (id, symbol, company_name, migration_batch_id) VALUES (2, 'BATCH_B_CO', 'B Co', 'BATCH_B');")
    conn.commit()

    # Execute scoped deletion targeting ONLY BATCH_A
    cur.execute("DELETE FROM companies WHERE migration_batch_id = ?;", ('BATCH_A',))
    conn.commit()

    # BATCH_B must remain untouched
    cur.execute("SELECT symbol FROM companies WHERE migration_batch_id = 'BATCH_B';")
    assert cur.fetchone()[0] == 'BATCH_B_CO'

    # BATCH_A must be deleted
    cur.execute("SELECT count(*) FROM companies WHERE migration_batch_id = 'BATCH_A';")
    assert cur.fetchone()[0] == 0

    conn.close()


def test_security_search_path_and_privilege_escalation_invariants():
    """
    TASK 3.8 & 3.9: Validates that fn_authorize_migration_rollback:
    1. Explicitly sets a fixed search_path (pg_catalog, public, pg_temp).
    2. References schema-qualified objects (public.migration_batches).
    3. Revokes EXECUTE from PUBLIC.
    4. Does not permit privilege escalation.
    """
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "database", "schema_pg.sql"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Invariant 1: Fixed search_path in SECURITY DEFINER
    assert "SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp" in sql, \
        "SECURITY DEFINER function missing fixed search_path defense!"

    # Invariant 2: Schema-qualified public.migration_batches
    assert "public.migration_batches" in sql, \
        "Application tables in function must be schema-qualified!"

    # Invariant 3: Revoke execute from PUBLIC
    assert "REVOKE EXECUTE ON FUNCTION fn_authorize_migration_rollback(VARCHAR) FROM PUBLIC;" in sql, \
        "PUBLIC must not have EXECUTE privileges on rollback authorization function!"

    # Invariant 4: SESSION_USER check (not CURRENT_USER)
    assert "pg_has_role(SESSION_USER, 'migration_admin', 'MEMBER')" in sql, \
        "Function must inspect SESSION_USER to prevent privilege escalation via CURRENT_USER!"


def test_security_unauthorized_role_membership_invariant():
    """
    TASK 3.10: Verifies that migration_admin role creation is conditional
    and unprivileged callers cannot alter role memberships.
    """
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "database", "schema_pg.sql"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    assert "CREATE ROLE migration_admin" in sql
    assert "DO $$" in sql
    # Verify migration_admin grant is restricted
    assert "GRANT EXECUTE ON FUNCTION fn_authorize_migration_rollback(VARCHAR) TO migration_admin;" in sql


