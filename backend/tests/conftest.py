"""
Pytest Configuration and Fixtures
=================================
Provides test fixtures, marker definitions, and test-environment normalization.
Supports portable CI execution in clean runners where production databases are absent.
"""

import os
import tempfile
import pytest
from pathlib import Path

from backend.config import PROJECT_ROOT, DATABASE_PATH, get_database_path
from backend.tests.fixtures.synthetic_ci_fixture import create_synthetic_ci_database

_SESSION_SYNTHETIC_DB: Path | None = None


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_environment():
    """
    Session-level autouse fixture:
    - If database/swing_trading.db exists, preserves default local behavior.
    - If database/swing_trading.db does not exist (e.g. clean CI checkout),
      creates an isolated temporary synthetic database so that API contract
      and portable schema tests execute deterministically without failures.
    """
    global _SESSION_SYNTHETIC_DB
    prod_db = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()
    temp_dir_obj = None

    if not prod_db.exists():
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="ci_test_db_")
        synthetic_db = Path(temp_dir_obj.name) / "synthetic_test.db"
        create_synthetic_ci_database(synthetic_db)
        os.environ["DATABASE_PATH"] = str(synthetic_db)
        _SESSION_SYNTHETIC_DB = synthetic_db

    yield

    if temp_dir_obj is not None:
        if os.environ.get("DATABASE_PATH") == str(synthetic_db):
            os.environ.pop("DATABASE_PATH", None)
        _SESSION_SYNTHETIC_DB = None
        temp_dir_obj.cleanup()


@pytest.fixture(autouse=True)
def preserve_test_database_environment():
    """
    Guarantees that individual test modifications cannot leak and wipe
    the session-level synthetic test database.
    """
    yield
    if _SESSION_SYNTHETIC_DB is not None and _SESSION_SYNTHETIC_DB.exists():
        if os.environ.get("DATABASE_PATH") != str(_SESSION_SYNTHETIC_DB):
            os.environ["DATABASE_PATH"] = str(_SESSION_SYNTHETIC_DB)

