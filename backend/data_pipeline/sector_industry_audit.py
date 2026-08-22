"""
Week 7 - Sector / Industry Data Audit

Purpose:
    Audit the 50-stock universe and verify that the company
    sector and industry classifications are complete,
    consistent, and aligned with STOCK_UNIVERSE.

This module does NOT:
    - calculate sector scores
    - calculate industry scores
    - make trading decisions
    - modify database records

Outputs:
    reports/week7_sector_industry_audit.json
    reports/week7_sector_industry_mapping.csv
"""

import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from backend.data_pipeline.stock_universe import STOCK_UNIVERSE


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)

REPORT_DIR = PROJECT_ROOT / "reports"

REPORT_DIR.mkdir(
    exist_ok=True
)


# ============================================================
# HELPERS
# ============================================================

def get_connection():
    return sqlite3.connect(
        DATABASE_PATH
    )


def normalize_text(value):
    """
    Normalize text only for comparison.

    Database values are NOT modified.
    """

    if value is None:
        return ""

    return " ".join(
        str(value).strip().split()
    )


# ============================================================
# LOAD EXPECTED UNIVERSE
# ============================================================

def get_expected_universe():
    """
    Build expected company mappings from STOCK_UNIVERSE.
    """

    expected = {}

    for stock in STOCK_UNIVERSE:

        symbol = normalize_text(
            stock["symbol"]
        ).upper()

        expected[symbol] = {
            "company_name": normalize_text(
                stock["name"]
            ),
            "sector": normalize_text(
                stock["sector"]
            ),
            "industry": normalize_text(
                stock["industry"]
            ),
        }

    return expected


# ============================================================
# LOAD DATABASE COMPANIES
# ============================================================

def get_database_companies(connection):
    """
    Load company mappings from SQLite.
    """

    rows = connection.execute(
        """
        SELECT
            symbol,
            company_name,
            sector,
            industry
        FROM companies
        ORDER BY symbol
        """
    ).fetchall()

    companies = {}

    for row in rows:

        symbol = normalize_text(
            row[0]
        ).upper()

        companies[symbol] = {
            "company_name": normalize_text(
                row[1]
            ),
            "sector": normalize_text(
                row[2]
            ),
            "industry": normalize_text(
                row[3]
            ),
        }

    return companies


# ============================================================
# DUPLICATE SYMBOL CHECK
# ============================================================

def get_duplicate_symbols(connection):
    """
    Find duplicate company symbols.
    """

    rows = connection.execute(
        """
        SELECT
            symbol,
            COUNT(*) AS count
        FROM companies
        GROUP BY symbol
        HAVING COUNT(*) > 1
        ORDER BY symbol
        """
    ).fetchall()

    return [
        {
            "symbol": row[0],
            "count": row[1],
        }
        for row in rows
    ]


# ============================================================
# MAPPING COMPARISON
# ============================================================

def compare_mappings(
    expected,
    database,
):
    """
    Compare STOCK_UNIVERSE mappings against
    database mappings.
    """

    expected_symbols = set(
        expected.keys()
    )

    database_symbols = set(
        database.keys()
    )

    missing_symbols = sorted(
        expected_symbols - database_symbols
    )

    extra_symbols = sorted(
        database_symbols - expected_symbols
    )

    mapping_mismatches = []

    for symbol in sorted(
        expected_symbols & database_symbols
    ):

        expected_data = expected[symbol]
        database_data = database[symbol]

        differences = {}

        for field in (
            "company_name",
            "sector",
            "industry",
        ):

            if normalize_text(
                expected_data[field]
            ) != normalize_text(
                database_data[field]
            ):

                differences[field] = {
                    "expected": expected_data[field],
                    "database": database_data[field],
                }

        if differences:

            mapping_mismatches.append(
                {
                    "symbol": symbol,
                    "differences": differences,
                }
            )

    return (
        missing_symbols,
        extra_symbols,
        mapping_mismatches,
    )


# ============================================================
# MISSING CLASSIFICATION CHECK
# ============================================================

def find_missing_classifications(
    database,
):
    """
    Find stocks with missing sector or industry.
    """

    missing_sector = []
    missing_industry = []

    for symbol, data in sorted(
        database.items()
    ):

        if not data["sector"]:

            missing_sector.append(
                symbol
            )

        if not data["industry"]:

            missing_industry.append(
                symbol
            )

    return (
        missing_sector,
        missing_industry,
    )


# ============================================================
# NAMING ANALYSIS
# ============================================================

def get_name_counts(database):
    """
    Count sector and industry names.
    """

    sectors = Counter()
    industries = Counter()

    for data in database.values():

        if data["sector"]:

            sectors[
                data["sector"]
            ] += 1

        if data["industry"]:

            industries[
                data["industry"]
            ] += 1

    return (
        sectors,
        industries,
    )


# ============================================================
# BUILD STOCK MAPPING REPORT
# ============================================================

def build_mapping_rows(
    expected,
    database,
):
    """
    Build one row per expected stock.
    """

    rows = []

    for symbol in sorted(
        expected.keys()
    ):

        expected_data = expected[
            symbol
        ]

        database_data = database.get(
            symbol
        )

        if database_data is None:

            rows.append(
                {
                    "symbol": symbol,
                    "company_name": "",
                    "sector": "",
                    "industry": "",
                    "status": "MISSING",
                }
            )

            continue

        status = (
            "MATCH"
            if expected_data
            == database_data
            else "MISMATCH"
        )

        rows.append(
            {
                "symbol": symbol,
                "company_name":
                    database_data["company_name"],
                "sector":
                    database_data["sector"],
                "industry":
                    database_data["industry"],
                "status": status,
            }
        )

    return rows


# ============================================================
# SAVE CSV
# ============================================================

def save_mapping_csv(rows):
    """
    Save the complete sector/industry mapping.
    """

    path = (
        REPORT_DIR
        / "week7_sector_industry_mapping.csv"
    )

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "symbol",
                "company_name",
                "sector",
                "industry",
                "status",
            ],
        )

        writer.writeheader()

        writer.writerows(rows)

    return path


# ============================================================
# BUILD AUDIT REPORT
# ============================================================

def build_report():
    """
    Build the complete Week 7 audit report.
    """

    connection = get_connection()

    try:

        expected = get_expected_universe()

        database = get_database_companies(
            connection
        )

        (
            missing_symbols,
            extra_symbols,
            mapping_mismatches,
        ) = compare_mappings(
            expected,
            database,
        )

        (
            missing_sector,
            missing_industry,
        ) = find_missing_classifications(
            database
        )

        duplicate_symbols = (
            get_duplicate_symbols(
                connection
            )
        )

        (
            sector_counts,
            industry_counts,
        ) = get_name_counts(
            database
        )

        mapping_rows = build_mapping_rows(
            expected,
            database
        )

        report = {
            "report_name":
                "Week 7 Sector Industry Data Audit",

            "generated_at":
                datetime.now().isoformat(),

            "universe": {
                "expected_stocks":
                    len(expected),

                "database_stocks":
                    len(database),

                "missing_symbols":
                    missing_symbols,

                "extra_symbols":
                    extra_symbols,

                "passed":
                    (
                        len(expected)
                        == len(database)
                        and not missing_symbols
                        and not extra_symbols
                    ),
            },

            "mapping": {
                "mismatches":
                    mapping_mismatches,

                "mismatch_count":
                    len(mapping_mismatches),

                "passed":
                    len(mapping_mismatches) == 0,
            },

            "classification_completeness": {
                "missing_sector":
                    missing_sector,

                "missing_industry":
                    missing_industry,

                "passed":
                    (
                        not missing_sector
                        and not missing_industry
                    ),
            },

            "duplicate_symbols": {
                "duplicates":
                    duplicate_symbols,

                "count":
                    len(duplicate_symbols),

                "passed":
                    len(duplicate_symbols) == 0,
            },

            "sector_summary": {
                "unique_count":
                    len(sector_counts),

                "counts":
                    dict(
                        sorted(
                            sector_counts.items()
                        )
                    ),
            },

            "industry_summary": {
                "unique_count":
                    len(industry_counts),

                "counts":
                    dict(
                        sorted(
                            industry_counts.items()
                        )
                    ),
            },
        }

        report["overall_passed"] = all(
            [
                report["universe"]["passed"],
                report["mapping"]["passed"],
                report[
                    "classification_completeness"
                ]["passed"],
                report[
                    "duplicate_symbols"
                ]["passed"],
            ]
        )

        return report, mapping_rows

    finally:

        connection.close()


# ============================================================
# PRINT REPORT
# ============================================================

def print_report(report):
    """
    Print human-readable audit results.
    """

    print("=" * 60)

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "WEEK 7 - SECTOR / INDUSTRY DATA AUDIT"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # Universe
    # --------------------------------------------------------

    universe = report[
        "universe"
    ]

    print(
        "\nUNIVERSE"
    )

    print("-" * 60)

    print(
        f"Expected stocks : "
        f"{universe['expected_stocks']}"
    )

    print(
        f"Database stocks : "
        f"{universe['database_stocks']}"
    )

    if universe["passed"]:

        print(
            "✓ Stock universe valid"
        )

    else:

        print(
            "❌ Stock universe mismatch"
        )

        print(
            "Missing:",
            universe["missing_symbols"]
        )

        print(
            "Extra:",
            universe["extra_symbols"]
        )

    # --------------------------------------------------------
    # Mapping
    # --------------------------------------------------------

    mapping = report[
        "mapping"
    ]

    print(
        "\nCOMPANY MAPPING"
    )

    print("-" * 60)

    print(
        f"Mapping mismatches : "
        f"{mapping['mismatch_count']}"
    )

    if mapping["passed"]:

        print(
            "✓ Company / sector / industry "
            "mapping matches STOCK_UNIVERSE"
        )

    else:

        print(
            "❌ Mapping mismatches found"
        )

        for mismatch in mapping[
            "mismatches"
        ]:

            print(
                f"   {mismatch['symbol']}: "
                f"{mismatch['differences']}"
            )

    # --------------------------------------------------------
    # Completeness
    # --------------------------------------------------------

    completeness = report[
        "classification_completeness"
    ]

    print(
        "\nCLASSIFICATION COMPLETENESS"
    )

    print("-" * 60)

    print(
        "Missing sectors   :",
        completeness["missing_sector"]
        or "NONE",
    )

    print(
        "Missing industries:",
        completeness["missing_industry"]
        or "NONE",
    )

    if completeness["passed"]:

        print(
            "✓ Sector and industry "
            "classification complete"
        )

    else:

        print(
            "❌ Missing classifications found"
        )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------

    duplicates = report[
        "duplicate_symbols"
    ]

    print(
        "\nDUPLICATE SYMBOLS"
    )

    print("-" * 60)

    if duplicates["passed"]:

        print(
            "✓ No duplicate company symbols"
        )

    else:

        for duplicate in duplicates[
            "duplicates"
        ]:

            print(
                f"❌ {duplicate['symbol']} "
                f"appears {duplicate['count']} times"
            )

    # --------------------------------------------------------
    # Sector summary
    # --------------------------------------------------------

    sectors = report[
        "sector_summary"
    ]

    print(
        "\nSECTOR SUMMARY"
    )

    print("-" * 60)

    print(
        f"Unique sectors: "
        f"{sectors['unique_count']}"
    )

    for sector, count in sectors[
        "counts"
    ].items():

        print(
            f"{sector:<40}: {count}"
        )

    # --------------------------------------------------------
    # Industry summary
    # --------------------------------------------------------

    industries = report[
        "industry_summary"
    ]

    print(
        "\nINDUSTRY SUMMARY"
    )

    print("-" * 60)

    print(
        f"Unique industries: "
        f"{industries['unique_count']}"
    )

    for industry, count in industries[
        "counts"
    ].items():

        print(
            f"{industry:<40}: {count}"
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print(
        "\nFINAL AUDIT"
    )

    print("-" * 60)

    if report["overall_passed"]:

        print(
            "✓ Universe validation passed"
        )

        print(
            "✓ Company mapping passed"
        )

        print(
            "✓ Classification completeness passed"
        )

        print(
            "✓ Duplicate check passed"
        )

        print(
            "✓ SECTOR / INDUSTRY AUDIT PASSED"
        )

    else:

        print(
            "❌ SECTOR / INDUSTRY AUDIT "
            "REQUIRES REVIEW"
        )

    print(
        "=" * 60
    )


# ============================================================
# MAIN
# ============================================================

def main():

    report, mapping_rows = build_report()

    print_report(
        report
    )

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    json_path = (
        REPORT_DIR
        / "week7_sector_industry_audit.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
        )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    csv_path = save_mapping_csv(
        mapping_rows
    )

    print(
        "\nReports saved:"
    )

    print(
        f"  JSON: {json_path}"
    )

    print(
        f"  CSV : {csv_path}"
    )

    print(
        "\nDatabase was NOT modified."
    )

    print(
        "=" * 60
    )

    return report["overall_passed"]


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)