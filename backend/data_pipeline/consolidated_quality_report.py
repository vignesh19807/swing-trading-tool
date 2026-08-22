"""
Week 5 - Consolidated Data Quality Report

Combines market-price and financial-data quality checks
into one repeatable report.

Data Engineer responsibility:
- collection
- validation
- normalization
- storage
- reporting

No scoring logic belongs here.
"""

from pathlib import Path
import sqlite3
import json
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "database" / "swing_trading.db"
REPORT_DIR = PROJECT_ROOT / "reports"

REPORT_DIR.mkdir(exist_ok=True)


MARKET_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

FINANCIAL_COLUMNS = [
    "revenue",
    "net_profit",
    "eps",
    "roe",
    "roce",
    "debt_equity",
    "operating_margin",
    "net_margin",
]


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def get_company_count(connection):
    return connection.execute(
        "SELECT COUNT(*) FROM companies"
    ).fetchone()[0]


def get_financial_record_count(connection):
    return connection.execute(
        "SELECT COUNT(*) FROM quarterly_results"
    ).fetchone()[0]


def get_price_record_count(connection):
    return connection.execute(
        "SELECT COUNT(*) FROM daily_prices"
    ).fetchone()[0]


def financial_quality(connection):
    result = {}

    for column in FINANCIAL_COLUMNS:
        total, missing = connection.execute(
            f"""
            SELECT
                COUNT(*),
                SUM(CASE WHEN {column} IS NULL THEN 1 ELSE 0 END)
            FROM quarterly_results
            """
        ).fetchone()

        missing = missing or 0

        result[column] = {
            "total": total,
            "missing": missing,
            "coverage_percent": round(
                ((total - missing) / total) * 100, 2
            ) if total else 0,
        }

    return result


def financial_duplicates(connection):
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT company_id, quarter
            FROM quarterly_results
            GROUP BY company_id, quarter
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]


def financial_orphans(connection):
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results qr
        LEFT JOIN companies c
            ON qr.company_id = c.id
        WHERE c.id IS NULL
        """
    ).fetchone()[0]


def negative_profit_count(connection):
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM quarterly_results
        WHERE net_profit < 0
        """
    ).fetchone()[0]


def market_quality(connection):
    result = {}

    for column in MARKET_COLUMNS:
        total, missing = connection.execute(
            f"""
            SELECT
                COUNT(*),
                SUM(
                    CASE
                        WHEN {column} IS NULL THEN 1
                        ELSE 0
                    END
                )
            FROM daily_prices
            """
        ).fetchone()

        missing = missing or 0

        result[column] = {
            "total": total,
            "missing": missing,
            "coverage_percent": round(
                ((total - missing) / total) * 100, 2
            ) if total else 0,
        }

    return result


def market_duplicates(connection):
    return connection.execute(
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


def market_orphans(connection):
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM daily_prices dp
        LEFT JOIN companies c
            ON dp.company_id = c.id
        WHERE c.id IS NULL
        """
    ).fetchone()[0]


def build_report():
    connection = get_connection()

    try:
        companies = get_company_count(connection)
        financial_records = get_financial_record_count(connection)
        price_records = get_price_record_count(connection)

        report = {
            "report_name": "Week 5 Consolidated Data Quality Report",
            "generated_at": datetime.now().isoformat(),

            "universe": {
                "expected_stocks": 50,
                "companies_in_database": companies,
                "passed": companies == 50,
            },

            "market_data": {
                "total_records": price_records,
                "quality": market_quality(connection),
                "duplicate_groups": market_duplicates(connection),
                "orphan_records": market_orphans(connection),
            },

            "financial_data": {
                "total_records": financial_records,
                "quality": financial_quality(connection),
                "duplicate_groups": financial_duplicates(connection),
                "orphan_records": financial_orphans(connection),
                "negative_profit_records": negative_profit_count(
                    connection
                ),
            },
        }

        return report

    finally:
        connection.close()


def print_report(report):
    print("=" * 50)
    print("SWING TRADING PLATFORM")
    print("WEEK 5 - CONSOLIDATED DATA QUALITY REPORT")
    print("=" * 50)

    universe = report["universe"]

    print("\nUNIVERSE")
    print("-" * 50)
    print(f"Expected stocks : {universe['expected_stocks']}")
    print(f"Found           : {universe['companies_in_database']}")

    if universe["passed"]:
        print("✓ 50-stock universe valid")
    else:
        print("⚠ Stock universe mismatch")

    market = report["market_data"]

    print("\nMARKET DATA")
    print("-" * 50)
    print(f"Total records   : {market['total_records']}")
    print(f"Duplicate groups: {market['duplicate_groups']}")
    print(f"Orphan records  : {market['orphan_records']}")

    for field, values in market["quality"].items():
        print(
            f"{field:<15} "
            f"missing: {values['missing']:<6} "
            f"coverage: {values['coverage_percent']:.2f}%"
        )

    financial = report["financial_data"]

    print("\nFINANCIAL DATA")
    print("-" * 50)
    print(f"Total records   : {financial['total_records']}")
    print(f"Duplicate groups: {financial['duplicate_groups']}")
    print(f"Orphan records  : {financial['orphan_records']}")
    print(
        f"Negative profits: "
        f"{financial['negative_profit_records']}"
    )

    for field, values in financial["quality"].items():
        print(
            f"{field:<18} "
            f"missing: {values['missing']:<6} "
            f"coverage: {values['coverage_percent']:.2f}%"
        )

    print("\nFINAL AUDIT")
    print("-" * 50)

    market_ok = (
        market["duplicate_groups"] == 0
        and market["orphan_records"] == 0
    )

    financial_ok = (
        financial["duplicate_groups"] == 0
        and financial["orphan_records"] == 0
    )

    universe_ok = universe["passed"]

    if universe_ok and market_ok and financial_ok:
        print("✓ Universe validation passed")
        print("✓ Market database integrity passed")
        print("✓ Financial database integrity passed")
        print("✓ Known missing values preserved as warnings")
        print("✓ Consolidated data audit PASSED")
    else:
        print("⚠ CONSOLIDATED AUDIT REQUIRES REVIEW")

    report_path = REPORT_DIR / "week5_consolidated_quality_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\nReport saved:")
    print(f"  {report_path}")

    print("=" * 50)


if __name__ == "__main__":
    report = build_report()
    print_report(report)