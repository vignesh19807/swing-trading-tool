"""
Week 11 - Automated Daily Data Update Runner
============================================

Purpose:
    Provide one repeatable entry point for the Data Engineering
    refresh and validation workflow.

Flow:
    1. Market data update
    2. Financial data update
    3. Technical indicator update
    4. Database validation
    5. Final execution status

Responsibilities:
    - Orchestrate existing Data Engineering services
    - Isolate stock-level technical failures
    - Record failed stocks
    - Resolve previously failed stocks after successful retry
    - Validate database coverage
    - Provide a final pipeline status

This module does NOT:
    - calculate trading decisions
    - generate BUY/SELL signals
    - calculate financial scores
    - calculate opportunity scores
    - perform portfolio decisions
    - modify the Technical Engine
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.data_pipeline.load_stock_data import (
    main as update_market_data,
)

from backend.data_pipeline.load_financial_data import (
    main as update_financial_data,
)

from backend.data_pipeline.technical_indicator_service import (
    save_technical_indicators,
)

from backend.data_pipeline.failure_report import (
    record_failure,
    mark_resolved,
)

from backend.data_pipeline.stock_universe import (
    STOCK_UNIVERSE,
)


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


# ============================================================
# STAGE EXECUTION
# ============================================================

def run_stage(stage_name, stage_function):
    """
    Execute one pipeline stage safely.

    Existing loaders may return None on success.
    Therefore only an explicit False is treated as failure.

    Returns
    -------
    bool
        True  -> stage completed successfully
        False -> stage failed
    """

    print("\n" + "=" * 60)
    print(stage_name)
    print("=" * 60)

    try:
        result = stage_function()

        if result is False:

            print(
                f"\n[FAIL] {stage_name}"
            )

            print(
                "Stage returned failure status."
            )

            return False

        print(
            f"\n[OK] {stage_name} completed successfully"
        )

        return True

    except Exception as error:

        print(
            f"\n[FAIL] {stage_name}"
        )

        print(
            f"Error: {error}"
        )

        return False


# ============================================================
# TECHNICAL UPDATE
# ============================================================

def update_technical_data():
    """
    Refresh technical indicators for the complete stock universe.

    Each stock is processed independently.

    One stock failure does not stop the remaining stocks.

    Failed stocks are recorded for later recovery.

    Returns
    -------
    bool
        True when every stock succeeds.
        False when one or more stocks fail.
    """

    successful = 0
    failed = 0
    total_records = 0

    failed_stocks = []

    total_stocks = len(STOCK_UNIVERSE)

    print(
        f"\nStocks in universe: {total_stocks}"
    )

    for index, stock in enumerate(
        STOCK_UNIVERSE,
        start=1,
    ):

        # ----------------------------------------------------
        # Resolve symbol
        # ----------------------------------------------------

        if isinstance(stock, dict):

            symbol = stock.get("symbol")

        else:

            symbol = str(stock)

        if not symbol:

            failed += 1

            failed_stocks.append(
                "INVALID_SYMBOL"
            )

            record_failure(
                "INVALID_SYMBOL",
                "technical",
                "Invalid stock symbol",
            )

            print(
                f"\n[{index}/{total_stocks}] "
                "[FAIL] Invalid stock symbol"
            )

            continue

        symbol = (
            symbol
            .upper()
            .strip()
        )

        print(
            f"\n[{index}/{total_stocks}] "
            f"Processing {symbol}..."
        )

        # ----------------------------------------------------
        # Process one stock
        # ----------------------------------------------------

        try:

            records = save_technical_indicators(
                symbol
            )

            if records <= 0:

                failed += 1

                reason = (
                    "no records processed"
                )

                failed_stocks.append(
                    f"{symbol}: {reason}"
                )

                record_failure(
                    symbol,
                    "technical",
                    reason,
                )

                print(
                    f"[FAIL] {symbol}: {reason}"
                )

                continue

            # ------------------------------------------------
            # Successful stock
            # ------------------------------------------------

            successful += 1

            total_records += records

            mark_resolved(
                symbol,
                "technical",
            )

            print(
                f"[OK] {symbol} completed "
                f"({records} records)"
            )

        except Exception as error:

            failed += 1

            reason = str(error)

            failed_stocks.append(
                f"{symbol}: {reason}"
            )

            record_failure(
                symbol,
                "technical",
                reason,
            )

            print(
                f"[FAIL] {symbol}: {error}"
            )

            # Failure isolation:
            # continue processing remaining stocks.
            continue

    # ========================================================
    # TECHNICAL SUMMARY
    # ========================================================

    print(
        "\n" + "-" * 60
    )

    print(
        "TECHNICAL UPDATE SUMMARY"
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
        f"Total records    : {total_records}"
    )

    if failed_stocks:

        print(
            "\nFailed stocks:"
        )

        for failure in failed_stocks:

            print(
                f"  - {failure}"
            )

    else:

        print(
            "\nFailed stocks: NONE"
        )

    return failed == 0


# ============================================================
# DATABASE VALIDATION
# ============================================================

def run_validation():
    """
    Validate basic database readiness for the complete
    stock universe.

    Checks:
        - companies
        - daily_prices
        - quarterly_results
        - technical_indicators

    Every stock must have:
        - market data
        - financial data
        - technical data

    Returns
    -------
    bool
        True when all stocks have required database coverage.
        False otherwise.
    """

    print(
        "\n" + "=" * 60
    )

    print(
        "WEEK 11 - DATABASE READINESS VALIDATION"
    )

    print(
        "=" * 60
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        # ----------------------------------------------------
        # Table-level counts
        # ----------------------------------------------------

        tables = [
            "companies",
            "daily_prices",
            "quarterly_results",
            "technical_indicators",
        ]

        print(
            "\nDATABASE COUNTS"
        )

        for table in tables:

            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(
                f"{table:<25} {count:>8}"
            )

        # ----------------------------------------------------
        # Per-stock coverage
        # ----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "PER-STOCK DATA COVERAGE"
        )

        print(
            "=" * 60
        )

        failures = []

        for stock in STOCK_UNIVERSE:

            if isinstance(stock, dict):

                symbol = stock.get("symbol")

            else:

                symbol = str(stock)

            if not symbol:

                failures.append(
                    "INVALID_SYMBOL"
                )

                continue

            symbol = (
                symbol
                .upper()
                .strip()
            )

            # ------------------------------------------------
            # Company ID
            # ------------------------------------------------

            row = connection.execute(
                """
                SELECT id
                FROM companies
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()

            if row is None:

                failures.append(
                    f"{symbol}: company missing"
                )

                print(
                    f"{symbol:<12} "
                    "company=MISSING"
                )

                continue

            company_id = row[0]

            # ------------------------------------------------
            # Market count
            # ------------------------------------------------

            market_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM daily_prices
                WHERE company_id = ?
                """,
                (company_id,),
            ).fetchone()[0]

            # ------------------------------------------------
            # Financial count
            # ------------------------------------------------

            financial_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM quarterly_results
                WHERE company_id = ?
                """,
                (company_id,),
            ).fetchone()[0]

            # ------------------------------------------------
            # Technical count
            # ------------------------------------------------

            technical_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM technical_indicators
                WHERE company_id = ?
                """,
                (company_id,),
            ).fetchone()[0]

            # ------------------------------------------------
            # Coverage status
            # ------------------------------------------------

            status = "OK"

            if market_count == 0:

                status = "FAIL"

            if financial_count == 0:

                status = "FAIL"

            if technical_count == 0:

                status = "FAIL"

            print(
                f"{symbol:<12} "
                f"market={market_count:>4} "
                f"financial={financial_count:>3} "
                f"technical={technical_count:>4} "
                f"status={status}"
            )

            if status == "FAIL":

                failures.append(
                    f"{symbol}: "
                    f"market={market_count}, "
                    f"financial={financial_count}, "
                    f"technical={technical_count}"
                )

        # ----------------------------------------------------
        # Validation result
        # ----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "VALIDATION RESULT"
        )

        print(
            "=" * 60
        )

        print(
            f"Stocks checked : {len(STOCK_UNIVERSE)}"
        )

        print(
            f"Failures       : {len(failures)}"
        )

        if failures:

            print(
                "\nValidation failures:"
            )

            for failure in failures:

                print(
                    f"  - {failure}"
                )

            return False

        print(
            "\nALL STOCKS HAVE REQUIRED DATABASE COVERAGE"
        )

        return True

    finally:

        connection.close()


# ============================================================
# FINAL SUMMARY
# ============================================================

def print_final_summary(
    start_time,
    statuses,
):
    """
    Print final execution summary.

    Returns
    -------
    bool
        True when every pipeline stage passed.
    """

    end_time = datetime.now(
        timezone.utc
    )

    elapsed = (
        end_time - start_time
    ).total_seconds()

    print(
        "\n" + "=" * 60
    )

    print(
        "WEEK 11 - FINAL DATA ENGINEERING SUMMARY"
    )

    print(
        "=" * 60
    )

    for stage, status in statuses.items():

        print(
            f"{stage:<30} {status}"
        )

    print(
        "-" * 60
    )

    overall_success = all(
        status == "PASSED"
        for status in statuses.values()
    )

    print(
        f"Elapsed time : {elapsed:.2f} seconds"
    )

    if overall_success:

        print(
            "\n[OK] ALL WEEK 11 DATA ENGINEERING STAGES PASSED"
        )

    else:

        print(
            "\n[FAIL] WEEK 11 DATA ENGINEERING REQUIRES REVIEW"
        )

    print(
        "=" * 60
    )

    return overall_success


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    """
    Execute the complete Data Engineering refresh workflow.

    Pipeline:

        Market Data
            ↓
        Financial Data
            ↓
        Technical Data
            ↓
        Database Validation
            ↓
        Final Summary

    Returns
    -------
    bool
        True when every stage passes.
    """

    start_time = datetime.now(
        timezone.utc
    )

    statuses = {}

    print(
        "=" * 60
    )

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "WEEK 11 - DATA ENGINEERING DAILY PIPELINE"
    )

    print(
        "=" * 60
    )

    # ========================================================
    # STEP 1 - MARKET DATA
    # ========================================================

    market_success = run_stage(
        "STEP 1/4 - MARKET DATA UPDATE",
        update_market_data,
    )

    statuses[
        "Market Data Update"
    ] = (
        "PASSED"
        if market_success
        else "FAILED"
    )

    # ========================================================
    # STEP 2 - FINANCIAL DATA
    # ========================================================

    financial_success = run_stage(
        "STEP 2/4 - FINANCIAL DATA UPDATE",
        update_financial_data,
    )

    statuses[
        "Financial Data Update"
    ] = (
        "PASSED"
        if financial_success
        else "FAILED"
    )

    # ========================================================
    # STEP 3 - TECHNICAL DATA
    # ========================================================

    technical_success = run_stage(
        "STEP 3/4 - TECHNICAL DATA UPDATE",
        update_technical_data,
    )

    statuses[
        "Technical Data Update"
    ] = (
        "PASSED"
        if technical_success
        else "FAILED"
    )

    # ========================================================
    # STEP 4 - DATABASE VALIDATION
    # ========================================================

    validation_success = run_stage(
        "STEP 4/4 - DATABASE VALIDATION",
        run_validation,
    )

    statuses[
        "Database Validation"
    ] = (
        "PASSED"
        if validation_success
        else "FAILED"
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    return print_final_summary(
        start_time,
        statuses,
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)