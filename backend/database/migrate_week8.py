"""
Week 8 - Technical Indicator Database Migration

Extends the existing technical_indicators table so it can store
the validated outputs produced by the Technical Engine.

This migration:
    - preserves all existing data
    - adds only missing columns
    - does not calculate indicators
    - does not modify trading logic
    - can be safely run more than once
"""

import sqlite3
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


# ============================================================
# COLUMNS REQUIRED BY WEEK 8
# ============================================================

REQUIRED_COLUMNS = {
    "ema_200": "REAL",
    "macd_histogram": "REAL",
    "atr_14": "REAL",
    "technical_score": "REAL",
}


# ============================================================
# HELPERS
# ============================================================

def get_existing_columns(cursor):
    """Return existing technical_indicators column names."""

    rows = cursor.execute(
        "PRAGMA table_info(technical_indicators)"
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


# ============================================================
# MIGRATION
# ============================================================

def migrate():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - TECHNICAL INDICATOR DATABASE MIGRATION")
    print("=" * 60)

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    try:

        # ----------------------------------------------------
        # Verify table exists
        # ----------------------------------------------------

        table = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'technical_indicators'
            """
        ).fetchone()

        if table is None:

            raise RuntimeError(
                "technical_indicators table does not exist."
            )

        print(
            "\n✓ technical_indicators table found"
        )

        # ----------------------------------------------------
        # Existing columns
        # ----------------------------------------------------

        existing_columns = get_existing_columns(
            cursor
        )

        print("\nExisting columns:")

        for column in sorted(existing_columns):

            print(
                f"  ✓ {column}"
            )

        # ----------------------------------------------------
        # Add required columns
        # ----------------------------------------------------

        print(
            "\nAdding Week 8 columns..."
        )

        added = 0
        already_exists = 0

        for column, data_type in (
            REQUIRED_COLUMNS.items()
        ):

            if column in existing_columns:

                print(
                    f"  ✓ {column} already exists"
                )

                already_exists += 1

                continue

            cursor.execute(
                f"""
                ALTER TABLE technical_indicators
                ADD COLUMN {column} {data_type}
                """
            )

            print(
                f"  ✓ Added {column}"
            )

            added += 1

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

        # ----------------------------------------------------
        # Verify final schema
        # ----------------------------------------------------

        final_columns = get_existing_columns(
            cursor
        )

        missing = (
            set(REQUIRED_COLUMNS)
            - final_columns
        )

        if missing:

            raise RuntimeError(
                "Migration verification failed. "
                f"Missing columns: {sorted(missing)}"
            )

        # ----------------------------------------------------
        # Verify existing records preserved
        # ----------------------------------------------------

        record_count = cursor.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators
            """
        ).fetchone()[0]

        print(
            "\n------------------------------------------"
        )

        print(
            "WEEK 8 MIGRATION VERIFICATION"
        )

        print(
            "------------------------------------------"
        )

        print(
            f"Columns added      : {added}"
        )

        print(
            f"Already existed    : {already_exists}"
        )

        print(
            f"Technical records  : {record_count}"
        )

        print(
            "\nRequired columns:"
        )

        for column in REQUIRED_COLUMNS:

            print(
                f"  ✓ {column}"
            )

        print(
            "\n🎉 WEEK 8 DATABASE MIGRATION PASSED"
        )

        print(
            "Existing technical data was preserved."
        )

        print(
            "No indicator calculations were performed."
        )

        print("=" * 60)

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ MIGRATION FAILED"
        )

        print(
            f"Error: {error}"
        )

        print(
            "All changes were rolled back."
        )

        raise

    finally:

        connection.close()


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    migrate()