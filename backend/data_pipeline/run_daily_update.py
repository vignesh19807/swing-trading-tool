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
from backend.data_pipeline.failure_report import (
    record_failure,
    mark_resolved,
)
from backend.data_pipeline.stock_universe import STOCK_UNIVERSE


# ============================================================
# STAGE EXECUTION
# ============================================================

def run_stage(stage_name, stage_function):
    """
    Execute one pipeline stage safely.

    Returns:
        True  -> stage completed successfully
        False -> stage failed
    """

    print("\n" + "=" * 60)
    print(stage_name)
    print("=" * 60)

    try:
        result = stage_function()

        # Some existing loaders return None on success.
        # Treat only an explicit False as failure.
        if result is False:
            print(
                f"\n❌ {stage_name} FAILED"
            )

            print(
                "Stage returned failure status."
            )

            return False

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

    Failures are also persisted for later recovery.
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

            record_failure(
                "INVALID_SYMBOL",
                "technical",
                "Invalid stock symbol",
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

                reason = "no records processed"

                failed_stocks.append(
                    f"{symbol}: {reason}"
                )

                record_failure(
                    symbol,
                    "technical",
                    reason,
                )

                print(
                    f"❌ {symbol} failed"
                )

                continue

            successful += 1
            total_records += records

            # If this stock previously failed and now succeeds,
            # mark its previous failure as resolved.
            mark_resolved(
                symbol,
                "technical",
            )

            print(
                f"✓ {symbol} completed "
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