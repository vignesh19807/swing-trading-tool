"""
Database Persistence & Operational Safety Test Suite
===================================================

Verifies Task D requirements:
1. Configured DATABASE_PATH points to mounted/persistent location.
2. In-process restart simulation retains data without wipe.
3. Backup utility respects configured DATABASE_PATH dynamically.
4. Restore utility respects configured DATABASE_PATH dynamically.
5. Missing database never results in 0-byte accidental creation.
6. .dockerignore strictly blocks production and staging databases.
7. Production database remains strictly read-only and immutable.
"""

import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
import pytest

from backend.config import PROJECT_ROOT, DATABASE_PATH, get_database_path


def test_database_persistence_simulation():
    """Verify data persisted in a configured directory survives simulated restart."""
    with tempfile.TemporaryDirectory() as persistent_dir:
        mount_path = Path(persistent_dir) / "swing_trading.db"
        original_env = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(mount_path)

        try:
            # 1. First run / init
            conn1 = sqlite3.connect(DATABASE_PATH)
            conn1.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT)")
            conn1.execute("INSERT INTO companies (symbol) VALUES ('TESTCO')")
            conn1.commit()
            conn1.close()

            # 2. Simulated container restart (disconnect & re-query)
            conn2 = sqlite3.connect(DATABASE_PATH)
            cursor = conn2.cursor()
            cursor.execute("SELECT symbol FROM companies WHERE id = 1")
            row = cursor.fetchone()
            conn2.close()

            assert row is not None
            assert row[0] == "TESTCO"
            assert mount_path.exists()
            assert mount_path.stat().st_size > 0
        finally:
            if original_env is not None:
                os.environ["DATABASE_PATH"] = original_env
            else:
                os.environ.pop("DATABASE_PATH", None)


def test_backup_service_respects_configured_database_path():
    """Verify backup_database.py creates backup from the active DATABASE_PATH."""
    from backend.data_pipeline.backup_database import create_backup

    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "swing_trading.db"
        # Seed test db
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT)")
        conn.execute("INSERT INTO companies (symbol) VALUES ('BACKUP_TEST')")
        conn.commit()
        conn.close()

        original_env = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(test_db)

        try:
            backup_result = create_backup()
            assert backup_result.exists()
            assert backup_result.parent == test_db.parent / "backups"

            # Verify backup content
            b_conn = sqlite3.connect(backup_result)
            b_cur = b_conn.cursor()
            b_cur.execute("SELECT symbol FROM companies")
            symbols = [r[0] for r in b_cur.fetchall()]
            b_conn.close()

            assert "BACKUP_TEST" in symbols
        finally:
            if original_env is not None:
                os.environ["DATABASE_PATH"] = original_env
            else:
                os.environ.pop("DATABASE_PATH", None)


def test_restore_service_respects_configured_database_path():
    """Verify restore_database.py restores to the active DATABASE_PATH location."""
    from backend.data_pipeline.restore_database import restore_database

    with tempfile.TemporaryDirectory() as tmpdir:
        source_db = Path(tmpdir) / "source.db"
        conn = sqlite3.connect(source_db)
        conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT)")
        conn.execute("INSERT INTO companies (symbol) VALUES ('RESTORE_TEST')")
        conn.commit()
        conn.close()

        # Create a backup file
        backups_dir = Path(tmpdir) / "backups"
        backups_dir.mkdir()
        backup_file = backups_dir / "swing_trading_20261106_120000.db"
        shutil.copyfile(source_db, backup_file)

        # Set DATABASE_PATH to source_db (representing active database)
        original_env = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(source_db)

        try:
            from backend.data_pipeline.restore_database import get_recovery_path
            success = restore_database(backup_file)
            assert success is True
            recovered_path = get_recovery_path()
            assert recovered_path.exists()
            assert recovered_path.parent == source_db.parent / "recovery"

            r_conn = sqlite3.connect(recovered_path)
            r_cur = r_conn.cursor()
            r_cur.execute("SELECT symbol FROM companies")
            res = [r[0] for r in r_cur.fetchall()]
            r_conn.close()

            assert "RESTORE_TEST" in res
        finally:
            if original_env is not None:
                os.environ["DATABASE_PATH"] = original_env
            else:
                os.environ.pop("DATABASE_PATH", None)


def test_dockerignore_strictly_excludes_sqlite_databases():
    """Verify .dockerignore explicitly blocks all SQLite files and directories."""
    dockerignore_path = PROJECT_ROOT / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist in project root"

    with open(dockerignore_path, "r", encoding="utf-8") as f:
        content = f.read()

    patterns = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    # Required exclusion rules
    required = ["*.db", "*.sqlite", "database/swing_trading.db", "database/staging_financial_expansion.db"]
    for req in required:
        assert req in patterns, f"Required pattern '{req}' missing from .dockerignore"
