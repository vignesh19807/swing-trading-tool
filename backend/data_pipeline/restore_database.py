"""
Week 12 - Database Restore & Recovery Validation

Purpose:
    Restore a verified SQLite backup into a separate recovery database
    and validate that the recovered database is usable.

Safety:
    - NEVER overwrites the production database.
    - Production database remains read-only during this operation.
    - Recovery database is created separately.

Responsibilities:
    - Locate a backup database
    - Restore it using SQLite backup
    - Verify the recovered database exists
    - Verify recovered database is non-empty
    - Run SQLite integrity_check
    - Compare table record counts with the backup
"""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)

BACKUP_DIR = (
    PROJECT_ROOT
    / "database"
    / "backups"
)

RECOVERY_DIR = (
    PROJECT_ROOT
    / "database"
    / "recovery"
)

RECOVERY_PATH = (
    RECOVERY_DIR
    / "swing_trading_recovery.db"
)


def get_latest_backup():
    """Return the newest database backup."""

    backups = sorted(
        BACKUP_DIR.glob("*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not backups:
        raise FileNotFoundError(
            f"No database backups found in {BACKUP_DIR}"
        )

    return backups[0]


def get_table_counts(database_path):
    """Return record counts for all application tables."""

    connection = sqlite3.connect(database_path)

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        counts = {}

        for (table,) in tables:
            counts[table] = connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

        return counts

    finally:
        connection.close()


def get_integrity(database_path):
    """Run SQLite integrity_check."""

    connection = sqlite3.connect(database_path)

    try:
        return connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

    finally:
        connection.close()


def restore_database(backup_path=None):
    """
    Restore a backup into a separate recovery database.

    Production database is never modified.
    """

    if backup_path is None:
        backup_path = get_latest_backup()

    backup_path = Path(backup_path)

    if not backup_path.exists():
        raise FileNotFoundError(
            f"Backup database not found: {backup_path}"
        )

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Production database not found: {DATABASE_PATH}"
        )

    RECOVERY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if RECOVERY_PATH.exists():
        RECOVERY_PATH.unlink()

    print("=" * 60)
    print("WEEK 12 - DATABASE RESTORE & RECOVERY")
    print("=" * 60)

    print(
        f"Backup source : {backup_path}"
    )

    print(
        f"Recovery DB   : {RECOVERY_PATH}"
    )

    print(
        f"Production DB : {DATABASE_PATH}"
    )

    # --------------------------------------------------------
    # Restore backup into separate recovery database
    # --------------------------------------------------------

    source = sqlite3.connect(backup_path)
    destination = sqlite3.connect(RECOVERY_PATH)

    try:
        source.backup(destination)

    finally:
        destination.close()
        source.close()

    # --------------------------------------------------------
    # Verify recovery database exists
    # --------------------------------------------------------

    if not RECOVERY_PATH.exists():
        raise RuntimeError(
            "Recovery database was not created."
        )

    size = RECOVERY_PATH.stat().st_size

    if size <= 0:
        raise RuntimeError(
            "Recovery database is empty."
        )

    # --------------------------------------------------------
    # Validate integrity
    # --------------------------------------------------------

    backup_integrity = get_integrity(
        backup_path
    )

    recovery_integrity = get_integrity(
        RECOVERY_PATH
    )

    # --------------------------------------------------------
    # Compare recovered data
    # --------------------------------------------------------

    backup_counts = get_table_counts(
        backup_path
    )

    recovery_counts = get_table_counts(
        RECOVERY_PATH
    )

    print("-" * 60)

    print(
        f"Backup integrity   : {backup_integrity}"
    )

    print(
        f"Recovery integrity : {recovery_integrity}"
    )

    print(
        f"Recovery size      : {size:,} bytes"
    )

    print("\nTABLE RECOVERY COMPARISON")
    print("-" * 60)

    all_tables = sorted(
        set(backup_counts)
        | set(recovery_counts)
    )

    all_match = True

    for table in all_tables:

        backup_count = backup_counts.get(table)
        recovery_count = recovery_counts.get(table)

        match = (
            backup_count == recovery_count
        )

        if not match:
            all_match = False

        status = "OK" if match else "MISMATCH"

        print(
            f"{table:<30} "
            f"backup={str(backup_count):>6} "
            f"recovery={str(recovery_count):>6} "
            f"{status}"
        )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    passed = (
        backup_integrity == "ok"
        and recovery_integrity == "ok"
        and all_match
    )

    print("\n" + "=" * 60)

    if passed:

        print(
            "STATUS: DATABASE RECOVERY VALIDATION PASSED"
        )

        print(
            "Production database was not overwritten."
        )

    else:

        print(
            "STATUS: DATABASE RECOVERY VALIDATION FAILED"
        )

    print("=" * 60)

    return passed


def main():
    return restore_database()


if __name__ == "__main__":

    success = main()

    if not success:
        raise SystemExit(1)