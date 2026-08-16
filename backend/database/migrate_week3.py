"""
Week 3 Database Migration
==========================

Adds the required financial-data fields to the existing
quarterly_results table.

This migration does NOT delete or modify existing market-price data.
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
# FINANCIAL COLUMNS
# ============================================================

FINANCIAL_COLUMNS = {
    "roe": "REAL",
    "roce": "REAL",
    "debt_equity": "REAL",
    "operating_margin": "REAL",
    "net_margin": "REAL",
}


# ============================================================
# MIGRATION
# ============================================================

def migrate_database():

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("WEEK 3 DATABASE MIGRATION")
    print("==========================================")

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Check existing columns
    # --------------------------------------------------------

    cursor.execute(
        "PRAGMA table_info(quarterly_results)"
    )

    existing_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    print("\nExisting quarterly_results columns:")

    for column in sorted(existing_columns):
        print(f"  ✓ {column}")

    # --------------------------------------------------------
    # Add missing financial columns
    # --------------------------------------------------------

    added_columns = []

    for column, data_type in FINANCIAL_COLUMNS.items():

        if column in existing_columns:

            print(
                f"✓ {column} already exists"
            )

            continue

        cursor.execute(
            f"""
            ALTER TABLE quarterly_results
            ADD COLUMN {column} {data_type}
            """
        )

        added_columns.append(column)

        print(
            f"✓ Added column: {column}"
        )

    connection.commit()

    # --------------------------------------------------------
    # Verify migration
    # --------------------------------------------------------

    cursor.execute(
        "PRAGMA table_info(quarterly_results)"
    )

    final_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    connection.close()

    print("\n==========================================")
    print("MIGRATION SUMMARY")
    print("==========================================")

    if added_columns:

        print(
            f"Columns added: {len(added_columns)}"
        )

    else:

        print(
            "No new columns were required"
        )

    print(
        "\nFinal quarterly_results schema:"
    )

    for column in final_columns:
        print(f"  ✓ {column}")

    print("\n==========================================")

    required_columns = [
        "company_id",
        "quarter",
        "revenue",
        "net_profit",
        "eps",
        "roe",
        "roce",
        "debt_equity",
        "operating_margin",
        "net_margin",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in final_columns
    ]

    if not missing_columns:

        print(
            "🎉 WEEK 3 FINANCIAL SCHEMA READY"
        )

        print(
            "All required financial columns exist."
        )

        print(
            "=========================================="
        )

    else:

        print(
            "❌ MIGRATION FAILED"
        )

        print(
            f"Missing columns: {missing_columns}"
        )

        print(
            "=========================================="
        )

        raise SystemExit(1)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    migrate_database()