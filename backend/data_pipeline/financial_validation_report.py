"""
Financial Validation Report
===========================

Week 4 - Thursday

Purpose
-------
Create a repeatable financial-data quality report.

The report checks:

    - Company count
    - Financial record count
    - Company/stock mapping
    - Missing financial values
    - Duplicate company/quarter records
    - Invalid reporting periods
    - Orphan financial records
    - Invalid numeric values
    - Negative net profits
    - Ratio/percentage ranges

Important
---------
This module NEVER deletes financial records.

Potential problems are reported as warnings/errors so that
the source data remains traceable.
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)

REPORTS_DIR = PROJECT_ROOT / "reports"

REPORTS_DIR.mkdir(
    exist_ok=True
)

JSON_REPORT_PATH = (
    REPORTS_DIR
    / "financial_validation_report.json"
)

CSV_REPORT_PATH = (
    REPORTS_DIR
    / "financial_validation_missing_values.csv"
)


# ============================================================
# EXPECTED DATA
# ============================================================

EXPECTED_STOCK_COUNT = 50

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
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """Return a SQLite database connection."""

    return sqlite3.connect(
        DATABASE_PATH
    )


# ============================================================
# LOAD FINANCIAL DATA
# ============================================================

def load_financial_data():
    """
    Load financial records together with company information.
    """

    connection = get_connection()

    query = """
        SELECT
            quarterly_results.id,
            quarterly_results.company_id,
            companies.symbol,
            companies.company_name,
            quarterly_results.quarter,
            quarterly_results.revenue,
            quarterly_results.net_profit,
            quarterly_results.eps,
            quarterly_results.roe,
            quarterly_results.roce,
            quarterly_results.debt_equity,
            quarterly_results.operating_margin,
            quarterly_results.net_margin

        FROM quarterly_results

        LEFT JOIN companies
            ON companies.id =
               quarterly_results.company_id

        ORDER BY
            companies.symbol,
            quarterly_results.quarter
    """

    try:

        data = pd.read_sql_query(
            query,
            connection
        )

    finally:

        connection.close()

    return data


# ============================================================
# COMPANY COUNT
# ============================================================

def check_company_count():

    connection = get_connection()

    try:

        result = connection.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()

    finally:

        connection.close()

    count = result[0]

    return {
        "expected": EXPECTED_STOCK_COUNT,
        "found": count,
        "passed": count == EXPECTED_STOCK_COUNT,
    }


# ============================================================
# FINANCIAL RECORD COUNT
# ============================================================

def check_record_count(data):

    count = len(data)

    return {
        "total_records": count,
        "passed": count > 0,
    }


# ============================================================
# STOCK MAPPING
# ============================================================

def check_stock_mapping():

    connection = get_connection()

    try:

        rows = connection.execute("""
            SELECT
                COUNT(*)

            FROM companies
            WHERE symbol IS NOT NULL
        """).fetchone()

    finally:

        connection.close()

    mapped_count = rows[0]

    return {
        "mapped_companies": mapped_count,
        "passed": (
            mapped_count
            == EXPECTED_STOCK_COUNT
        ),
    }


# ============================================================
# MISSING VALUES
# ============================================================

def check_missing_values(data):

    rows = []

    for field in FINANCIAL_FIELDS:

        missing = int(
            data[field]
            .isna()
            .sum()
        )

        available = int(
            data[field]
            .notna()
            .sum()
        )

        rows.append({
            "field": field,
            "available": available,
            "missing": missing,
            "total": len(data),
            "coverage_pct": round(
                (
                    available
                    / len(data)
                    * 100
                )
                if len(data) > 0
                else 0,
                2
            ),
        })

    return rows


# ============================================================
# MISSING VALUES BY STOCK
# ============================================================

def build_stock_missing_report(data):

    rows = []

    for symbol, group in data.groupby(
        "symbol",
        dropna=False
    ):

        row = {
            "symbol": symbol,
            "records": len(group),
        }

        for field in FINANCIAL_FIELDS:

            row[
                f"{field}_missing"
            ] = int(
                group[field]
                .isna()
                .sum()
            )

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# DUPLICATE CHECK
# ============================================================

def check_duplicates(data):

    duplicates = data[
        data.duplicated(
            subset=[
                "company_id",
                "quarter",
            ],
            keep=False
        )
    ]

    return {
        "duplicate_records": len(
            duplicates
        ),
        "passed": duplicates.empty,
    }


# ============================================================
# INVALID PERIOD CHECK
# ============================================================

def check_periods(data):

    periods = pd.to_datetime(
        data["quarter"],
        errors="coerce"
    )

    invalid = data[
        periods.isna()
    ]

    return {
        "invalid_period_records": len(
            invalid
        ),
        "passed": invalid.empty,
    }


# ============================================================
# ORPHAN CHECK
# ============================================================

def check_orphan_records(data):

    orphans = data[
        data["symbol"].isna()
    ]

    return {
        "orphan_records": len(
            orphans
        ),
        "passed": orphans.empty,
    }


# ============================================================
# NUMERIC VALIDATION
# ============================================================

def check_numeric_values(data):

    results = {}

    for field in FINANCIAL_FIELDS:

        converted = pd.to_numeric(
            data[field],
            errors="coerce"
        )

        invalid = (
            data[field].notna()
            & converted.isna()
        )

        results[field] = {
            "invalid_values": int(
                invalid.sum()
            ),
            "passed": not invalid.any(),
        }

    return results


# ============================================================
# NEGATIVE PROFIT CHECK
# ============================================================

def check_negative_profits(data):

    negative = data[
        data["net_profit"] < 0
    ]

    rows = []

    for _, row in negative.iterrows():

        rows.append({
            "symbol": row["symbol"],
            "quarter": row["quarter"],
            "net_profit": row["net_profit"],
        })

    return {
        "negative_profit_records": len(
            rows
        ),
        "records": rows,
    }


# ============================================================
# RATIO / RANGE CHECK
# ============================================================

def check_ratio_ranges(data):

    results = {}

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = data["roe"].dropna()

    invalid_roe = roe[
        (roe < -100)
        | (roe > 1000)
    ]

    results["roe"] = {
        "invalid_values": int(
            len(invalid_roe)
        ),
        "passed": invalid_roe.empty,
    }

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = data["roce"].dropna()

    invalid_roce = roce[
        (roce < -100)
        | (roce > 1000)
    ]

    results["roce"] = {
        "invalid_values": int(
            len(invalid_roce)
        ),
        "passed": invalid_roce.empty,
    }

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    debt_equity = (
        data["debt_equity"]
        .dropna()
    )

    invalid_de = debt_equity[
        debt_equity < 0
    ]

    results["debt_equity"] = {
        "invalid_values": int(
            len(invalid_de)
        ),
        "passed": invalid_de.empty,
    }

    return results


# ============================================================
# BUILD COMPLETE REPORT
# ============================================================

def build_report(data):

    company_count = (
        check_company_count()
    )

    record_count = (
        check_record_count(data)
    )

    mapping = (
        check_stock_mapping()
    )

    missing_values = (
        check_missing_values(data)
    )

    duplicates = (
        check_duplicates(data)
    )

    periods = (
        check_periods(data)
    )

    orphans = (
        check_orphan_records(data)
    )

    numeric = (
        check_numeric_values(data)
    )

    negative_profits = (
        check_negative_profits(data)
    )

    ratio_ranges = (
        check_ratio_ranges(data)
    )

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    structural_checks = [
        company_count["passed"],
        record_count["passed"],
        mapping["passed"],
        duplicates["passed"],
        periods["passed"],
        orphans["passed"],
    ]

    numeric_checks = [
        result["passed"]
        for result in numeric.values()
    ]

    ratio_checks = [
        result["passed"]
        for result in ratio_ranges.values()
    ]

    overall_passed = all(
        structural_checks
        + numeric_checks
        + ratio_checks
    )

    return {
        "report_type":
            "financial_validation",

        "week":
            4,

        "overall_status":
            "PASSED"
            if overall_passed
            else "FAILED",

        "company_count":
            company_count,

        "record_count":
            record_count,

        "stock_mapping":
            mapping,

        "missing_values":
            missing_values,

        "duplicates":
            duplicates,

        "invalid_periods":
            periods,

        "orphan_records":
            orphans,

        "numeric_validation":
            numeric,

        "negative_net_profits":
            negative_profits,

        "ratio_validation":
            ratio_ranges,
    }


# ============================================================
# SAVE JSON REPORT
# ============================================================

def save_json_report(report):

    with open(
        JSON_REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            default=str
        )

    print(
        f"\n✓ JSON report saved:"
    )

    print(
        f"  {JSON_REPORT_PATH}"
    )


# ============================================================
# SAVE CSV REPORT
# ============================================================

def save_csv_report(data):

    report = (
        build_stock_missing_report(
            data
        )
    )

    report.to_csv(
        CSV_REPORT_PATH,
        index=False
    )

    print(
        f"✓ CSV missing-data report saved:"
    )

    print(
        f"  {CSV_REPORT_PATH}"
    )


# ============================================================
# PRINT REPORT
# ============================================================

def print_report(report):

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL VALIDATION REPORT"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # Company count
    # --------------------------------------------------------

    company = report[
        "company_count"
    ]

    print(
        f"\nCompanies:"
    )

    print(
        f"  Expected : {company['expected']}"
    )

    print(
        f"  Found    : {company['found']}"
    )

    print(
        "  ✓ Passed"
        if company["passed"]
        else "  ❌ Failed"
    )

    # --------------------------------------------------------
    # Records
    # --------------------------------------------------------

    records = report[
        "record_count"
    ]

    print(
        f"\nFinancial records:"
    )

    print(
        f"  Total: {records['total_records']}"
    )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    print(
        "\nMissing financial values:"
    )

    for item in report[
        "missing_values"
    ]:

        status = (
            "✓"
            if item["missing"] == 0
            else "⚠"
        )

        print(
            f"  {status} "
            f"{item['field']:<20}"
            f"missing: "
            f"{item['missing']:<4}"
            f"coverage: "
            f"{item['coverage_pct']:.2f}%"
        )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------

    duplicates = report[
        "duplicates"
    ]

    print(
        "\nDuplicate company/quarter:"
    )

    print(
        "  ✓ None"
        if duplicates["passed"]
        else
        f"  ❌ {duplicates['duplicate_records']}"
    )

    # --------------------------------------------------------
    # Periods
    # --------------------------------------------------------

    periods = report[
        "invalid_periods"
    ]

    print(
        "\nInvalid periods:"
    )

    print(
        "  ✓ None"
        if periods["passed"]
        else
        f"  ❌ {periods['invalid_period_records']}"
    )

    # --------------------------------------------------------
    # Orphans
    # --------------------------------------------------------

    orphans = report[
        "orphan_records"
    ]

    print(
        "\nOrphan records:"
    )

    print(
        "  ✓ None"
        if orphans["passed"]
        else
        f"  ❌ {orphans['orphan_records']}"
    )

    # --------------------------------------------------------
    # Negative profits
    # --------------------------------------------------------

    negative = report[
        "negative_net_profits"
    ]

    print(
        "\nNegative net-profit records:"
    )

    if negative[
        "negative_profit_records"
    ] == 0:

        print(
            "  ✓ None"
        )

    else:

        print(
            f"  ⚠ "
            f"{negative['negative_profit_records']} "
            f"record(s)"
        )

        for item in negative[
            "records"
        ]:

            print(
                f"     {item['symbol']} "
                f"{item['quarter']} "
                f"profit={item['net_profit']}"
            )

    # --------------------------------------------------------
    # Numeric validation
    # --------------------------------------------------------

    print(
        "\nNumeric validation:"
    )

    for field, result in (
        report[
            "numeric_validation"
        ].items()
    ):

        if result["passed"]:

            print(
                f"  ✓ {field}"
            )

        else:

            print(
                f"  ❌ {field}: "
                f"{result['invalid_values']} "
                f"invalid"
            )

    # --------------------------------------------------------
    # Ratio validation
    # --------------------------------------------------------

    print(
        "\nRatio validation:"
    )

    for field, result in (
        report[
            "ratio_validation"
        ].items()
    ):

        if result["passed"]:

            print(
                f"  ✓ {field}"
            )

        else:

            print(
                f"  ❌ {field}: "
                f"{result['invalid_values']} "
                f"invalid"
            )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    print(
        "\n------------------------------------------"
    )

    print(
        f"FINAL STATUS: "
        f"{report['overall_status']}"
    )

    print(
        "=========================================="
    )


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
        "WEEK 4 - VALIDATION REPORTING"
    )

    print(
        "=========================================="
    )

    data = load_financial_data()

    print(
        f"\nRecords loaded: {len(data)}"
    )

    if data.empty:

        print(
            "❌ No financial records found."
        )

        return

    report = build_report(
        data
    )

    print_report(
        report
    )

    save_json_report(
        report
    )

    save_csv_report(
        data
    )

    print(
        "\n=========================================="
    )

    print(
        "REPEATABLE FINANCIAL VALIDATION COMPLETE"
    )

    print(
        "No database records were modified."
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":

    main()