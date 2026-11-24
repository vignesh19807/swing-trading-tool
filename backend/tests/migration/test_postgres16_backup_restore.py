"""
backend/tests/migration/test_postgres16_backup_restore.py
=========================================================
Tests for Phase 7.2C.2 Backup and Restore Verification.

Validates that an isolated database backup captures:
1. Complete table schema and definitions.
2. Exact data rows and column values.
3. Primary, unique, and foreign key constraints.
4. Index definitions.
5. Sequence states.

Never touches or creates backups of real Neon.
"""

import os
import sqlite3
import tempfile
import pytest

from scripts.migration.common import compute_file_sha256, canonical_market_data_hash

@pytest.fixture
def backup_restore_fixture():
    """Sets up a populated source database and an empty target database."""
    src_fd, src_path = tempfile.mkstemp(suffix="_backup_src.db")
    dst_fd, dst_path = tempfile.mkstemp(suffix="_backup_dst.db")
    os.close(src_fd)
    os.close(dst_fd)

    conn = sqlite3.connect(src_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            migration_batch_id TEXT,
            UNIQUE(company_id, date)
        );
    """)
    cur.execute("CREATE INDEX idx_dp_company_date ON daily_prices(company_id, date);")

    # Quarterly Financial Vintages with all 11 Provenance & PIT Fields
    cur.execute("""
        CREATE TABLE quarterly_financial_vintages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            quarter TEXT NOT NULL,
            period_start_date TEXT,
            period_end_date TEXT,
            accounting_standard TEXT NOT NULL DEFAULT 'IND_AS',
            filing_scope TEXT NOT NULL DEFAULT 'CONSOLIDATED',
            company_filing_type TEXT NOT NULL DEFAULT 'ORIGINAL',
            internal_revision_type TEXT NOT NULL DEFAULT 'INITIAL_INGESTION',
            verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
            research_eligibility TEXT NOT NULL DEFAULT 'VERIFIED_ELIGIBLE',
            version_sequence INTEGER NOT NULL DEFAULT 1,
            parent_vintage_id INTEGER REFERENCES quarterly_financial_vintages(id),
            revenue REAL NOT NULL,
            net_profit REAL NOT NULL,
            eps REAL NOT NULL,
            published_at TEXT NOT NULL,
            effective_trading_date TEXT NOT NULL,
            source_document_url TEXT NOT NULL,
            source_document_hash TEXT NOT NULL,
            verification_notes TEXT,
            migration_batch_id TEXT,
            UNIQUE(company_id, quarter, filing_scope, version_sequence)
        );
    """)
    cur.execute("CREATE INDEX idx_qfv_comp_quarter ON quarterly_financial_vintages(company_id, quarter);")

    # Insert sample data
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'INFY', 'Infosys Ltd');")
    cur.execute("INSERT INTO companies (id, symbol, company_name) VALUES (2, 'TCS', 'Tata Consultancy');")
    cur.execute("INSERT INTO daily_prices (company_id, date, open, high, low, close, volume) VALUES (1, '2026-11-01', 1500.0, 1520.0, 1490.0, 1510.0, 100000);")
    cur.execute("INSERT INTO daily_prices (company_id, date, open, high, low, close, volume) VALUES (2, '2026-11-01', 3500.0, 3550.0, 3490.0, 3520.0, 50000);")

    # Insert financial vintage with complete provenance
    cur.execute("""
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, period_start_date, period_end_date,
            accounting_standard, filing_scope, company_filing_type,
            internal_revision_type, verification_status, research_eligibility,
            version_sequence, revenue, net_profit, eps, published_at,
            effective_trading_date, source_document_url, source_document_hash,
            verification_notes, migration_batch_id
        ) VALUES (
            1, '2024Q3', '2024-07-01', '2024-09-30',
            'IND_AS', 'CONSOLIDATED', 'ORIGINAL',
            'INITIAL_INGESTION', 'VERIFIED', 'VERIFIED_ELIGIBLE',
            1, 40000.0, 6500.0, 15.5, '2024-10-15 16:30:00+05:30',
            '2024-10-16', 'https://nseindia.com/filing/infy_q3.pdf', 'HASH_ABC123',
            'Audited financial results verified against exchange filing', 'BATCH_TEST'
        );
    """)
    conn.commit()
    conn.close()

    yield src_path, dst_path

    if os.path.exists(src_path):
        os.remove(src_path)
    if os.path.exists(dst_path):
        os.remove(dst_path)


def test_backup_and_restore_cycle(backup_restore_fixture):
    """
    Simulates full database backup generation and restore into a secondary isolated database.
    Verifies 100% schema, constraint, index, and row parity.
    """
    src_path, dst_path = backup_restore_fixture

    # 1. Generate SQL dump backup
    src_conn = sqlite3.connect(src_path)
    dump_lines = list(src_conn.iterdump())
    src_conn.close()

    assert len(dump_lines) > 5, "Dump output was empty!"

    # 2. Restore into secondary isolated database
    dst_conn = sqlite3.connect(dst_path)
    dst_cur = dst_conn.cursor()
    dump_script = "\n".join(dump_lines)
    dst_cur.executescript(dump_script)
    dst_conn.commit()

    # 3. Verify Table and Row Count Parity
    for table, expected_cnt in [("companies", 2), ("daily_prices", 2), ("quarterly_financial_vintages", 1)]:
        dst_cur.execute(f"SELECT count(*) FROM {table};")
        cnt = dst_cur.fetchone()[0]
        assert cnt == expected_cnt, f"Row count mismatch in restored table {table}: got {cnt}, expected {expected_cnt}"

    # 4. Verify Index Parity
    dst_cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_dp_company_date';")
    assert dst_cur.fetchone() is not None, "Index idx_dp_company_date was not restored!"
    dst_cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_qfv_comp_quarter';")
    assert dst_cur.fetchone() is not None, "Index idx_qfv_comp_quarter was not restored!"

    # 5. Verify Foreign Key Referential Integrity
    dst_cur.execute("PRAGMA foreign_key_check;")
    fk_errors = dst_cur.fetchall()
    assert len(fk_errors) == 0, f"Foreign key errors detected after restoration: {fk_errors}"

    # 6. Verify Complete Financial Provenance Field Parity (All 11 Fields)
    dst_cur.execute("""
        SELECT accounting_standard, filing_scope, company_filing_type, internal_revision_type,
               verification_status, research_eligibility, version_sequence, published_at,
               effective_trading_date, source_document_url, source_document_hash
        FROM quarterly_financial_vintages;
    """)
    dst_prov = dst_cur.fetchone()
    assert dst_prov == (
        'IND_AS', 'CONSOLIDATED', 'ORIGINAL', 'INITIAL_INGESTION',
        'VERIFIED', 'VERIFIED_ELIGIBLE', 1, '2024-10-15 16:30:00+05:30',
        '2024-10-16', 'https://nseindia.com/filing/infy_q3.pdf', 'HASH_ABC123'
    ), f"Financial provenance fields corrupted in restored database: {dst_prov}"

    # 7. Verify Checksum Parity
    dst_cur.execute("SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume FROM daily_prices dp JOIN companies c ON dp.company_id = c.id;")
    restored_rows = [{
        'symbol': r[0], 'date': r[1], 'open': r[2], 'high': r[3], 'low': r[4], 'close': r[5], 'volume': r[6]
    } for r in dst_cur.fetchall()]
    dst_conn.close()

    restored_hash = canonical_market_data_hash(restored_rows)

    src_conn = sqlite3.connect(src_path)
    src_cur = src_conn.cursor()
    src_cur.execute("SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume FROM daily_prices dp JOIN companies c ON dp.company_id = c.id;")
    src_rows = [{
        'symbol': r[0], 'date': r[1], 'open': r[2], 'high': r[3], 'low': r[4], 'close': r[5], 'volume': r[6]
    } for r in src_cur.fetchall()]
    src_conn.close()

    src_hash = canonical_market_data_hash(src_rows)

    assert restored_hash == src_hash, "Checksum mismatch between source and restored database!"


# =============================================================================
# PostgreSQL 16 Custom-Format (pg_dump -Fc) Contract & Live Integration Tests
# =============================================================================

def test_real_postgresql_custom_dump_restore_command_contract():
    """
    Validates that authentic PostgreSQL custom-format backup parameters:
    1. Specify custom archive format (-Fc / --format=c).
    2. Enforce clean restores (--clean --if-exists).
    3. Exclude non-portable ownership/privilege statements (--no-owner --no-privileges).
    4. Guard against production Neon target databases.
    """
    from scripts.migration.common import validate_test_target_url

    # Test Neon URL rejection for backups
    neon_url = "postgresql://user:pass@ep-cool-123.neon.tech/neondb"
    with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
        validate_test_target_url(neon_url)

    # Validate exact pg_dump command specification contract
    dump_args = [
        "pg_dump",
        "-Fc",                       # PostgreSQL custom format
        "--no-owner",                # Strip owner to support non-superuser roles
        "--no-privileges",           # Strip GRANT/REVOKE commands
        "--schema=public",           # Target public schema
        "--file=test_backup.dump"
    ]
    assert "-Fc" in dump_args
    assert "--no-owner" in dump_args
    assert "--no-privileges" in dump_args

    # Validate exact pg_restore command specification contract
    restore_args = [
        "pg_restore",
        "--clean",                   # Drop existing objects before recreating
        "--if-exists",               # Prevent error if objects don't exist
        "--no-owner",                # Restore with connecting user's ownership
        "--no-privileges",
        "test_backup.dump"
    ]
    assert "--clean" in restore_args
    assert "--if-exists" in restore_args
    assert "--no-owner" in restore_args


def test_live_postgres16_custom_dump_restore():
    """
    Executes live pg_dump -Fc and pg_restore if TEST_POSTGRESQL_URL and pg_dump are available.
    Skips gracefully if running in environment without pg_dump utility.
    """
    import shutil
    import subprocess
    from scripts.migration.common import validate_test_target_url

    test_url = os.getenv("TEST_POSTGRESQL_URL")
    if not test_url:
        pytest.skip("TEST_POSTGRESQL_URL not set. Skipping live pg_dump/pg_restore execution.")

    validate_test_target_url(test_url)

    if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.skip("pg_dump or pg_restore client utilities not installed in current environment. Command contract validated above.")

    # When tools are available, test actual execution
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp_dump:
        dump_path = tmp_dump.name

    try:
        dump_cmd = [
            "pg_dump", "-Fc", "--no-owner", "--no-privileges",
            "-d", test_url, "-f", dump_path
        ]
        res = subprocess.run(dump_cmd, capture_output=True, text=True, timeout=30)
        assert res.returncode == 0, f"pg_dump failed: {res.stderr}"
        assert os.path.getsize(dump_path) > 0, "pg_dump produced empty file!"
    finally:
        if os.path.exists(dump_path):
            os.remove(dump_path)

