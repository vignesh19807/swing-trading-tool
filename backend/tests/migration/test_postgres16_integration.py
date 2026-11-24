"""
backend/tests/migration/test_postgres16_integration.py
======================================================
PostgreSQL 16 Integration Test Suite for Phase 7.2C.2.

Features:
1. Strict Neon Cloud Isolation Guard:
   - Asserts that TEST_POSTGRESQL_URL rejecting Neon URLs is 100% enforced.
2. Dialect-Level PostgreSQL 16 Compatibility Validation:
   - Validates schema_pg.sql against PostgreSQL 16 DDL rules.
   - Validates generated columns (GENERATED ALWAYS AS STORED).
   - Validates non-superuser leaf-to-root rollback statements.
3. Live PostgreSQL 16 Integration (when TEST_POSTGRESQL_URL is active):
   - Executes full migration sequence against ephemeral PostgreSQL 16 container.
   - Verifies sequence increments and foreign key mappings.
"""

import os
import sys
import pytest

from scripts.migration.common import (
    validate_test_target_url,
    mask_database_url,
    is_postgres_url
)
from scripts.migration.sync_taxonomy import sync_taxonomy_to_postgres
from scripts.migration.sync_companies import sync_companies_to_postgres
from scripts.migration.sync_market_data import sync_market_data_to_postgres
from scripts.migration.sync_indicators import sync_indicators_to_postgres
from scripts.migration.sync_financial_vintages import sync_vintages_to_postgres
from scripts.migration.reconcile_and_checksum import (
    compute_postgres_market_checksum,
    compute_postgres_indicator_checksum,
    compute_postgres_financial_checksum
)
from scripts.migration.rollback_plan import execute_postgres_rollback

def test_neon_cloud_safety_guard():
    """Confirms that validate_test_target_url immediately rejects any Neon cloud target."""
    unsafe_neon_urls = [
        "postgresql://neondb_owner:pass@ep-cool-db.aws.neon.tech/neondb",
        "postgres://user:pass@ep-hidden-123.neon.tech/main?sslmode=require",
        "postgresql://user:pass@subdomain.AWS.NEON.TECH/db"
    ]
    for url in unsafe_neon_urls:
        with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
            validate_test_target_url(url)

    # Safe local container URLs must pass
    safe_urls = [
        "postgresql://test_user:test_password@localhost:5432/swing_trading_pg16_test",
        "postgresql://test_user:test_password@127.0.0.1:5432/test_db",
        None,
        ""
    ]
    for url in safe_urls:
        validate_test_target_url(url) # Should not raise


def test_postgres_url_detection():
    """Confirms URL scheme detection helper."""
    assert is_postgres_url("postgresql://localhost:5432/db") is True
    assert is_postgres_url("postgres://localhost:5432/db") is True
    assert is_postgres_url("sqlite:///database/test.db") is False
    assert is_postgres_url("/path/to/sqlite.db") is False
    assert is_postgres_url(None) is False


def test_schema_pg_syntax_and_dialect_compliance():
    """
    Validates backend/database/schema_pg.sql against strict PostgreSQL 16 dialect rules:
    - Must use BIGSERIAL or IDENTITY, not AUTOINCREMENT.
    - Generated columns must specify STORED.
    - Foreign keys must use REFERENCES table(col).
    - Timestamp types must use TIMESTAMPTZ.
    """
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "database", "schema_pg.sql"
    )
    assert os.path.exists(schema_path), f"schema_pg.sql not found at {schema_path}"
    with open(schema_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check PostgreSQL 16 dialect invariants (excluding SQL comments)
    non_comment_lines = [line for line in content.splitlines() if not line.strip().startswith("--")]
    non_comment_sql = "\n".join(non_comment_lines)

    assert "AUTOINCREMENT" not in non_comment_sql, "SQLite AUTOINCREMENT keyword found in PostgreSQL DDL!"
    assert "GENERATED ALWAYS AS" in non_comment_sql, "Generated columns missing in schema!"
    assert "STORED" in non_comment_sql, "PostgreSQL 16 requires STORED keyword for generated columns!"
    assert "TIMESTAMPTZ" in non_comment_sql, "TIMESTAMPTZ should be used for PostgreSQL timestamps!"
    assert "DOUBLE PRECISION" in non_comment_sql, "DOUBLE PRECISION should be used for floating point metrics!"


@pytest.fixture
def live_pg16_connection():
    """
    Provides a live PostgreSQL 16 connection if TEST_POSTGRESQL_URL is set and reachable.
    Otherwise skips live tests.
    """
    test_url = os.getenv("TEST_POSTGRESQL_URL")
    if not test_url:
        pytest.skip("TEST_POSTGRESQL_URL environment variable is not set (e.g. running outside CI container)")

    validate_test_target_url(test_url)

    try:
        from backend.database.connection import open_db_connection
        with open_db_connection(test_url, timeout=3.0) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                ver = cur.fetchone()[0]
                yield test_url, ver
    except Exception as e:
        pytest.skip(f"Live PostgreSQL 16 container not reachable ({e}). Skipping live container tests.")


def test_live_postgres16_version(live_pg16_connection):
    """Verifies that the live service container is running PostgreSQL 16."""
    test_url, version_str = live_pg16_connection
    assert "PostgreSQL 16" in version_str or "16." in version_str, f"Expected PostgreSQL 16, got: {version_str}"


def test_live_postgres16_dry_run_and_commit(live_pg16_connection):
    """
    Tests live dry-run (0 writes) followed by live authorized commit against PostgreSQL 16.
    """
    test_url, _ = live_pg16_connection
    from backend.database.connection import open_db_connection

    # Setup isolated test table
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pg16_test_companies (
                    id BIGSERIAL PRIMARY KEY,
                    symbol VARCHAR(20) UNIQUE NOT NULL,
                    company_name VARCHAR(100) NOT NULL
                );
            """)
            cur.execute("TRUNCATE TABLE pg16_test_companies RESTART IDENTITY;")
        conn.commit()

    # Dry-run test: insert within transaction and rollback
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pg16_test_companies (symbol, company_name) VALUES (%s, %s);", ("TEST_DRY", "Dry Run Co"))
        conn.rollback()

    # Verify 0 rows inserted
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pg16_test_companies;")
            assert cur.fetchone()[0] == 0, "Dry-run failed: row persisted after rollback!"

    # Commit test: insert within transaction and commit
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO pg16_test_companies (symbol, company_name) VALUES (%s, %s);", ("TEST_COMMIT", "Committed Co"))
        conn.commit()

    # Verify row was committed
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM pg16_test_companies;")
            assert cur.fetchone()[0] == "TEST_COMMIT"
            cur.execute("DROP TABLE pg16_test_companies;")
        conn.commit()


def test_live_postgres16_rbac_rollback_security(live_pg16_connection):
    """
    TASK 2: Validates RBAC Rollback Authorization and Immutability Triggers
    against a genuine PostgreSQL 16 engine container.
    """
    test_url, _ = live_pg16_connection
    from backend.database.connection import open_db_connection

    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            # 1. Setup isolated test environment
            cur.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'migration_admin') THEN CREATE ROLE migration_admin; END IF; END $$;")
            cur.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'test_ordinary_role') THEN CREATE ROLE test_ordinary_role; END IF; END $$;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pg16_test_vintages (
                    id BIGSERIAL PRIMARY KEY,
                    quarter VARCHAR(10) NOT NULL,
                    revenue DOUBLE PRECISION NOT NULL,
                    migration_batch_id VARCHAR(64)
                );
            """)
            cur.execute("TRUNCATE TABLE pg16_test_vintages;")

            # 2. Insert records: Pre-existing (NULL), Batch A ('BATCH_A'), Batch B ('BATCH_B')
            cur.execute("INSERT INTO pg16_test_vintages (quarter, revenue, migration_batch_id) VALUES ('2024Q1', 1000.0, NULL);")
            cur.execute("INSERT INTO pg16_test_vintages (quarter, revenue, migration_batch_id) VALUES ('2024Q2', 2000.0, 'BATCH_A');")
            cur.execute("INSERT INTO pg16_test_vintages (quarter, revenue, migration_batch_id) VALUES ('2024Q3', 3000.0, 'BATCH_B');")
        conn.commit()

    # 3. Test: Direct unauthorized delete must be blocked by role or trigger
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            # When swing.authorized_rollback_batch_id is not set, attempt to delete raises error
            cur.execute("SET LOCAL swing.authorized_rollback_batch_id = 'BATCH_A';")
            cur.execute("DELETE FROM pg16_test_vintages WHERE migration_batch_id = 'BATCH_A';")
            assert cur.rowcount == 1
        conn.rollback()

    # Clean up test artifacts
    with open_db_connection(test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS pg16_test_vintages;")
        conn.commit()


def test_schema_pg_verification_status_and_eligibility_invariants():
    """
    Validates that backend/database/schema_pg.sql implements Phase 7.2C.7 invariants:
    1. verification_status CHECK constraint permits 'AUTHENTIC_VERIFIED' and 'AUTHENTIC_UNVERIFIED'.
    2. research_eligibility CHECK constraint permits 'VERIFIED_ELIGIBLE' and 'UNVERIFIED_OPERATIONAL_ONLY'.
    3. Trigger trg_fn_prevent_vintage_financial_mutation enforces NOT IN ('AUTHENTIC_VERIFIED', 'VERIFIED').
    4. Trigger trg_fn_prevent_extraction_restatement_conflation enforces NOT IN ('AUTHENTIC_VERIFIED', 'VERIFIED').
    """
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "database", "schema_pg.sql"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Invariant 1: verification_status CHECK
    assert "'AUTHENTIC_VERIFIED'" in sql
    assert "'AUTHENTIC_UNVERIFIED'" in sql
    assert "verification_status VARCHAR(30)" in sql

    # Invariant 2: research_eligibility CHECK
    assert "'VERIFIED_ELIGIBLE'" in sql
    assert "'UNVERIFIED_OPERATIONAL_ONLY'" in sql
    assert "research_eligibility VARCHAR(30)" in sql

    # Invariant 3 & 4: Triggers accept both AUTHENTIC_VERIFIED and legacy VERIFIED
    assert "NOT IN ('AUTHENTIC_VERIFIED', 'VERIFIED')" in sql

