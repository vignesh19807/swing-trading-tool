"""
Phase 4 Universe Schema Migration
=================================
Extends the companies table to support dynamic, database-driven stock universe
management with lifecycle tracking, active/inactive states, and audit logging.

Capabilities added:
- is_active (INTEGER NOT NULL DEFAULT 1)
- status (TEXT NOT NULL DEFAULT 'ACTIVE')
- listing_date (TEXT)
- created_at (TEXT)
- updated_at (TEXT)
- source (TEXT DEFAULT 'INITIAL_UNIVERSE')
- universe_audit_log table (tracks all additions, activations, deactivations)

Safety Invariants:
- Strictly idempotent: checks PRAGMA table_info before adding columns.
- Preserves all existing company IDs, symbols, sector_ids, and foreign key relationships.
- Non-destructive: existing rows default to is_active=1, status='ACTIVE'.
- Can be tested against any isolated SQLite database file.
"""

import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Optional

from backend.config import DATABASE_PATH

logger = logging.getLogger(__name__)


def migrate_universe_schema(db_path: Optional[Path] = None) -> bool:
    """
    Applies universe schema extensions to the specified SQLite database.

    Parameters
    ----------
    db_path : Path, optional
        Path to the target database. Defaults to DATABASE_PATH.

    Returns
    -------
    bool
        True if migration completed successfully.
    """
    target_path = Path(db_path or DATABASE_PATH)
    if not target_path.exists():
        raise FileNotFoundError(f"Database file not found at: {target_path}")

    conn = sqlite3.connect(target_path)
    cur = conn.cursor()

    try:
        cur.execute("PRAGMA foreign_keys = ON")

        # 1. Inspect existing columns in companies
        cur.execute("PRAGMA table_info(companies)")
        existing_cols = {row[1] for row in cur.fetchall()}

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 2. Add columns if not already present
        if "is_active" not in existing_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
            logger.info("Added column is_active to companies")

        if "status" not in existing_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE'")
            logger.info("Added column status to companies")

        if "listing_date" not in existing_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN listing_date TEXT")
            logger.info("Added column listing_date to companies")

        if "created_at" not in existing_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN created_at TEXT")
            # Populate created_at for legacy companies
            cur.execute("UPDATE companies SET created_at = ? WHERE created_at IS NULL", (now_iso,))
            logger.info("Added column created_at to companies")

        if "updated_at" not in existing_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN updated_at TEXT")
            # Populate updated_at for legacy companies
            cur.execute("UPDATE companies SET updated_at = ? WHERE updated_at IS NULL", (now_iso,))
            logger.info("Added column updated_at to companies")

        if "source" not in existing_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN source TEXT DEFAULT 'INITIAL_UNIVERSE'")
            logger.info("Added column source to companies")

        # 3. Create universe_audit_log table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS universe_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                old_values_json TEXT,
                new_values_json TEXT,
                initiated_by TEXT NOT NULL DEFAULT 'SYSTEM',
                notes TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # 4. Create indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_is_active ON companies(is_active)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_universe_audit_symbol ON universe_audit_log(symbol)")

        conn.commit()
        logger.info(f"Successfully migrated universe schema for {target_path}")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to migrate universe schema: {e}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Universe schema migration module ready.")

