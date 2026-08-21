"""
Financial Database Indexes
==========================

Week 4 - Wednesday

Adds indexes that improve common financial-data queries.

The UNIQUE(company_id, quarter) constraint already creates
an automatic SQLite index. These indexes are additional
query-performance indexes.
"""

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


def add_indexes():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    # --------------------------------------------------------
    # 1. Company + quarter
    # --------------------------------------------------------
    #
    # Useful for:
    #
    #   Get all financial records for one company
    #   ordered by reporting period.
    #
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_quarterly_results_company_quarter
        ON quarterly_results(company_id, quarter)
    """)

    # --------------------------------------------------------
    # 2. Quarter
    # --------------------------------------------------------
    #
    # Useful for:
    #
    #   Get financial records for a particular
    #   reporting period across companies.
    #
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_quarterly_results_quarter
        ON quarterly_results(quarter)
    """)

    connection.commit()

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    rows = cursor.execute("""
        SELECT
            name,
            sql
        FROM sqlite_master
        WHERE type = 'index'
        AND tbl_name = 'quarterly_results'
        ORDER BY name
    """).fetchall()

    connection.close()

    print(
        "=========================================="
    )

    print(
        "WEEK 4 FINANCIAL DATABASE INDEXES"
    )

    print(
        "=========================================="
    )

    print(
        "\nIndexes on quarterly_results:"
    )

    for name, sql in rows:

        print(
            f"\n{name}"
        )

        if sql:

            print(
                f"  {sql}"
            )

        else:

            print(
                "  SQLite automatic index"
            )

    print(
        "\n=========================================="
    )

    print(
        "✓ FINANCIAL INDEX MIGRATION COMPLETE"
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":

    add_indexes()