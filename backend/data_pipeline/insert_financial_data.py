"""
Financial Data Database Insertion
=================================

Week 3 Data Engineering Layer

Responsibilities:
    1. Fetch financial data
    2. Validate financial data
    3. Map stock symbols to companies
    4. Insert financial records into quarterly_results
    5. Prevent duplicate company/quarter records
    6. Preserve missing values as NULL

This module does NOT calculate financial scores.
"""

import sqlite3
from pathlib import Path

from backend.data_pipeline.financial_data import (
    fetch_financial_data,
)

from backend.data_pipeline.financial_validator import (
    validate_financial_data,
)


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
# TEST STOCKS
# ============================================================

TEST_STOCKS = [
    "INFY",
    "TCS",
    "RELIANCE",
    "WIPRO",
    "HDFCBANK",
]


# ============================================================
# HELPER
# ============================================================

def clean_value(value):
    """
    Convert pandas NaN values to None so SQLite stores them
    as NULL.

    Normal numerical values are converted to float.
    """

    if value is None:
        return None

    try:

        if value != value:
            return None

        return float(value)

    except (TypeError, ValueError):

        return None


# ============================================================
# COMPANY LOOKUP
# ============================================================

def get_company_id(cursor, symbol):
    """
    Find the company_id for an NSE symbol.
    """

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE symbol = ?
        """,
        (symbol.upper(),)
    )

    result = cursor.fetchone()

    if result is None:

        return None

    return result[0]


# ============================================================
# INSERT FINANCIAL RECORDS
# ============================================================

def insert_financial_records(
    cursor,
    company_id,
    data
):
    """
    Insert normalized financial records.

    Duplicate company/quarter records are ignored.
    Missing values are stored as NULL.
    """

    inserted = 0
    skipped = 0

    for _, row in data.iterrows():

        cursor.execute(
            """
            INSERT OR IGNORE INTO quarterly_results (
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                row["quarter"],
                clean_value(row["revenue"]),
                clean_value(row["net_profit"]),
                clean_value(row["eps"]),
                clean_value(row["roe"]),
                clean_value(row["roce"]),
                clean_value(row["debt_equity"]),
                clean_value(
                    row["operating_margin"]
                ),
                clean_value(
                    row["net_margin"]
                ),
            )
        )

        if cursor.rowcount == 1:

            inserted += 1

        else:

            skipped += 1

    return inserted, skipped


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "FINANCIAL DATABASE INSERTION"
    )

    print(
        "=========================================="
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Enable foreign keys
    # --------------------------------------------------------

    cursor.execute(
        "PRAGMA foreign_keys = ON"
    )

    total_inserted = 0
    total_skipped = 0
    successful = 0
    failed = 0

    # --------------------------------------------------------
    # Process test stocks
    # --------------------------------------------------------

    for symbol in TEST_STOCKS:

        print(
            "\n------------------------------------------"
        )

        print(
            f"Processing {symbol}"
        )

        print(
            "------------------------------------------"
        )

        # ----------------------------------------------------
        # Company lookup
        # ----------------------------------------------------

        company_id = get_company_id(
            cursor,
            symbol
        )

        if company_id is None:

            print(
                f"❌ Company not found in database: "
                f"{symbol}"
            )

            failed += 1
            continue

        print(
            f"✓ Company ID: {company_id}"
        )

        # ----------------------------------------------------
        # Fetch financial data
        # ----------------------------------------------------

        data = fetch_financial_data(
            symbol
        )

        if data is None:

            print(
                f"❌ Financial collection failed: "
                f"{symbol}"
            )

            failed += 1
            continue

        print(
            f"✓ Records collected: {len(data)}"
        )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        valid, report = (
            validate_financial_data(
                symbol,
                data
            )
        )

        if not valid:

            print(
                f"❌ Validation failed: {symbol}"
            )

            for error in report["errors"]:

                print(
                    f"   {error}"
                )

            failed += 1
            continue

        # ----------------------------------------------------
        # Display warnings
        # ----------------------------------------------------

        if report["warnings"]:

            print(
                "⚠ Data quality warnings:"
            )

            for warning in report["warnings"]:

                print(
                    f"   {warning}"
                )

        # ----------------------------------------------------
        # Insert
        # ----------------------------------------------------

        inserted, skipped = (
            insert_financial_records(
                cursor,
                company_id,
                data
            )
        )

        total_inserted += inserted
        total_skipped += skipped

        successful += 1

        print(
            f"✓ Inserted : {inserted}"
        )

        print(
            f"✓ Skipped  : {skipped}"
        )

    # --------------------------------------------------------
    # Commit
    # --------------------------------------------------------

    connection.commit()

    # --------------------------------------------------------
    # Database verification
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        """
    )

    total_records = cursor.fetchone()[0]

    connection.close()

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL DATABASE INSERTION COMPLETE"
    )

    print(
        "=========================================="
    )

    print(
        f"Stocks processed : {len(TEST_STOCKS)}"
    )

    print(
        f"Successful       : {successful}"
    )

    print(
        f"Failed           : {failed}"
    )

    print(
        f"Records inserted : {total_inserted}"
    )

    print(
        f"Records skipped  : {total_skipped}"
    )

    print(
        f"Total financial records in DB: "
        f"{total_records}"
    )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()