"""
Week 12 - Database Backup Service

Creates and verifies a timestamped SQLite database backup.
"""

from datetime import datetime
from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "database" / "swing_trading.db"

BACKUP_DIR = PROJECT_ROOT / "database" / "backups"


def create_backup():
    """Create and verify a timestamped database backup."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = (
        BACKUP_DIR
        / f"swing_trading_{timestamp}.db"
    )

    print("=" * 60)
    print("WEEK 12 - DATABASE BACKUP")
    print("=" * 60)

    print(f"Source database : {DATABASE_PATH}")
    print(f"Backup location : {backup_path}")

    source = sqlite3.connect(DATABASE_PATH)
    destination = sqlite3.connect(backup_path)

    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    if not backup_path.exists():
        raise RuntimeError(
            "Backup file was not created."
        )

    size = backup_path.stat().st_size

    if size <= 0:
        raise RuntimeError(
            "Backup file is empty."
        )

    connection = sqlite3.connect(backup_path)

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
    finally:
        connection.close()

    if integrity != "ok":
        raise RuntimeError(
            f"Backup integrity check failed: {integrity}"
        )

    print("-" * 60)
    print(f"Backup size     : {size:,} bytes")
    print(f"Integrity       : {integrity}")
    print("Status          : SUCCESS")
    print("=" * 60)

    return backup_path


def main():
    backup_path = create_backup()

    print(f"\nVerified backup: {backup_path}")

    return True


if __name__ == "__main__":
    success = main()

    if not success:
        raise SystemExit(1)