"""
50-Stock Financial Data Loader
==============================

Week 3 Data Engineering Layer

Pipeline:

    50-stock universe
            ↓
    Financial Data Collector
            ↓
    Financial Validator
            ↓
    Company Mapping
            ↓
    SQLite quarterly_results

This module does NOT calculate financial scores.
"""

import sqlite3
from pathlib import Path

from backend.data_pipeline.stock_universe import (
    STOCK_UNIVERSE,
)

from backend.data_pipeline.financial_data import (
    fetch_financial_data,
)

from backend.data_pipeline.financial_validator import (
    validate_financial_data,
)

from backend.data_pipeline.insert_financial_data import (
    get_company_id,
    insert_financial_records,
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
# MAIN PIPELINE
# ============================================================

def main():

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("50-STOCK FINANCIAL DATA LOAD")
    print("==========================================")

    print(
        f"\nStock universe size: "
        f"{len(STOCK_UNIVERSE)}"
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

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    total_stocks = len(STOCK_UNIVERSE)

    successful = 0
    failed = 0

    total_inserted = 0
    total_skipped = 0

    # --------------------------------------------------------
    # Process each stock
    # --------------------------------------------------------

    for index, stock in enumerate(
        STOCK_UNIVERSE,
        start=1
    ):

        # ----------------------------------------------------
        # Support both dictionary and list-style universes
        # ----------------------------------------------------

        if isinstance(stock, dict):

            symbol = stock.get(
                "symbol"
            )

        else:

            symbol = str(stock)

        if not symbol:

            print(
                f"\n❌ Stock #{index}: "
                "Invalid symbol"
            )

            failed += 1
            continue

        symbol = symbol.upper().strip()

        print(
            "\n------------------------------------------"
        )

        print(
            f"[{index}/{total_stocks}] "
            f"Processing {symbol}"
        )

        print(
            "------------------------------------------"
        )

        # ----------------------------------------------------
        # Find company
        # ----------------------------------------------------

        company_id = get_company_id(
            cursor,
            symbol
        )

        if company_id is None:

            print(
                f"❌ {symbol}: "
                "Company not found in database"
            )

            failed += 1
            continue

        print(
            f"✓ Company ID: {company_id}"
        )

        # ----------------------------------------------------
        # Fetch financial data
        # ----------------------------------------------------

        try:

            data = fetch_financial_data(
                symbol
            )

        except Exception as error:

            print(
                f"❌ {symbol}: "
                f"Collection error: {error}"
            )

            failed += 1
            continue

        if data is None or data.empty:

            print(
                f"❌ {symbol}: "
                "No financial data returned"
            )

            failed += 1
            continue

        print(
            f"✓ Records collected: "
            f"{len(data)}"
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
                f"❌ {symbol}: "
                "Validation failed"
            )

            for error in report["errors"]:

                print(
                    f"   ❌ {error}"
                )

            failed += 1
            continue

        # ----------------------------------------------------
        # Show warnings
        # ----------------------------------------------------

        warning_count = len(
            report["warnings"]
        )

        if warning_count > 0:

            print(
                f"⚠ Warnings: "
                f"{warning_count}"
            )

        else:

            print(
                "✓ No data quality warnings"
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
            f"✓ Inserted: {inserted}"
        )

        print(
            f"✓ Skipped : {skipped}"
        )

    # --------------------------------------------------------
    # Commit all successful records
    # --------------------------------------------------------

    connection.commit()

    # --------------------------------------------------------
    # Final database count
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        """
    )

    total_database_records = (
        cursor.fetchone()[0]
    )

    connection.close()

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "WEEK 3 FINANCIAL DATA LOAD COMPLETE"
    )

    print(
        "=========================================="
    )

    print(
        f"Stocks processed : {total_stocks}"
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
        f"{total_database_records}"
    )

    print(
        "------------------------------------------"
    )

    if failed == 0:

        print(
            "🎉 ALL 50 STOCKS PROCESSED SUCCESSFULLY"
        )

    else:

        print(
            "⚠ SOME STOCKS REQUIRE REVIEW"
        )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()