"""
Week 9 - Automated Daily Data Update Runner

Purpose:
    Provide one repeatable entry point for the daily Data Engineering
    refresh workflow.

Flow:
    1. Market data update
    2. Financial data update
    3. Technical indicator update
    4. Data validation
    5. Final execution status

This module does NOT:
    - calculate trading decisions
    - generate BUY/SELL signals
    - calculate financial scores
    - perform portfolio decisions
"""

from datetime import datetime, timezone

from backend.data_pipeline.load_stock_data import main as update_market_data
from backend.data_pipeline.load_financial_data import main as update_financial_data
from backend.data_pipeline.technical_indicator_service import (
    save_technical_indicators,
)
from backend.data_pipeline.stock_universe import STOCK_UNIVERSE


# ============================================================
# STAGE EXECUTION
# ============================================================

def run_stage(stage_name, stage_function):
    """
    Execute one pipeline stage safely.

    Returns:
        True  -> stage completed
        False -> stage failed
    """

    print("\n" + "=" * 60)
    print(stage_name)
    print("=" * 60)

    try:
        stage_function()

        print(
            f"\n✓ {stage_name} completed successfully"
        )

        return True

    except Exception as error:

        print(
            f"\n❌ {stage_name} FAILED"
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

    Each stock is processed independently so that one stock failure
    does not stop the remaining stocks.
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

        if isinstance(stock, dict):
            symbol = stock.get("symbol")
        else:
            symbol = str(stock)

        if not symbol:
            failed += 1
            failed_stocks.append(
                "INVALID_SYMBOL"
            )
            continue

        symbol = symbol.upper().strip()

        print(
            f"\n[{index}/{total_stocks}] "
            f"Processing {symbol}..."
        )

        try:

            records = save_technical_indicators(
                symbol
            )

            if records <= 0:

                failed += 1

                failed_stocks.append(
                    f"{symbol}: no records processed"
                )

                print(
                    f"❌ {symbol} failed"
                )

                continue

            successful += 1
            total_records += records

            print(
                f"✓ {symbol} completed "
                f"({records} records)"
            )

        except Exception as error:

            failed += 1

            failed_stocks.append(
                f"{symbol}: {error}"
            )

            print(
                f"❌ {symbol} failed: {error}"
            )

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

    return failed == 0


# ============================================================
# VALIDATION
# ============================================================

def run_validation():
    """
    Run the existing database validation after updates.

    The validation module is imported here rather than duplicated.
    """

    from backend.database.verify_data import main as verify_database

    try:

        result = verify_database()

        return result is not False

    except Exception as error:

        print(
            f"\n❌ Validation error: {error}"
        )

        return False


# ============================================================
# FINAL SUMMARY
# ============================================================

def print_final_summary(
    start_time,
    statuses,
):
    """
    Print the complete Week 9 execution summary.
    """

    end_time = datetime.now(timezone.utc)

    duration = (
        end_time - start_time
    ).total_seconds()

    print("\n" + "=" * 60)
    print("WEEK 9 DAILY UPDATE SUMMARY")
    print("=" * 60)

    print(
        f"Start time : {start_time.isoformat()}"
    )

    print(
        f"End time   : {end_time.isoformat()}"
    )

    print(
        f"Duration   : {duration:.2f} seconds"
    )

    print("\nStage Status")
    print("-" * 60)

    for stage, status in statuses.items():

        if status == "PASSED":
            symbol = "✓"

        elif status == "FAILED":
            symbol = "❌"

        elif status == "SKIPPED":
            symbol = "⏭"

        else:
            symbol = "•"

        print(
            f"{stage:<35} "
            f"{symbol} {status}"
        )

    print("-" * 60)

    overall_success = all(
        status == "PASSED"
        for status in statuses.values()
    )

    if overall_success:

        print(
            "\n✓ Overall Status: PASSED"
        )

        print(
            "\n🎉 WEEK 9 DAILY UPDATE PASSED"
        )

    else:

        print(
            "\n❌ Overall Status: FAILED"
        )

        print(
            "\n⚠ WEEK 9 DAILY UPDATE REQUIRES REVIEW"
        )

    print("=" * 60)

    return overall_success


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = datetime.now(
        timezone.utc
    )

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 9 - AUTOMATED DAILY DATA UPDATE")
    print("=" * 60)

    print(
        f"\nRun started: "
        f"{start_time.isoformat()}"
    )

    statuses = {
        "Market Data Update": "PENDING",
        "Financial Data Update": "PENDING",
        "Technical Data Update": "PENDING",
        "Database Validation": "PENDING",
    }

    # ========================================================
    # STEP 1 — MARKET DATA
    # ========================================================

    market_success = run_stage(
        "STEP 1/4 — MARKET DATA UPDATE",
        update_market_data,
    )

    if market_success:

        statuses[
            "Market Data Update"
        ] = "PASSED"

    else:

        statuses[
            "Market Data Update"
        ] = "FAILED"

        statuses[
            "Financial Data Update"
        ] = "SKIPPED"

        statuses[
            "Technical Data Update"
        ] = "SKIPPED"

        statuses[
            "Database Validation"
        ] = "SKIPPED"

        return print_final_summary(
            start_time,
            statuses,
        )

    # ========================================================
    # STEP 2 — FINANCIAL DATA
    # ========================================================

    financial_success = run_stage(
        "STEP 2/4 — FINANCIAL DATA UPDATE",
        update_financial_data,
    )

    if financial_success:

        statuses[
            "Financial Data Update"
        ] = "PASSED"

    else:

        statuses[
            "Financial Data Update"
        ] = "FAILED"

    # ========================================================
    # STEP 3 — TECHNICAL DATA
    # ========================================================

    technical_success = update_technical_data()

    if technical_success:

        statuses[
            "Technical Data Update"
        ] = "PASSED"

    else:

        statuses[
            "Technical Data Update"
        ] = "FAILED"

    # ========================================================
    # STEP 4 — VALIDATION
    # ========================================================

    validation_success = run_stage(
        "STEP 4/4 — DATABASE VALIDATION",
        run_validation,
    )

    if validation_success:

        statuses[
            "Database Validation"
        ] = "PASSED"

    else:

        statuses[
            "Database Validation"
        ] = "FAILED"

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