"""
Week 10 - Complete Data Validation Pipeline

Purpose:
    Run the complete Data Engineering validation pipeline
    through one final validation command.

Validation stages:
    1. Financial data validation
    2. Sector / industry validation
    3. Market data validation
    4. Consolidated database audit
    5. Market data -> Logic Engineer handoff
    6. Financial data -> Logic Engineer handoff

This module does NOT:
    - collect data
    - calculate scores
    - make trading decisions
    - modify database records
"""

from backend.data_pipeline.verify_financial_data import (
    main as verify_financial,
)

from backend.data_pipeline.sector_industry_audit import (
    main as sector_audit,
)

from backend.data_pipeline.consolidated_quality_report import (
    build_report,
    print_report,
)

from backend.data_pipeline.test_data_handoff import (
    main as test_market_handoff,
)

from backend.data_pipeline.test_financial_handoff import (
    main as test_financial_handoff,
)


def run_check(name, function):
    """Run one validation safely."""

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    try:
        result = function()

        if result is False:
            print(f"\n[FAIL] {name}")
            return False

        print(f"\n[PASS] {name}")
        return True

    except Exception as error:
        print(f"\n[FAIL] {name}")
        print(f"Error: {error}")
        return False


def run_consolidated_audit():
    """Run the consolidated database quality audit."""

    try:
        report = build_report()
        print_report(report)

        universe_ok = report["universe"]["passed"]

        market = report["market_data"]
        financial = report["financial_data"]

        market_ok = (
            market["duplicate_groups"] == 0
            and market["orphan_records"] == 0
        )

        financial_ok = (
            financial["duplicate_groups"] == 0
            and financial["orphan_records"] == 0
        )

        return (
            universe_ok
            and market_ok
            and financial_ok
        )

    except Exception as error:
        print("\n[FAIL] CONSOLIDATED AUDIT")
        print(f"Error: {error}")
        return False


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 10 - COMPLETE DATA VALIDATION")
    print("=" * 60)

    results = {}

    # --------------------------------------------------------
    # 1. Financial validation
    # --------------------------------------------------------

    results["Financial Validation"] = run_check(
        "1/6 - FINANCIAL DATA VALIDATION",
        verify_financial,
    )

    # --------------------------------------------------------
    # 2. Sector / Industry validation
    # --------------------------------------------------------

    results["Sector / Industry Validation"] = run_check(
        "2/6 - SECTOR / INDUSTRY VALIDATION",
        sector_audit,
    )

    # --------------------------------------------------------
    # 3. Market validation
    # --------------------------------------------------------

    results["Market Data Validation"] = run_check(
        "3/6 - MARKET DATA VALIDATION",
        validate_market_data,
    )

    # --------------------------------------------------------
    # 4. Consolidated database audit
    # --------------------------------------------------------

    results["Consolidated Database Audit"] = run_check(
        "4/6 - CONSOLIDATED DATABASE AUDIT",
        run_consolidated_audit,
    )

    # --------------------------------------------------------
    # 5. Market -> Logic handoff
    # --------------------------------------------------------

    results["Market -> Logic Handoff"] = run_check(
        "5/6 - MARKET DATA -> LOGIC HANDOFF",
        test_market_handoff,
    )

    # --------------------------------------------------------
    # 6. Financial -> Logic handoff
    # --------------------------------------------------------

    results["Financial -> Logic Handoff"] = run_check(
        "6/6 - FINANCIAL DATA -> LOGIC HANDOFF",
        test_financial_handoff,
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("WEEK 10 DATA VALIDATION SUMMARY")
    print("=" * 60)

    for name, passed in results.items():

        status = "PASS" if passed else "FAIL"

        print(
            f"{name:<40} {status}"
        )

    overall_passed = all(results.values())

    print("-" * 60)

    if overall_passed:

        print("OVERALL STATUS: PASS")
        print("WEEK 10 VALIDATED DATA PIPELINE PASSED")

    else:

        print("OVERALL STATUS: FAIL")
        print("WEEK 10 DATA PIPELINE REQUIRES REVIEW")

    print("=" * 60)

    return overall_passed


def validate_market_data():
    """
    Validate market data for all stocks.

    This function is imported from the existing Week 10
    implementation when the module is executed.
    """

    import sqlite3
    from pathlib import Path

    from backend.data_pipeline.stock_universe import (
        STOCK_UNIVERSE,
    )

    project_root = Path(__file__).resolve().parents[2]

    database_path = (
        project_root
        / "database"
        / "swing_trading.db"
    )

    connection = sqlite3.connect(database_path)

    try:

        total_stocks = len(STOCK_UNIVERSE)

        stocks_with_data = 0
        failed_stocks = []

        for stock in STOCK_UNIVERSE:

            if isinstance(stock, dict):
                symbol = stock.get("symbol")
            else:
                symbol = str(stock)

            if not symbol:

                failed_stocks.append(
                    "INVALID_SYMBOL"
                )

                continue

            symbol = symbol.upper().strip()

            row = connection.execute(
                """
                SELECT
                    COUNT(*),

                    SUM(
                        CASE
                            WHEN open IS NULL
                              OR high IS NULL
                              OR low IS NULL
                              OR close IS NULL
                              OR volume IS NULL
                            THEN 1
                            ELSE 0
                        END
                    ),

                    SUM(
                        CASE
                            WHEN high < low
                              OR high < open
                              OR high < close
                              OR low > open
                              OR low > close
                            THEN 1
                            ELSE 0
                        END
                    )

                FROM daily_prices dp

                JOIN companies c
                    ON c.id = dp.company_id

                WHERE c.symbol = ?
                """,
                (symbol,),
            ).fetchone()

            record_count = row[0] or 0
            missing_values = row[1] or 0
            invalid_ohlc = row[2] or 0

            if record_count == 0:

                failed_stocks.append(
                    f"{symbol}: no market records"
                )

                continue

            if missing_values > 0:

                failed_stocks.append(
                    f"{symbol}: {missing_values} "
                    "records contain missing values"
                )

                continue

            if invalid_ohlc > 0:

                failed_stocks.append(
                    f"{symbol}: {invalid_ohlc} "
                    "invalid OHLC records"
                )

                continue

            stocks_with_data += 1

        duplicate_groups = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT company_id, date
                FROM daily_prices
                GROUP BY company_id, date
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        orphan_records = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices dp

            LEFT JOIN companies c
                ON c.id = dp.company_id

            WHERE c.id IS NULL
            """
        ).fetchone()[0]

    finally:

        connection.close()

    print("\nMARKET DATA - ALL STOCKS")
    print("-" * 60)

    print(
        f"Stocks expected       : {total_stocks}"
    )

    print(
        f"Stocks with data      : {stocks_with_data}"
    )

    print(
        f"Stocks failed         : {len(failed_stocks)}"
    )

    print(
        f"Duplicate groups      : {duplicate_groups}"
    )

    print(
        f"Orphan records        : {orphan_records}"
    )

    if failed_stocks:

        print("\nMarket-data failures:")

        for failure in failed_stocks:

            print(
                f"  - {failure}"
            )

    passed = (
        stocks_with_data == total_stocks
        and not failed_stocks
        and duplicate_groups == 0
        and orphan_records == 0
    )

    if passed:

        print(
            "\n[PASS] MARKET DATA VALIDATION PASSED"
        )

    else:

        print(
            "\n[FAIL] MARKET DATA VALIDATION FAILED"
        )

    return passed


if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)