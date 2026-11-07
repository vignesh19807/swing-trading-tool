"""
Unit tests for centralized database path configuration.
Verifies Task 2, Task B & Task E requirements:
- Default local path behavior
- Environment variable overrides (absolute and relative)
- Anchoring of relative paths to PROJECT_ROOT (CWD independence)
- Dynamic update of DATABASE_PATH proxy when os.environ changes
- Path operators (__truediv__, parent, exists)
- Isolation of staging and test databases
- Parent directory safety
- Health probe readiness & missing DB handling
"""

import os
import sqlite3
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.config import PROJECT_ROOT, DATABASE_PATH, get_database_path
from backend.app import app


def test_default_database_path():
    """Verify default database path points to project root / database / swing_trading.db."""
    original = os.environ.get("DATABASE_PATH")
    try:
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]
        default_path = get_database_path()
        expected = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()
        assert default_path == expected
        assert DATABASE_PATH == expected
    finally:
        if original is not None:
            os.environ["DATABASE_PATH"] = original


def test_database_path_env_override():
    """Verify DATABASE_PATH environment variable overrides default path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "custom" / "custom_market.db"
        os.environ["DATABASE_PATH"] = str(test_db)
        try:
            resolved = get_database_path()
            assert resolved == test_db.resolve()
            assert test_db.parent.exists()  # Parent dir safely created
            assert DATABASE_PATH == test_db.resolve()
        finally:
            del os.environ["DATABASE_PATH"]


def test_relative_database_path_anchored_to_project_root():
    """Verify relative DATABASE_PATH resolves relative to PROJECT_ROOT regardless of CWD."""
    original = os.environ.get("DATABASE_PATH")
    try:
        os.environ["DATABASE_PATH"] = "database/swing_trading.db"
        resolved = get_database_path()
        expected = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()
        assert resolved == expected
        assert DATABASE_PATH == expected
    finally:
        if original is not None:
            os.environ["DATABASE_PATH"] = original
        else:
            os.environ.pop("DATABASE_PATH", None)


def test_dynamic_proxy_updates_on_environ_change():
    """Verify DATABASE_PATH proxy dynamically reflects os.environ changes without re-import."""
    original = os.environ.get("DATABASE_PATH")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "dynamic_test.db"
        try:
            os.environ["DATABASE_PATH"] = str(tmp_db)
            assert str(DATABASE_PATH) == str(tmp_db.resolve())
            assert DATABASE_PATH.name == "dynamic_test.db"
            assert not DATABASE_PATH.exists()
            # Test sqlite3.connect with the proxy object directly (via os.PathLike)
            conn = sqlite3.connect(DATABASE_PATH)
            conn.execute("CREATE TABLE test_proxy (id INT)")
            conn.commit()
            conn.close()
            assert DATABASE_PATH.exists()
        finally:
            if original is not None:
                os.environ["DATABASE_PATH"] = original
            else:
                os.environ.pop("DATABASE_PATH", None)


def test_database_path_operators():
    """Verify parent and truediv (/) operators work on DATABASE_PATH."""
    backup_dir = DATABASE_PATH.parent / "backups"
    assert backup_dir.name == "backups"
    child = DATABASE_PATH / "subfile"
    assert child.name == "subfile"


@pytest.mark.requires_preseeded_db
def test_read_only_access_existing_db(monkeypatch):
    """Verify that importing services with default path allows reading tables without mutation."""
    from backend.data_pipeline.classification_service import get_all_classifications
    from backend.data_pipeline.data_service import get_latest_price

    monkeypatch.setenv("DATABASE_URL", "")
    df = get_all_classifications()
    assert df is not None
    assert len(df) == 52

    price = get_latest_price("TCS")
    assert price is not None
    assert "close" in price


@pytest.mark.requires_preseeded_db
def test_healthz_probes_with_active_database(monkeypatch):
    """Verify liveness, readiness, and composite healthz return 200 with standard healthy database."""
    monkeypatch.setenv("DATABASE_URL", "")
    client = TestClient(app)
    root_res = client.get("/healthz")
    assert root_res.status_code == 200
    assert root_res.json()["status"] == "healthy"
    assert root_res.json()["readiness"]["companies_count"] >= 50

    live_res = client.get("/healthz/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "ok"

    ready_res = client.get("/healthz/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"
    assert ready_res.json()["companies_count"] >= 50


def test_healthz_readiness_missing_database_fails_without_creating_file(monkeypatch):
    """Verify readiness returns 503 when database is missing, and does NOT create empty file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent_db = Path(tmpdir) / "missing" / "non_existent.db"
        monkeypatch.setenv("DATABASE_PATH", str(non_existent_db))
        monkeypatch.setenv("DATABASE_URL", "")

        client = TestClient(app)
        res = client.get("/healthz/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["detail"] == "Database file does not exist"
        # Invariant: Must not create a 0-byte placeholder
        assert not non_existent_db.exists()

        # Verify composite /healthz also fails with 503
        res_root = client.get("/healthz")
        assert res_root.status_code == 503


def test_healthz_readiness_unseeded_database_fails(monkeypatch):
    """Verify readiness returns 503 with 'Database unseeded' when companies table is empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_db = Path(tmpdir) / "empty.db"
        conn = sqlite3.connect(empty_db)
        conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT)")
        conn.commit()
        conn.close()

        monkeypatch.setenv("DATABASE_PATH", str(empty_db))
        monkeypatch.setenv("DATABASE_URL", "")

        client = TestClient(app)
        res = client.get("/healthz/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["detail"] == "Database unseeded"


def test_healthz_readiness_does_not_leak_filesystem_paths(monkeypatch):
    """Verify readiness error responses never expose internal filesystem paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupted_db = Path(tmpdir) / "corrupt.db"
        # Write non-sqlite garbage
        with open(corrupted_db, "wb") as f:
            f.write(b"not a valid sqlite file header")

        monkeypatch.setenv("DATABASE_PATH", str(corrupted_db))
        monkeypatch.setenv("DATABASE_URL", "")

        client = TestClient(app)
        res = client.get("/healthz/ready")
        assert res.status_code == 503
        detail = res.json()["detail"]
        assert tmpdir not in detail
        assert "Database check failed" in detail


class TestDatabaseEnvironmentValidation:
    """Test suite for validate_database_environment() function."""

    def test_dev_missing_url_allowed(self):
        """Case 1: Development environment with missing DATABASE_URL allows default."""
        from backend.config import validate_database_environment
        validate_database_environment(env_name="development", db_url="")
        validate_database_environment(env_name="development", db_url=None)

    def test_dev_sqlite_url_allowed(self):
        """Case 2: Development environment with SQLite URL is allowed."""
        from backend.config import validate_database_environment
        validate_database_environment(env_name="development", db_url="sqlite:///database/swing_trading.db")
        validate_database_environment(env_name="development", db_url="sqlite:///:memory:")

    def test_dev_postgresql_url_allowed(self):
        """Case 3: Development environment with PostgreSQL URL is allowed."""
        from backend.config import validate_database_environment
        validate_database_environment(
            env_name="development",
            db_url="postgresql://user:pass@ep-test-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
        )

    def test_prod_valid_postgresql_allowed(self):
        """Case 4: Production environment with valid PostgreSQL URL is allowed."""
        from backend.config import validate_database_environment
        validate_database_environment(
            env_name="production",
            db_url="postgresql://user:pass@ep-test-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
        )
        validate_database_environment(
            env_name="production",
            db_url="postgres://user:pass@ep-test-123.ap-southeast-1.aws.neon.tech/neondb"
        )

    def test_prod_missing_url_fails_closed(self):
        """Case 5: Production environment with missing DATABASE_URL fails closed."""
        from backend.config import validate_database_environment, ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            validate_database_environment(env_name="production", db_url="")
        assert "DATABASE_URL must be configured when ENVIRONMENT=production" in str(exc_info.value)
        assert "Silent fallback to local SQLite is strictly prohibited" in str(exc_info.value)

    def test_prod_sqlite_url_fails_closed(self):
        """Case 6: Production environment with SQLite URL fails closed."""
        from backend.config import validate_database_environment, ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            validate_database_environment(env_name="production", db_url="sqlite:///database/swing_trading.db")
        assert "SQLite database cannot be used when ENVIRONMENT=production" in str(exc_info.value)

        with pytest.raises(ConfigurationError) as exc_info2:
            validate_database_environment(env_name="production", db_url="database/swing_trading.db")
        assert "SQLite database cannot be used when ENVIRONMENT=production" in str(exc_info2.value)

    def test_prod_malformed_or_non_pg_scheme_fails_closed(self):
        """Case 7: Production environment with non-PostgreSQL scheme fails closed."""
        from backend.config import validate_database_environment, ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            validate_database_environment(env_name="production", db_url="mysql://user:pass@localhost/db")
        assert "DATABASE_URL must use 'postgresql://' or 'postgres://' scheme in production" in str(exc_info.value)


class TestParseDatabaseUrlWithEnvironmentGuard:
    """Test parse_database_url behavior with live environment variables."""

    def test_prod_env_blocks_default_sqlite(self, monkeypatch):
        """When ENVIRONMENT=production and no DATABASE_URL is set, parse_database_url() fails closed."""
        from backend.config import ConfigurationError
        from backend.database.connection import parse_database_url
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "")
        with pytest.raises(ConfigurationError):
            parse_database_url()

    def test_prod_env_blocks_explicit_sqlite(self, monkeypatch):
        """When ENVIRONMENT=production, passing an explicit SQLite path fails closed."""
        from backend.config import ConfigurationError
        from backend.database.connection import parse_database_url
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "")
        with pytest.raises(ConfigurationError):
            parse_database_url("sqlite:///database/swing_trading.db")

    def test_prod_env_allows_neon_pg_url(self, monkeypatch):
        """When ENVIRONMENT=production with Neon PostgreSQL URL, config succeeds."""
        from backend.database.connection import parse_database_url, DatabaseEngine
        dummy_pg = "postgresql://user:secret@ep-test-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", dummy_pg)
        config = parse_database_url()
        assert config.engine == DatabaseEngine.POSTGRESQL
        assert config.masked_url == "postgresql://user:***@ep-test-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
        assert "secret" not in config.masked_url
