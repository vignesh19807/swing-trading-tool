"""
PostgreSQL 16 Schema, Immutability Triggers, and Migration Integration Tests
============================================================================
Tests the PostgreSQL 16 schema definition and deterministic migration framework:
1. Migration CLI safety gates and dry-run validation (portable unit tests).
2. Production database access rejection safeguards (portable unit tests).
3. Topological table ordering and sequence logic (portable unit tests).
4. Live PostgreSQL 16 schema creation, foreign keys, unique constraints,
   and PL/pgSQL immutability triggers (runs when TEST_POSTGRESQL_URL is configured).

If a local or test PostgreSQL instance is unavailable, live PostgreSQL tests are
strictly reported as SKIPPED / NOT RUN, adhering to Phase 5.3.2 requirements.
"""

import os
import tempfile
import sqlite3
import uuid
from typing import Optional
import pytest
from pathlib import Path

from backend.config import PROJECT_ROOT
from backend.database.connection import (
    DatabaseEngine,
    open_db_connection,
    get_db_connection,
    mask_database_url,
    reset_db_pool,
)
from backend.database.migrate_sqlite_to_pg import (
    migrate_sqlite_to_postgres,
    TABLES_TOPOLOGICAL_ORDER,
)
from backend.database.verify_pg_migration import (
    verify_migration,
    _compute_table_checksum,
)

SCHEMA_PG_PATH = PROJECT_ROOT / "backend" / "database" / "schema_pg.sql"


@pytest.fixture(autouse=True)
def clean_pool():
    reset_db_pool()
    yield
    reset_db_pool()


# =============================================================================
# 1. Migration Framework Safety & Dry-Run Tests (Portable)
# =============================================================================

def test_migration_framework_defaults_to_dry_run():
    """Verifies that migration defaults to dry-run and does not mutate without --confirm."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = Path(tf.name)

    try:
        conn = sqlite3.connect(temp_path)
        conn.execute("CREATE TABLE sectors (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)")
        conn.execute("INSERT INTO sectors VALUES (1, 'Energy'), (2, 'Technology')")
        conn.commit()
        conn.close()

        res = migrate_sqlite_to_postgres(
            source_sqlite_path=temp_path,
            target_pg_url="postgresql://mock_user:mock_pass@127.0.0.1:5432/mock_db",
            dry_run=True,
            confirm=False,
        )

        assert res.is_dry_run is True
        assert res.success is True
        assert res.tables_migrated.get("sectors") == 2
        # Credentials must be masked in report
        assert "mock_pass" not in res.masked_target_url
        assert "mock_user:***@127.0.0.1" in res.masked_target_url
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def test_production_database_rejection_guard():
    """Verifies that production database swing_trading.db is rejected without --allow-production."""
    prod_path = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()
    created = False
    if not prod_path.exists():
        prod_path.parent.mkdir(parents=True, exist_ok=True)
        prod_path.touch()
        created = True
    try:
        res = migrate_sqlite_to_postgres(
            source_sqlite_path=prod_path,
            target_pg_url="postgresql://usr:pwd@localhost:5432/db",
            dry_run=False,
            confirm=True,
            allow_production=False,
        )

        assert res.success is False
        assert any("CRITICAL REJECTION" in err for err in res.errors)
    finally:
        if created and prod_path.exists():
            prod_path.unlink()


def test_topological_table_order_integrity():
    """Verifies that foreign-key dependency hierarchy is strictly preserved."""
    assert TABLES_TOPOLOGICAL_ORDER[0] == "sectors"
    assert TABLES_TOPOLOGICAL_ORDER[1] == "industries"
    assert TABLES_TOPOLOGICAL_ORDER[2] == "companies"
    # Dependent tables must follow companies
    comp_idx = TABLES_TOPOLOGICAL_ORDER.index("companies")
    assert TABLES_TOPOLOGICAL_ORDER.index("daily_prices") > comp_idx
    assert TABLES_TOPOLOGICAL_ORDER.index("technical_indicators") > comp_idx
    assert TABLES_TOPOLOGICAL_ORDER.index("quarterly_results") > comp_idx
    assert TABLES_TOPOLOGICAL_ORDER.index("quarterly_financial_vintages") > comp_idx
    # Backtest dependencies
    runs_idx = TABLES_TOPOLOGICAL_ORDER.index("backtest_runs")
    assert TABLES_TOPOLOGICAL_ORDER.index("backtest_results") > runs_idx
    assert TABLES_TOPOLOGICAL_ORDER.index("backtest_trades") > runs_idx
    assert TABLES_TOPOLOGICAL_ORDER.index("backtest_equity_curve") > runs_idx


def test_schema_sql_file_syntax_and_completeness():
    """Validates that schema_pg.sql exists and defines all 15 expected tables and 3 triggers."""
    assert SCHEMA_PG_PATH.exists()
    content = SCHEMA_PG_PATH.read_text(encoding="utf-8")

    # Verify all 15 tables defined
    for table in TABLES_TOPOLOGICAL_ORDER:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in content, f"Missing table definition for: {table}"

    # Verify PL/pgSQL triggers defined
    assert "CREATE OR REPLACE FUNCTION trg_fn_prevent_vintage_deletion()" in content
    assert "CREATE OR REPLACE FUNCTION trg_fn_prevent_vintage_financial_mutation()" in content
    assert "CREATE OR REPLACE FUNCTION trg_fn_prevent_extraction_restatement_conflation()" in content
    assert "CREATE TRIGGER trg_prevent_vintage_deletion" in content
    assert "CREATE TRIGGER trg_prevent_vintage_financial_mutation" in content
    assert "CREATE TRIGGER trg_prevent_extraction_restatement_conflation" in content


# =============================================================================
# 2. Live PostgreSQL 16 Integration Tests (Conditional / Skip Reporting)
# =============================================================================

def _get_live_pg_url() -> Optional[str]:
    return os.getenv("TEST_POSTGRESQL_URL")


@pytest.mark.skipif(
    not _get_live_pg_url(),
    reason="NOT RUN: PostgreSQL test server not configured (set TEST_POSTGRESQL_URL to enable live integration tests)",
)
def test_postgresql_live_schema_creation():
    """Applies schema_pg.sql to a live PostgreSQL test database."""
    pg_url = _get_live_pg_url()
    with open_db_connection(pg_url) as conn:
        assert conn.engine == DatabaseEngine.POSTGRESQL
        cur = conn.cursor()
        sql_text = SCHEMA_PG_PATH.read_text(encoding="utf-8")
        cur.raw_cursor.execute(sql_text)
        conn.commit()

        # Check tables in information_schema
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = {r["table_name"] for r in cur.fetchall()}
        for t in TABLES_TOPOLOGICAL_ORDER:
            assert t in tables, f"Table {t} missing in PostgreSQL target"


@pytest.mark.skipif(
    not _get_live_pg_url(),
    reason="NOT RUN: PostgreSQL test server not configured (set TEST_POSTGRESQL_URL to enable live integration tests)",
)
def test_postgresql_live_immutability_triggers():
    """
    Tests that PostgreSQL PL/pgSQL triggers strictly reject:
    - DELETE on quarterly_financial_vintages
    - UPDATE on core financials (revenue, profit, timestamps)
    - Insertion of unverified vintages as VERIFIED_ELIGIBLE
    - Conflation of internal fixes with corporate restatements
    """
    pg_url = _get_live_pg_url()
    with open_db_connection(pg_url) as conn:
        cur = conn.cursor()

        # Ensure seed company exists
        cur.execute("INSERT INTO sectors (name) VALUES ('Test Sector') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM sectors WHERE name = 'Test Sector'")
        s_id = cur.fetchone()["id"]

        cur.execute(
            "INSERT INTO companies (symbol, company_name, sector_id) "
            "VALUES ('TEST_TRIG', 'Trigger Test Corp', %s) "
            "ON CONFLICT (symbol) DO UPDATE SET company_name = EXCLUDED.company_name RETURNING id",
            (s_id,),
        )
        c_id = cur.fetchone()["id"]
        conn.commit()

        # 1. Permitted insertion
        bc_id_1 = f"BC_{uuid.uuid4().hex[:8]}"
        cur.execute(
            """
            INSERT INTO quarterly_financial_vintages (
                company_id, quarter, period_start_date, period_end_date,
                company_filing_type, internal_revision_type, verification_status,
                research_eligibility, exchange, exchange_broadcast_id,
                published_at, effective_trading_date, revenue, net_profit, eps,
                source_document_url, source_document_hash
            ) VALUES (
                %s, '2025-Q1', '2025-01-01', '2025-03-31',
                'ORIGINAL', 'INITIAL_INGESTION', 'PROVISIONAL',
                'PROVISIONAL_DEMO', 'NSE', %s,
                '2025-04-15 18:30:00+00', '2025-04-16', 5000.0, 750.0, 15.5,
                'https://nseindia.com/doc1', 'hash001'
            ) RETURNING id
            """,
            (c_id, bc_id_1),
        )
        v_id = cur.fetchone()["id"]
        conn.commit()

        # 2. Rejection of prohibited DELETE
        with pytest.raises(Exception) as exc_del:
            cur.execute("DELETE FROM quarterly_financial_vintages WHERE id = %s", (v_id,))
        conn.rollback()
        assert "Historical financial vintages are immutable and cannot be deleted" in str(exc_del.value)

        # 3. Rejection of prohibited UPDATE on financial figures
        with pytest.raises(Exception) as exc_upd:
            cur.execute(
                "UPDATE quarterly_financial_vintages SET revenue = 6000.0 WHERE id = %s",
                (v_id,),
            )
        conn.rollback()
        assert "Financial figures and publication timestamps are immutable" in str(exc_upd.value)

        # 4. Rejection of semantic conflation on INSERT
        bc_id_2 = f"BC_{uuid.uuid4().hex[:8]}"
        with pytest.raises(Exception) as exc_conflation:
            cur.execute(
                """
                INSERT INTO quarterly_financial_vintages (
                    company_id, quarter, period_start_date, period_end_date,
                    company_filing_type, internal_revision_type, verification_status,
                    research_eligibility, exchange, exchange_broadcast_id,
                    published_at, effective_trading_date, revenue, net_profit, eps,
                    source_document_url, source_document_hash
                ) VALUES (
                    %s, '2025-Q2', '2025-04-01', '2025-06-30',
                    'CORPORATE_RESTATEMENT', 'EXTRACTION_CORRECTION', 'PROVISIONAL',
                    'PROVISIONAL_DEMO', 'NSE', %s,
                    '2025-07-15 18:30:00+00', '2025-07-16', 5500.0, 800.0, 16.0,
                    'https://nseindia.com/doc2', 'hash002'
                )
                """,
                (c_id, bc_id_2),
            )
        conn.rollback()
        assert "Semantic Conflation Error" in str(exc_conflation.value)

        # 5. Rejection of unverified promotion to VERIFIED_ELIGIBLE
        with pytest.raises(Exception) as exc_promo:
            cur.execute(
                """
                INSERT INTO quarterly_financial_vintages (
                    company_id, quarter, period_start_date, period_end_date,
                    company_filing_type, internal_revision_type, verification_status,
                    research_eligibility, exchange, exchange_broadcast_id,
                    published_at, effective_trading_date, revenue, net_profit, eps,
                    source_document_url, source_document_hash
                ) VALUES (
                    %s, '2025-Q3', '2025-07-01', '2025-09-30',
                    'ORIGINAL', 'INITIAL_INGESTION', 'PROVISIONAL',
                    'VERIFIED_ELIGIBLE', 'NSE', 'BC_TEST_003',
                    '2025-10-15 18:30:00+00', '2025-10-16', 5600.0, 810.0, 16.5,
                    'https://nseindia.com/doc3', 'hash003'
                )
                """,
                (c_id,),
            )
        conn.rollback()
        assert "Integrity Error: Cannot insert VERIFIED_ELIGIBLE vintage without verification_status = VERIFIED" in str(exc_promo.value)

        # 6. Rejection of self-supersession
        with pytest.raises(Exception) as exc_self:
            cur.execute(
                """
                UPDATE quarterly_financial_vintages
                SET superseded_by_vintage_id = %s
                WHERE id = %s
                """,
                (v_id, v_id),
            )
        conn.rollback()
        assert "Illegal lineage" in str(exc_self.value) or "check constraint" in str(exc_self.value).lower()


@pytest.mark.skipif(
    not _get_live_pg_url(),
    reason="NOT RUN: PostgreSQL test server not configured (set TEST_POSTGRESQL_URL to enable live integration tests)",
)
def test_postgresql_live_deterministic_migration_and_verification():
    """
    Tests live end-to-end migration from an isolated SQLite database fixture
    into the live PostgreSQL test database, followed by automated checksum verification.
    """
    pg_url = _get_live_pg_url()

    # Reset test database schema to ensure isolated clean migration test
    with open_db_connection(pg_url) as conn:
        cur = conn.cursor()
        for t in reversed(TABLES_TOPOLOGICAL_ORDER):
            cur.raw_cursor.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")
        conn.commit()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        sqlite_test_path = Path(tf.name)

    try:
        # Create small multi-table fixture in SQLite
        conn = sqlite3.connect(sqlite_test_path)
        conn.execute("CREATE TABLE sectors (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)")
        conn.execute("INSERT INTO sectors VALUES (1, 'Energy'), (2, 'Technology')")
        conn.execute(
            "CREATE TABLE industries (id INTEGER PRIMARY KEY, name TEXT NOT NULL, sector_id INTEGER NOT NULL)"
        )
        conn.execute("INSERT INTO industries VALUES (1, 'Software', 2), (2, 'Refineries', 1)")
        conn.execute(
            """
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                symbol TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                sector TEXT,
                industry TEXT,
                exchange TEXT NOT NULL,
                sector_id INTEGER,
                industry_id INTEGER,
                is_active INTEGER DEFAULT 1,
                status TEXT DEFAULT 'ACTIVE',
                listing_date TEXT,
                created_at TEXT,
                updated_at TEXT,
                source TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO companies (id, symbol, company_name, exchange, sector_id, industry_id) "
            "VALUES (10, 'LIVE_TEST', 'Live Test Company', 'NSE', 2, 1)"
        )
        conn.commit()
        conn.close()

        # Execute migration with --confirm
        res = migrate_sqlite_to_postgres(
            source_sqlite_path=sqlite_test_path,
            target_pg_url=pg_url,
            dry_run=False,
            confirm=True,
            allow_production=False,
        )

        assert res.success is True
        assert res.tables_migrated["sectors"] == 2
        assert res.tables_migrated["industries"] == 2
        assert res.tables_migrated["companies"] == 1

        # Verify automated checksum verification ran and passed
        assert res.verification is not None
        assert res.verification["is_valid"] is True
        assert res.verification["table_results"]["companies"]["rows_match"] is True
        assert res.verification["table_results"]["companies"]["checksum_matches"] is True

    finally:
        if sqlite_test_path.exists():
            try:
                sqlite_test_path.unlink()
            except OSError:
                pass

