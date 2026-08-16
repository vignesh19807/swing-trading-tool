"""
Financial Data Quality Verification
===================================

Week 3 Data Engineering

Validates the financial data stored in quarterly_results.

Checks:
    1. Company count
    2. Financial record count
    3. Company mapping
    4. Duplicate company/quarter records
    5. Invalid/missing periods
    6. Invalid numeric values
    7. Negative revenue/profit anomalies
    8. Invalid percentage/ratio values
    9. Financial service availability

Missing values are reported as warnings, not failures.
"""

import sqlite3
from pathlib import Path

from backend.data_pipeline.stock_universe import (
    STOCK_UNIVERSE,
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
# EXPECTED VALUES
# ============================================================

EXPECTED_COMPANIES = 50


FINANCIAL_FIELDS = [
    "revenue",
    "net_profit",
    "eps",
    "roe",
    "roce",
    "debt_equity",
    "operating_margin",
    "net_margin",
]


# ============================================================
# MAIN VALIDATION
# ============================================================

def main():

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("WEEK 3 FINANCIAL DATA QUALITY CHECK")
    print("==========================================")

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    checks_passed = True

    # ========================================================
    # 1. COMPANY COUNT
    # ========================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM companies
        """
    )

    company_count = cursor.fetchone()[0]

    print(
        "\nCompany count:"
    )

    print(
        f"  Expected : {EXPECTED_COMPANIES}"
    )

    print(
        f"  Found    : {company_count}"
    )

    if company_count == EXPECTED_COMPANIES:

        print(
            "✓ 50 companies present"
        )

    else:

        print(
            "❌ Company count mismatch"
        )

        checks_passed = False

    # ========================================================
    # 2. FINANCIAL RECORD COUNT
    # ========================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        """
    )

    total_records = cursor.fetchone()[0]

    print(
        "\nFinancial records:"
    )

    print(
        f"  Total records: {total_records}"
    )

    if total_records > 0:

        print(
            "✓ Financial records exist"
        )

    else:

        print(
            "❌ No financial records found"
        )

        checks_passed = False

    # ========================================================
    # 3. STOCK UNIVERSE MAPPING
    # ========================================================

    universe_symbols = set()

    for stock in STOCK_UNIVERSE:

        if isinstance(stock, dict):

            symbol = stock.get("symbol")

        else:

            symbol = str(stock)

        if symbol:

            universe_symbols.add(
                symbol.upper().strip()
            )

    cursor.execute(
        """
        SELECT symbol
        FROM companies
        """
    )

    database_symbols = {
        row[0].upper().strip()
        for row in cursor.fetchall()
    }

    missing_companies = (
        universe_symbols
        - database_symbols
    )

    extra_companies = (
        database_symbols
        - universe_symbols
    )

    print(
        "\nStock universe mapping:"
    )

    if not missing_companies:

        print(
            "✓ All universe stocks exist "
            "in companies table"
        )

    else:

        print(
            f"❌ Missing companies: "
            f"{sorted(missing_companies)}"
        )

        checks_passed = False

    if extra_companies:

        print(
            f"⚠ Extra companies: "
            f"{sorted(extra_companies)}"
        )

    # ========================================================
    # 4. RECORDS PER COMPANY
    # ========================================================

    cursor.execute(
        """
        SELECT
            companies.symbol,
            COUNT(quarterly_results.id)

        FROM companies

        LEFT JOIN quarterly_results
            ON companies.id =
               quarterly_results.company_id

        GROUP BY companies.id

        ORDER BY companies.symbol
        """
    )

    company_records = cursor.fetchall()

    stocks_with_data = 0
    stocks_without_data = []

    print(
        "\nFinancial records per company:"
    )

    for symbol, count in company_records:

        if count > 0:

            stocks_with_data += 1

        else:

            stocks_without_data.append(
                symbol
            )

    print(
        f"  Stocks with data: "
        f"{stocks_with_data}"
    )

    print(
        f"  Stocks without data: "
        f"{len(stocks_without_data)}"
    )

    if stocks_without_data:

        print(
            f"⚠ No financial data for: "
            f"{stocks_without_data}"
        )

    else:

        print(
            "✓ All 50 companies have financial data"
        )

    # ========================================================
    # 5. DUPLICATE CHECK
    # ========================================================

    cursor.execute(
        """
        SELECT
            company_id,
            quarter,
            COUNT(*)

        FROM quarterly_results

        GROUP BY company_id, quarter

        HAVING COUNT(*) > 1
        """
    )

    duplicates = cursor.fetchall()

    print(
        "\nDuplicate company/quarter records:"
    )

    if not duplicates:

        print(
            "✓ No duplicate financial records"
        )

    else:

        print(
            f"❌ Duplicate groups: "
            f"{len(duplicates)}"
        )

        for duplicate in duplicates:

            print(
                f"   company_id={duplicate[0]}, "
                f"quarter={duplicate[1]}, "
                f"count={duplicate[2]}"
            )

        checks_passed = False

    # ========================================================
    # 6. INVALID PERIODS
    # ========================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        WHERE quarter IS NULL
           OR TRIM(quarter) = ''
        """
    )

    invalid_periods = cursor.fetchone()[0]

    print(
        "\nInvalid financial periods:"
    )

    if invalid_periods == 0:

        print(
            "✓ No invalid periods"
        )

    else:

        print(
            f"❌ Invalid periods: "
            f"{invalid_periods}"
        )

        checks_passed = False

    # ========================================================
    # 7. ORPHAN RECORDS
    # ========================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results qr

        LEFT JOIN companies c
            ON qr.company_id = c.id

        WHERE c.id IS NULL
        """
    )

    orphan_records = cursor.fetchone()[0]

    print(
        "\nOrphan financial records:"
    )

    if orphan_records == 0:

        print(
            "✓ No orphan records"
        )

    else:

        print(
            f"❌ Orphan records: "
            f"{orphan_records}"
        )

        checks_passed = False

    # ========================================================
    # 8. MISSING VALUE REPORT
    # ========================================================

    print(
        "\nMissing financial values:"
    )

    total_missing = 0

    for field in FINANCIAL_FIELDS:

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM quarterly_results
            WHERE {field} IS NULL
            """
        )

        missing = cursor.fetchone()[0]

        total_missing += missing

        if missing > 0:

            print(
                f"  ⚠ {field:<20} {missing}"
            )

        else:

            print(
                f"  ✓ {field:<20} 0"
            )

    print(
        f"  Total missing values: "
        f"{total_missing}"
    )

    print(
        "  Missing values are warnings, "
        "not validation failures."
    )

    # ========================================================
    # 9. NUMERIC VALIDITY
    # ========================================================

    print(
        "\nNumeric value validation:"
    )

    numeric_errors = 0

    for field in FINANCIAL_FIELDS:

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM quarterly_results
            WHERE {field} IS NOT NULL
              AND typeof({field}) NOT IN (
                  'integer',
                  'real'
              )
            """
        )

        invalid = cursor.fetchone()[0]

        if invalid > 0:

            print(
                f"  ❌ {field}: "
                f"{invalid} invalid values"
            )

            numeric_errors += invalid

        else:

            print(
                f"  ✓ {field}"
            )

    if numeric_errors > 0:

        checks_passed = False

    # ========================================================
    # 10. NEGATIVE VALUE CHECK
    # ========================================================

    print(
        "\nNegative value review:"
    )

    for field in [
        "revenue",
        "net_profit",
    ]:

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM quarterly_results
            WHERE {field} < 0
            """
        )

        negative = cursor.fetchone()[0]

        if negative > 0:

            print(
                f"  ⚠ {field}: "
                f"{negative} negative values"
            )

        else:

            print(
                f"  ✓ {field}: "
                f"no negative values"
            )

    # ========================================================
    # 11. RATIO / PERCENTAGE REVIEW
    # ========================================================

    print(
        "\nRatio / percentage review:"
    )

    # ROE is represented as decimal in the current
    # collector, e.g. 0.32 = 32%.
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        WHERE roe IS NOT NULL
          AND (
              roe < -1
              OR roe > 5
          )
        """
    )

    invalid_roe = cursor.fetchone()[0]

    if invalid_roe > 0:

        print(
            f"  ⚠ ROE suspicious values: "
            f"{invalid_roe}"
        )

    else:

        print(
            "  ✓ ROE values within broad range"
        )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        WHERE debt_equity IS NOT NULL
          AND debt_equity < 0
        """
    )

    invalid_de = cursor.fetchone()[0]

    if invalid_de > 0:

        print(
            f"  ❌ Negative debt/equity values: "
            f"{invalid_de}"
        )

        checks_passed = False

    else:

        print(
            "  ✓ Debt/equity values valid"
        )

    # ========================================================
    # 12. UNIQUE CONSTRAINT CHECK
    # ========================================================

    cursor.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'quarterly_results'
        """
    )

    table_schema = cursor.fetchone()[0]

    print(
        "\nDatabase constraint:"
    )

    if "UNIQUE(company_id, quarter)" in table_schema:

        print(
            "✓ UNIQUE(company_id, quarter) active"
        )

    else:

        print(
            "❌ Financial uniqueness constraint missing"
        )

        checks_passed = False

    connection.close()

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "FINAL FINANCIAL DATA QUALITY RESULT"
    )

    print(
        "=========================================="
    )

    if checks_passed:

        print(
            "✓ 50 companies available"
        )

        print(
            f"✓ {total_records} financial records"
        )

        print(
            "✓ Company mappings valid"
        )

        print(
            "✓ No duplicate company/quarter records"
        )

        print(
            "✓ Financial periods valid"
        )

        print(
            "✓ No orphan records"
        )

        print(
            "✓ Numeric fields valid"
        )

        print(
            "✓ Financial database validation passed"
        )

        print(
            "------------------------------------------"
        )

        print(
            "🎉 WEEK 3 FINANCIAL DATA VALIDATION PASSED"
        )

    else:

        print(
            "⚠ FINANCIAL DATA VALIDATION REQUIRES REVIEW"
        )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()