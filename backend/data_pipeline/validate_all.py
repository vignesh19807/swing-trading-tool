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

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.data_pipeline.stock_universe import STOCK_UNIVERSE
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)

LOG_FILE = REPORT_DIR / "week10_validation.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("week10_validation")


def run_check(name, function):
    """Run one validation safely and log the result."""

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    logger.info("START: %s", name)

    try:
        result = function()

        if result is False:
            print(f"\n[FAIL] {name}")
            logger.error("FAIL: %s", name)
            return False

        print(f"\n[PASS] {name}")
        logger.info("PASS: %s", name)
        return True

    except Exception as error:
        print(f"\n[FAIL] {name}")
        print(f"Error: {error}")

        logger.exception("ERROR: %s", name)

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
        "1/7 - FINANCIAL DATA VALIDATION",
        verify_financial,
    )

    # --------------------------------------------------------
    # 2. Sector / Industry validation
    # --------------------------------------------------------

    results["Sector / Industry Validation"] = run_check(
        "2/7 - SECTOR / INDUSTRY VALIDATION",
        sector_audit,
    )

    # --------------------------------------------------------
    # 3. Market validation
    # --------------------------------------------------------

    results["Market Data Validation"] = run_check(
        "3/7 - MARKET DATA VALIDATION",
        run_market_validation,
    )

    # --------------------------------------------------------
    # 4. Cross-Dataset consistency
    # --------------------------------------------------------

    results["Cross-Dataset Consistency"] = run_check(
        "4/7 - CROSS-DATASET CONSISTENCY",
        validate_cross_dataset_consistency,
    )

    # --------------------------------------------------------
    # 5. Consolidated database audit
    # --------------------------------------------------------

    results["Consolidated Database Audit"] = run_check(
        "5/7 - CONSOLIDATED DATABASE AUDIT",
        run_consolidated_audit,
    )

    # --------------------------------------------------------
    # 6. Market -> Logic handoff
    # --------------------------------------------------------

    results["Market -> Logic Handoff"] = run_check(
        "6/7 - MARKET DATA -> LOGIC HANDOFF",
        test_market_handoff,
    )

    # --------------------------------------------------------
    # 7. Financial -> Logic handoff
    # --------------------------------------------------------

    results["Financial -> Logic Handoff"] = run_check(
        "7/7 - FINANCIAL DATA -> LOGIC HANDOFF",
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


def validate_market_date_gaps():
    """
    Detect unexpected missing trading dates.

    Uses dates present across the 50-stock dataset as the
    reference trading calendar. This avoids treating weekends
    and exchange holidays as missing data.
    """

    project_root = Path(__file__).resolve().parents[2]

    database_path = (
        project_root
        / "database"
        / "swing_trading.db"
    )

    connection = sqlite3.connect(database_path)

    try:

        universe_symbols = []

        for stock in STOCK_UNIVERSE:

            if isinstance(stock, dict):
                symbol = stock.get("symbol")
            else:
                symbol = str(stock)

            if symbol:
                universe_symbols.append(
                    symbol.upper().strip()
                )

        # Reference dates: dates on which at least one
        # stock in the universe has market data.
        reference_dates = {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT dp.date
                FROM daily_prices dp
                INNER JOIN companies c
                    ON c.id = dp.company_id
                WHERE c.symbol IN (
                    SELECT symbol FROM companies
                )
                ORDER BY dp.date
                """
            ).fetchall()
        }

        if not reference_dates:
            print("\n[FAIL] No market dates available")
            logger.error("No market dates available")
            return False

        total_gaps = 0
        stocks_with_gaps = []

        for symbol in universe_symbols:

            rows = connection.execute(
                """
                SELECT DISTINCT dp.date
                FROM daily_prices dp
                INNER JOIN companies c
                    ON c.id = dp.company_id
                WHERE c.symbol = ?
                ORDER BY dp.date
                """,
                (symbol,),
            ).fetchall()

            stock_dates = {
                row[0]
                for row in rows
            }

            missing_dates = (
                reference_dates - stock_dates
            )

            if missing_dates:

                total_gaps += len(missing_dates)

                stocks_with_gaps.append(
                    {
                        "symbol": symbol,
                        "missing_count": len(missing_dates),
                        "dates": sorted(missing_dates),
                    }
                )

    finally:

        connection.close()

    print("\nMARKET TRADING-DATE GAP CHECK")
    print("-" * 60)

    print(
        f"Stocks checked : {len(universe_symbols)}"
    )

    print(
        f"Stocks with gaps: {len(stocks_with_gaps)}"
    )

    print(
        f"Missing date instances: {total_gaps}"
    )

    if stocks_with_gaps:

        print("\nMissing trading dates:")

        for item in stocks_with_gaps:

            print(
                f"  {item['symbol']}: "
                f"{item['missing_count']} dates"
            )

        logger.warning(
            "Market trading-date gaps detected: %s",
            total_gaps,
        )

        return False

    print(
        "✓ No unexpected trading-date gaps"
    )

    logger.info(
        "Market trading-date validation passed"
    )

    return True


def validate_suspicious_market_values():
    """
    Detect invalid and suspicious market values.

    Invalid values are blocking failures.
    Suspicious values are warnings.
    """

    project_root = Path(__file__).resolve().parents[2]

    database_path = (
        project_root
        / "database"
        / "swing_trading.db"
    )

    connection = sqlite3.connect(database_path)

    try:

        invalid_price_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices
            WHERE open <= 0
               OR high <= 0
               OR low <= 0
               OR close <= 0
               OR volume < 0
            """
        ).fetchone()[0]

        zero_volume_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices
            WHERE volume = 0
            """
        ).fetchone()[0]

        extreme_move_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    company_id,
                    date,
                    close,
                    LAG(close) OVER (
                        PARTITION BY company_id
                        ORDER BY date
                    ) AS previous_close
                FROM daily_prices
            )
            WHERE previous_close > 0
              AND ABS(
                    (close - previous_close)
                    / previous_close
                  ) > 0.20
            """
        ).fetchone()[0]

    finally:

        connection.close()

    print("\nSUSPICIOUS MARKET VALUE CHECK")
    print("-" * 60)

    print(
        f"Invalid price/value rows : "
        f"{invalid_price_rows}"
    )

    print(
        f"Zero-volume rows         : "
        f"{zero_volume_rows}"
    )

    print(
        f">20% daily price moves  : "
        f"{extreme_move_rows}"
    )

    if invalid_price_rows > 0:

        print(
            "❌ Invalid market values detected"
        )

        logger.error(
            "Invalid market values: %s",
            invalid_price_rows,
        )

        return False

    if zero_volume_rows > 0:

        print(
            "⚠ Zero-volume records detected"
        )

        logger.warning(
            "Zero-volume records: %s",
            zero_volume_rows,
        )

    if extreme_move_rows > 0:

        print(
            "⚠ Extreme price movements detected"
        )

        logger.warning(
            "Extreme price movements: %s",
            extreme_move_rows,
        )

    print(
        "✓ No invalid market values"
    )

    return True


def run_market_validation():
    """Run all market-data validation checks."""

    basic_ok = validate_market_data()

    gap_ok = validate_market_date_gaps()

    suspicious_ok = validate_suspicious_market_values()

    return (
        basic_ok
        and gap_ok
        and suspicious_ok
    )


def validate_cross_dataset_consistency():
    """
    Validate company identifiers and mappings across
    companies, daily_prices and quarterly_results.
    """

    project_root = Path(__file__).resolve().parents[2]

    database_path = (
        project_root
        / "database"
        / "swing_trading.db"
    )

    connection = sqlite3.connect(database_path)

    try:

        # ----------------------------------------------------
        # Market records with invalid company mapping
        # ----------------------------------------------------

        market_orphans = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices dp
            LEFT JOIN companies c
                ON dp.company_id = c.id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Financial records with invalid company mapping
        # ----------------------------------------------------

        financial_orphans = connection.execute(
            """
            SELECT COUNT(*)
            FROM quarterly_results qr
            LEFT JOIN companies c
                ON qr.company_id = c.id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Market company IDs
        # ----------------------------------------------------

        market_invalid_company_ids = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices dp
            INNER JOIN companies c
                ON dp.company_id = c.id
            WHERE c.symbol IS NULL
               OR TRIM(c.symbol) = ''
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Financial company IDs
        # ----------------------------------------------------

        financial_invalid_company_ids = connection.execute(
            """
            SELECT COUNT(*)
            FROM quarterly_results qr
            INNER JOIN companies c
                ON qr.company_id = c.id
            WHERE c.symbol IS NULL
               OR TRIM(c.symbol) = ''
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Companies with sector/industry problems
        # ----------------------------------------------------

        classification_problems = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE sector_id IS NULL
               OR industry_id IS NULL
            """
        ).fetchone()[0]

    finally:

        connection.close()

    print("\nCROSS-DATASET CONSISTOLOGY")
    print("-" * 60)

    print(
        f"Market orphan records     : "
        f"{market_orphans}"
    )

    print(
        f"Financial orphan records  : "
        f"{financial_orphans}"
    )

    print(
        f"Invalid market mappings   : "
        f"{market_invalid_company_ids}"
    )

    print(
        f"Invalid financial mappings: "
        f"{financial_invalid_company_ids}"
    )

    print(
        f"Classification problems   : "
        f"{classification_problems}"
    )

    passed = (
        market_orphans == 0
        and financial_orphans == 0
        and market_invalid_company_ids == 0
        and financial_invalid_company_ids == 0
        and classification_problems == 0
    )

    if passed:

        print(
            "✓ CROSS-DATASET CONSISTENCY PASSED"
        )

        logger.info(
            "Cross-dataset consistency passed"
        )

    else:

        print(
            "❌ CROSS-DATASET CONSISTENCY FAILED"
        )

        logger.error(
            "Cross-dataset consistency failed"
        )

    return passed


if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)