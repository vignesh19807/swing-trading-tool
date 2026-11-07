"""
Unit and Integration Tests for Centralized Database Access Layer (DAL)
====================================================================
Tests the database connection interface in backend/database/connection.py:
- SQLite connection creation (default, explicit path, in-memory)
- PostgreSQL connection configuration parsing and credentials masking
- Invalid DATABASE_URL scheme rejection
- Connection lifecycle and automatic resource cleanup
- Transaction commit behavior
- Transaction rollback on exception
- Parameterized queries and SQL injection resistance
- Placeholder adaptation (? vs %s)
- PostgreSQL DbRow proxy dictionary and tuple indexing
- Database isolation between test instances
- Safe reporting of unconfigured PostgreSQL live integration tests (NOT RUN)
"""

import os
import tempfile
import sqlite3
import pytest
from pathlib import Path

from backend.database.connection import (
    DatabaseEngine,
    DatabaseConfig,
    DatabaseError,
    DatabaseConfigurationError,
    DatabaseConnectionError,
    DatabaseQueryError,
    parse_database_url,
    mask_database_url,
    get_db_connection,
    get_db_cursor,
    open_db_connection,
    reset_db_pool,
    DbRow,
    _adapt_query_placeholders,
)


@pytest.fixture(autouse=True)
def cleanup_pool_state():
    """Ensures clean pool state before and after each test."""
    reset_db_pool()
    yield
    reset_db_pool()


# =============================================================================
# 1. SQLite Connection Creation Tests
# =============================================================================

def test_sqlite_connection_creation_default():
    """Verifies that default configuration without DATABASE_URL resolves to SQLite."""
    old_env = os.environ.pop("DATABASE_URL", None)
    try:
        config = parse_database_url()
        assert config.engine == DatabaseEngine.SQLITE
        assert config.is_sqlite is True
        assert config.is_postgresql is False
        assert config.db_path is not None
        assert "swing_trading.db" in str(config.db_path)
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env


def test_sqlite_connection_creation_explicit_path():
    """Verifies explicit SQLite path configuration."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = tf.name

    try:
        config = parse_database_url(temp_path)
        assert config.engine == DatabaseEngine.SQLITE
        assert config.db_path == Path(temp_path).resolve()
        assert config.raw_url.startswith("sqlite:///")

        with get_db_connection(temp_path) as conn:
            assert conn.engine == DatabaseEngine.SQLITE
            cur = conn.execute("CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, val TEXT)")
            cur.execute("INSERT INTO test_tbl (val) VALUES (?)", ("alpha",))
            conn.commit()

        # Reopen and verify persistence
        with get_db_cursor(temp_path) as cur:
            cur.execute("SELECT val FROM test_tbl WHERE id = ?", (1,))
            row = cur.fetchone()
            assert row is not None
            assert row["val"] == "alpha"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_sqlite_connection_in_memory():
    """Verifies in-memory SQLite connection configuration."""
    config = parse_database_url("sqlite:///:memory:")
    assert config.engine == DatabaseEngine.SQLITE
    assert config.db_path is None

    with get_db_connection("sqlite:///:memory:") as conn:
        conn.execute("CREATE TABLE mem_tbl (key TEXT, score REAL)")
        conn.execute("INSERT INTO mem_tbl VALUES (?, ?)", ("metric_1", 98.5))
        conn.commit()

        cur = conn.execute("SELECT score FROM mem_tbl WHERE key = ?", ("metric_1",))
        row = cur.fetchone()
        assert row["score"] == 98.5


# =============================================================================
# 2. PostgreSQL Configuration & Credentials Masking
# =============================================================================

def test_postgresql_connection_configuration_valid():
    """Verifies parsing of PostgreSQL URLs and credential masking."""
    secret_pass = "SuperSecret_P@ss#123"
    raw_url = f"postgresql://app_user:{secret_pass}@ep-twilight-456.us-east-2.neon.tech:5432/swing_db?sslmode=require"

    config = parse_database_url(raw_url)
    assert config.engine == DatabaseEngine.POSTGRESQL
    assert config.is_postgresql is True
    assert config.is_sqlite is False
    assert config.raw_url == raw_url

    # Strict credentials masking validation
    assert secret_pass not in config.masked_url
    assert secret_pass not in repr(config)
    assert "app_user:***@ep-twilight-456.us-east-2.neon.tech" in config.masked_url


def test_postgresql_postgres_scheme_alias():
    """Verifies that postgres:// scheme alias is parsed identically to postgresql://."""
    raw_url = "postgres://usr:pwd@localhost:5432/testdb"
    config = parse_database_url(raw_url)
    assert config.engine == DatabaseEngine.POSTGRESQL
    assert "usr:***@localhost" in config.masked_url


def test_mask_database_url_edge_cases():
    """Verifies masking handles empty, malformed, or password-less URLs gracefully."""
    assert mask_database_url("") == ""
    assert mask_database_url("sqlite:///local.db") == "sqlite:///local.db"
    assert "user:***@host" in mask_database_url("postgresql://user:pass@host/db")
    assert mask_database_url("postgresql://user@host/db") == "postgresql://user@host/db"


# =============================================================================
# 3. Invalid Configuration & Failure Behavior
# =============================================================================

def test_invalid_database_url_handling():
    """Verifies that unsupported database schemes raise DatabaseConfigurationError loudly."""
    invalid_urls = [
        "mysql://root:secret@localhost:3306/db",
        "oracle://system:manager@localhost:1521/xe",
        "mongodb://localhost:27017/db",
        "redis://localhost:6379",
        "http://example.com/api",
    ]
    for url in invalid_urls:
        with pytest.raises(DatabaseConfigurationError) as exc_info:
            parse_database_url(url)
        assert "Unsupported database scheme" in str(exc_info.value)
        # Ensure password is masked even in exception message
        assert "secret" not in str(exc_info.value)
        assert "manager" not in str(exc_info.value)


def test_postgresql_unreachable_connection_does_not_silently_fallback():
    """
    CRITICAL INVARIANT:
    If a PostgreSQL URL is configured, connection failures must NOT silently
    fall back to a local SQLite database.
    """
    unreachable_pg = "postgresql://invalid_user:fake_pass@127.0.0.1:59999/nonexistent_db?sslmode=disable"
    with pytest.raises(DatabaseConnectionError):
        with get_db_connection(unreachable_pg, timeout=1.0) as conn:
            conn.execute("SELECT 1")


# =============================================================================
# 4. Connection Cleanup & Resource Management
# =============================================================================

def test_connection_cleanup_on_context_exit():
    """Verifies connections and cursors are reliably closed upon exiting context manager."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = tf.name

    try:
        captured_conn = None
        with get_db_connection(temp_path) as conn:
            captured_conn = conn
            assert conn.is_closed is False
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # After exiting block, connection must be closed
        assert captured_conn.is_closed is True
        with pytest.raises(DatabaseConnectionError):
            captured_conn.cursor()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_open_db_connection_manual_lifecycle():
    """Verifies manual close() on open_db_connection."""
    conn = open_db_connection(":memory:")
    assert conn.is_closed is False
    conn.execute("CREATE TABLE t (id INT)")
    conn.close()
    assert conn.is_closed is True


# =============================================================================
# 5. Transaction Handling (Commit & Rollback)
# =============================================================================

def test_transaction_commit_success():
    """Verifies explicit and context-manager transaction commits."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = tf.name

    try:
        with get_db_connection(temp_path) as conn:
            conn.execute("CREATE TABLE ledger (tx_id TEXT PRIMARY KEY, amount REAL)")
            conn.commit()

            with conn.transaction():
                conn.execute("INSERT INTO ledger VALUES (?, ?)", ("TX_001", 1000.0))
                conn.execute("INSERT INTO ledger VALUES (?, ?)", ("TX_002", 2500.0))

        # Verify both rows were committed
        with get_db_cursor(temp_path) as cur:
            cur.execute("SELECT COUNT(*) as cnt, SUM(amount) as total FROM ledger")
            row = cur.fetchone()
            assert row["cnt"] == 2
            assert row["total"] == 3500.0
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_transaction_rollback_on_exception():
    """Verifies atomic rollback when an exception occurs inside a transaction."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = tf.name

    try:
        with get_db_connection(temp_path) as conn:
            conn.execute("CREATE TABLE balances (account TEXT PRIMARY KEY, balance REAL)")
            conn.execute("INSERT INTO balances VALUES (?, ?)", ("ACC_1", 5000.0))
            conn.commit()

            # Attempt a debit/credit transfer that fails midway
            try:
                with conn.transaction():
                    conn.execute("UPDATE balances SET balance = balance - 1000 WHERE account = ?", ("ACC_1",))
                    raise RuntimeError("Network crash during transaction!")
            except RuntimeError:
                pass

        # Verify balance was restored to original 5000.0
        with get_db_cursor(temp_path) as cur:
            cur.execute("SELECT balance FROM balances WHERE account = ?", ("ACC_1",))
            row = cur.fetchone()
            assert row["balance"] == 5000.0
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =============================================================================
# 6. Parameterized Queries & SQL Injection Resistance
# =============================================================================

def test_parameterized_queries_and_sql_injection_resistance():
    """Verifies parameters are safely escaped and resistant to SQL injection."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = tf.name

    try:
        with get_db_connection(temp_path) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT)")
            conn.execute("INSERT INTO users (username, role) VALUES (?, ?)", ("trader_bob", "USER"))
            conn.execute("INSERT INTO users (username, role) VALUES (?, ?)", ("admin_alice", "ADMIN"))
            conn.commit()

            # Classic SQL injection payload
            injection_payload = "' OR '1'='1"
            cur = conn.execute("SELECT * FROM users WHERE username = ?", (injection_payload,))
            rows = cur.fetchall()
            # Must return 0 rows (treated strictly as literal username string)
            assert len(rows) == 0

            # Destructive injection attempt
            destructive_payload = "trader_bob'; DROP TABLE users; --"
            cur = conn.execute("SELECT * FROM users WHERE username = ?", (destructive_payload,))
            assert len(cur.fetchall()) == 0

            # Verify table still exists and data is intact
            cur = conn.execute("SELECT COUNT(*) as c FROM users")
            assert cur.fetchone()["c"] == 2
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_query_placeholder_adaptation():
    """
    Verifies query adaptation between ? and %s without altering string literals,
    SQL comments, or quoted identifiers.
    """
    # 1. Basic parameter substitution
    sql_with_qmark = "SELECT * FROM companies WHERE symbol = ? AND sector = ?"
    adapted_to_pg = _adapt_query_placeholders(sql_with_qmark, DatabaseEngine.POSTGRESQL)
    assert adapted_to_pg == "SELECT * FROM companies WHERE symbol = %s AND sector = %s"

    # 2. Query containing '?' inside a single-quoted string literal
    sql_with_literal = "SELECT * FROM audit WHERE notes = 'Is this active?' AND id = ?"
    adapted_literal = _adapt_query_placeholders(sql_with_literal, DatabaseEngine.POSTGRESQL)
    assert adapted_literal == "SELECT * FROM audit WHERE notes = 'Is this active?' AND id = %s"

    # 3. Query containing '?' inside single-quoted string with escaped quotes
    sql_escaped = "SELECT * FROM logs WHERE msg = 'Why? It''s broken?' AND id = ?"
    adapted_escaped = _adapt_query_placeholders(sql_escaped, DatabaseEngine.POSTGRESQL)
    assert adapted_escaped == "SELECT * FROM logs WHERE msg = 'Why? It''s broken?' AND id = %s"

    # 4. Query containing '?' inside single-line SQL comment
    sql_comment = "SELECT * FROM companies WHERE symbol = ? -- Should we filter by active?"
    adapted_comment = _adapt_query_placeholders(sql_comment, DatabaseEngine.POSTGRESQL)
    assert adapted_comment == "SELECT * FROM companies WHERE symbol = %s -- Should we filter by active?"

    # 5. Query containing '?' inside multi-line block comment
    sql_block = "/* Is this query valid? */ SELECT * FROM sectors WHERE id = ?"
    adapted_block = _adapt_query_placeholders(sql_block, DatabaseEngine.POSTGRESQL)
    assert adapted_block == "/* Is this query valid? */ SELECT * FROM sectors WHERE id = %s"

    # 6. Query containing '?' inside double-quoted identifier
    sql_ident = 'SELECT "col?" FROM tbl WHERE id = ?'
    adapted_ident = _adapt_query_placeholders(sql_ident, DatabaseEngine.POSTGRESQL)
    assert adapted_ident == 'SELECT "col?" FROM tbl WHERE id = %s'

    # 7. PostgreSQL -> SQLite adaptation
    sql_with_percent_s = "SELECT * FROM indicators WHERE date = %s -- Is date format YYYY-MM-DD%s?"
    adapted_to_sqlite = _adapt_query_placeholders(sql_with_percent_s, DatabaseEngine.SQLITE)
    assert adapted_to_sqlite == "SELECT * FROM indicators WHERE date = ? -- Is date format YYYY-MM-DD%s?"


# =============================================================================
# 7. DbRow Wrapper (PostgreSQL Row Ergonomics)
# =============================================================================

def test_dbrow_proxy_indexing_and_dict_access():
    """Verifies that DbRow provides identical column and index access to sqlite3.Row."""
    mapping = {"id": 0, "symbol": 1, "price": 2, "is_active": 3}
    data = (42, "INFY", 1850.75, True)
    row = DbRow(data, mapping)

    # Column name access
    assert row["symbol"] == "INFY"
    assert row["price"] == 1850.75
    assert row["is_active"] is True

    # Numeric index access
    assert row[0] == 42
    assert row[1] == "INFY"
    assert row[2] == 1850.75

    # Dict conversion
    d = dict(row.items())
    assert d == {"id": 42, "symbol": "INFY", "price": 1850.75, "is_active": True}

    # Dict comparison
    assert row == {"id": 42, "symbol": "INFY", "price": 1850.75, "is_active": True}

    # Helper methods
    assert row.get("symbol") == "INFY"
    assert row.get("missing", "default_val") == "default_val"
    assert list(row.keys()) == ["id", "symbol", "price", "is_active"]
    assert len(row) == 4

    with pytest.raises(KeyError):
        _ = row["nonexistent_column"]


# =============================================================================
# 8. Database Isolation Between Test Instances
# =============================================================================

def test_database_isolation_between_test_instances():
    """Verifies that separate database targets do not share state or leak data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf1, \
         tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf2:
        db1_path = tf1.name
        db2_path = tf2.name

    try:
        with get_db_connection(db1_path) as conn1:
            conn1.execute("CREATE TABLE inst1 (val TEXT)")
            conn1.execute("INSERT INTO inst1 VALUES ('instance_one')")
            conn1.commit()

        with get_db_connection(db2_path) as conn2:
            conn2.execute("CREATE TABLE inst2 (val TEXT)")
            conn2.execute("INSERT INTO inst2 VALUES ('instance_two')")
            conn2.commit()

        # Verify inst1 table does not exist in db2
        with get_db_cursor(db2_path) as cur2:
            with pytest.raises(DatabaseQueryError):
                cur2.execute("SELECT * FROM inst1")

        # Verify inst2 table does not exist in db1
        with get_db_cursor(db1_path) as cur1:
            with pytest.raises(DatabaseQueryError):
                cur1.execute("SELECT * FROM inst2")
    finally:
        for p in [db1_path, db2_path]:
            if os.path.exists(p):
                os.remove(p)


# =============================================================================
# 9. Live PostgreSQL Integration Test (Safe Skip Reporting)
# =============================================================================

def test_postgresql_live_integration_or_skip():
    """
    Attempts connection to live PostgreSQL test server only if TEST_POSTGRESQL_URL is set.
    Otherwise reports status as SKIPPED (NOT RUN: PostgreSQL test server not configured).
    """
    test_pg_url = os.getenv("TEST_POSTGRESQL_URL")
    if not test_pg_url:
        pytest.skip("NOT RUN: PostgreSQL test server not configured (set TEST_POSTGRESQL_URL to enable)")

    # If configured, run live verification
    with get_db_connection(test_pg_url, timeout=5.0) as conn:
        assert conn.engine == DatabaseEngine.POSTGRESQL
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS alive")
            row = cur.fetchone()
            assert row["alive"] == 1

