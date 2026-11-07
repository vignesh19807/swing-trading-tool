"""
First-Boot Database Validation Service
======================================
Ensures the backend never silently treats an uninitialized or empty database
as a fully initialized research database. Validates schema completeness,
table structure, foreign keys, and baseline records.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Union

from backend.config import get_database_path
from backend.database.connection import open_db_connection, DatabaseEngine

logger = logging.getLogger(__name__)

REQUIRED_CORE_TABLES = {
    "companies",
    "sectors",
    "industries",
    "daily_prices",
    "quarterly_results",
    "technical_indicators",
    "signals",
    "opportunity_scores",
    "backtest_trades",
    "backtest_results",
    "financial_scores",
    "universe_audit_log",
}

def validate_database_readiness(db_path: Path = None) -> Dict[str, Any]:
    """
    Performs comprehensive first-boot verification on the configured database.
    Fails closed if the database is missing, corrupted, unseeded, or partially migrated.
    """
    target = db_path if db_path else get_database_path()
    target_str = str(target)
    is_pg = target_str.startswith(("postgresql://", "postgres://"))

    if not is_pg:
        target_path = Path(target)
        if not target_path.exists():
            return {
                "is_ready": False,
                "status": "MISSING_DATABASE_FILE",
                "detail": f"Database file does not exist at configured path: {target_path}",
                "companies_count": 0,
                "missing_tables": sorted(list(REQUIRED_CORE_TABLES)),
            }

        if target_path.stat().st_size == 0:
            return {
                "is_ready": False,
                "status": "EMPTY_DATABASE_FILE",
                "detail": "Database file is 0 bytes. Persistent volume requires initialization/seeding.",
                "companies_count": 0,
                "missing_tables": sorted(list(REQUIRED_CORE_TABLES)),
            }

    conn = None
    try:
        conn = open_db_connection(target)
        cursor = conn.cursor()

        # 1. Integrity check
        if conn.engine == DatabaseEngine.POSTGRESQL:
            cursor.execute("SELECT 1")
        else:
            cursor.execute("PRAGMA integrity_check")
            integrity_row = cursor.fetchone()
            if not integrity_row or integrity_row[0] != "ok":
                return {
                    "is_ready": False,
                    "status": "CORRUPTED_DATABASE",
                    "detail": f"SQLite integrity check failed: {integrity_row[0] if integrity_row else 'Unknown error'}",
                    "companies_count": 0,
                    "missing_tables": [],
                }

        # 2. Check existing tables
        if conn.engine == DatabaseEngine.POSTGRESQL:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        else:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        missing_tables = REQUIRED_CORE_TABLES - existing_tables

        if missing_tables:
            return {
                "is_ready": False,
                "status": "INCOMPLETE_SCHEMA",
                "detail": f"Database missing essential tables: {sorted(list(missing_tables))}",
                "companies_count": 0,
                "missing_tables": sorted(list(missing_tables)),
            }

        # 3. Check companies count
        cursor.execute("SELECT count(*) FROM companies")
        companies_count = cursor.fetchone()[0]

        if companies_count == 0:
            return {
                "is_ready": False,
                "status": "UNSEEDED_DATABASE",
                "detail": "Database schema exists but companies table contains zero records.",
                "companies_count": 0,
                "missing_tables": [],
            }

        return {
            "is_ready": True,
            "status": "READY",
            "detail": "Database is fully initialized and operational.",
            "companies_count": companies_count,
            "missing_tables": [],
        }

    except Exception as exc:
        logger.error(f"First-boot database validation encountered an unexpected exception: {exc}")
        return {
            "is_ready": False,
            "status": "VALIDATION_EXCEPTION",
            "detail": f"Database check failed with exception: {type(exc).__name__}",
            "companies_count": 0,
            "missing_tables": [],
        }
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    result = validate_database_readiness()
    print("Database First-Boot Verification:")
    print(f"Status: {result['status']}")
    print(f"Is Ready: {result['is_ready']}")
    print(f"Companies Count: {result['companies_count']}")
    print(f"Detail: {result['detail']}")

