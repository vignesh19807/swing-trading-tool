"""
Week 3 Financial Table Constraint Migration
============================================

Adds a UNIQUE(company_id, quarter) constraint to the
existing quarterly_results table.

Existing records are preserved.
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
# MIGRATION
# ============================================================

def migrate():

    print("==========================================")
    print("WEEK 3 FINANCIAL CONSTRAINT MIGRATION")
    print("==========================================")

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Check for existing duplicates
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT company_id, quarter, COUNT(*)
        FROM quarterly_results
        GROUP BY company_id, quarter
        HAVING COUNT(*) > 1
        """
    )

    duplicates = cursor.fetchall()

    if duplicates:

        print(
            "❌ Duplicate company/quarter records found."
        )

        for duplicate in duplicates:

            print(
                f"   company_id={duplicate[0]}, "
                f"quarter={duplicate[1]}, "
                f"count={duplicate[2]}"
            )

        print(
            "\nMigration stopped."
        )

        connection.close()

        raise SystemExit(1)

    print(
        "✓ No existing duplicate financial records"
    )

    # --------------------------------------------------------
    # Create replacement table
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE quarterly_results_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            revenue REAL,
            net_profit REAL,
            eps REAL,
            roe REAL,
            roce REAL,
            debt_equity REAL,
            operating_margin REAL,
            net_margin REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id),

            UNIQUE(company_id, quarter)
        )
        """
    )

    print(
        "✓ New financial table created"
    )

    # --------------------------------------------------------
    # Copy existing records
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO quarterly_results_new (
            id,
            company_id,
            quarter,
            revenue,
            net_profit,
            eps,
            roe,
            roce,
            debt_equity,
            operating_margin,
            net_margin
        )
        SELECT
            id,
            company_id,
            quarter,
            revenue,
            net_profit,
            eps,
            roe,
            roce,
            debt_equity,
            operating_margin,
            net_margin
        FROM quarterly_results
        """
    )

    copied = cursor.rowcount

    print(
        f"✓ Existing records copied: {copied}"
    )

    # --------------------------------------------------------
    # Replace old table
    # --------------------------------------------------------

    cursor.execute(
        """
        DROP TABLE quarterly_results
        """
    )

    cursor.execute(
        """
        ALTER TABLE quarterly_results_new
        RENAME TO quarterly_results
        """
    )

    connection.commit()

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'quarterly_results'
        """
    )

    schema = cursor.fetchone()[0]

    print(
        "\nFinal table definition:"
    )

    print(schema)

    connection.close()

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    if "UNIQUE(company_id, quarter)" in schema:

        print(
            "\n=========================================="
        )

        print(
            "🎉 FINANCIAL CONSTRAINT MIGRATION PASSED"
        )

        print(
            "UNIQUE(company_id, quarter) is active."
        )

        print(
            "=========================================="
        )

    else:

        print(
            "\n❌ UNIQUE constraint was not found."
        )

        raise SystemExit(1)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    migrate()
    