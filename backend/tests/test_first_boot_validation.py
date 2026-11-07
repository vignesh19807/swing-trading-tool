"""
Tests for First-Boot Database Validation and Staging Seeding
============================================================
"""

import tempfile
import sqlite3
from pathlib import Path
from backend.database.first_boot_validation import validate_database_readiness
from backend.database.staging_seed import provision_staging_database

def test_missing_database_file_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent = Path(tmpdir) / "does_not_exist.db"
        result = validate_database_readiness(non_existent)
        assert result["is_ready"] is False
        assert result["status"] == "MISSING_DATABASE_FILE"

def test_empty_zero_byte_database_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_db = Path(tmpdir) / "empty.db"
        empty_db.touch()
        result = validate_database_readiness(empty_db)
        assert result["is_ready"] is False
        assert result["status"] == "EMPTY_DATABASE_FILE"

def test_incomplete_schema_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        partial_db = Path(tmpdir) / "partial.db"
        conn = sqlite3.connect(partial_db)
        conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT)")
        conn.execute("INSERT INTO companies (symbol) VALUES ('TCS')")
        conn.commit()
        conn.close()

        result = validate_database_readiness(partial_db)
        assert result["is_ready"] is False
        assert result["status"] == "INCOMPLETE_SCHEMA"
        assert "sectors" in result["missing_tables"]

def test_staging_seed_provisions_valid_database():
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_target = Path(tmpdir) / "test_staging.db"
        provision_staging_database(staging_target, force_recreate=True)
        assert staging_target.exists()
        assert staging_target.stat().st_size > 0

        result = validate_database_readiness(staging_target)
        assert result["is_ready"] is True
        assert result["status"] == "READY"
        assert result["companies_count"] == 10

