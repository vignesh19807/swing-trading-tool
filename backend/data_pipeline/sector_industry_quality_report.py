"""
Week 7 - Sector / Industry Quality Report

Purpose:
    Provide a repeatable, read-only quality audit for the
    sector and industry master-data layer.

Checks:
    1. 50-stock universe
    2. Sector master completeness
    3. Industry master completeness
    4. Company sector links
    5. Company industry links
    6. Orphan sector links
    7. Orphan industry links
    8. Duplicate company symbols
    9. Company text-to-master mapping consistency
   10. Sector stock-count consistency
   11. Industry stock-count consistency

This module does NOT:
    - modify the database
    - calculate trading scores
    - rank stocks
    - make trading decisions
"""

from pathlib import Path
import json
import sqlite3
from datetime import datetime

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


EXPECTED_COMPANIES = 50
EXPECTED_SECTORS = 16
EXPECTED_INDUSTRY_MAPPINGS = 32


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Return a SQLite connection.
    """

    return sqlite3.connect(
        DATABASE_PATH
    )


# ============================================================
# UNIVERSE CHECK
# ============================================================

def check_universe(connection):

    expected_symbols = {
        stock["symbol"]
        for stock in STOCK_UNIVERSE
    }

    rows = connection.execute(
        """
        SELECT symbol
        FROM companies
        """
    ).fetchall()

    database_symbols = {
        row[0]
        for row in rows
    }

    missing = sorted(
        expected_symbols - database_symbols
    )

    extra = sorted(
        database_symbols - expected_symbols
    )

    return {
        "expected": len(expected_symbols),
        "found": len(database_symbols),
        "missing": missing,
        "extra": extra,
        "passed": (
            len(expected_symbols) == EXPECTED_COMPANIES
            and len(database_symbols) == EXPECTED_COMPANIES
            and not missing
            and not extra
        ),
    }


# ============================================================
# SECTOR MASTER CHECK
# ============================================================

def check_sectors(connection):

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM sectors
        """
    ).fetchone()[0]

    missing_names = connection.execute(
        """
        SELECT id
        FROM sectors
        WHERE name IS NULL
           OR TRIM(name) = ''
        """
    ).fetchall()

    duplicate_names = connection.execute(
        """
        SELECT name, COUNT(*)
        FROM sectors
        GROUP BY name
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    return {
        "total": total,
        "missing_names": len(missing_names),
        "duplicate_names": len(duplicate_names),
        "passed": (
            total == EXPECTED_SECTORS
            and len(missing_names) == 0
            and len(duplicate_names) == 0
        ),
    }


# ============================================================
# INDUSTRY MASTER CHECK
# ============================================================

def check_industries(connection):

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM industries
        """
    ).fetchone()[0]

    missing_names = connection.execute(
        """
        SELECT id
        FROM industries
        WHERE name IS NULL
           OR TRIM(name) = ''
        """
    ).fetchall()

    duplicate_mappings = connection.execute(
        """
        SELECT name, sector_id, COUNT(*)
        FROM industries
        GROUP BY name, sector_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    invalid_sector_links = connection.execute(
        """
        SELECT i.id
        FROM industries i
        LEFT JOIN sectors s
            ON i.sector_id = s.id
        WHERE i.sector_id IS NULL
           OR s.id IS NULL
        """
    ).fetchall()

    return {
        "total": total,
        "missing_names": len(missing_names),
        "duplicate_mappings": len(
            duplicate_mappings
        ),
        "invalid_sector_links": len(
            invalid_sector_links
        ),
        "passed": (
            total == EXPECTED_INDUSTRY_MAPPINGS
            and len(missing_names) == 0
            and len(duplicate_mappings) == 0
            and len(invalid_sector_links) == 0
        ),
    }


# ============================================================
# COMPANY LINK CHECK
# ============================================================

def check_company_links(connection):

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM companies
        """
    ).fetchone()[0]

    missing_sector_links = connection.execute(
        """
        SELECT symbol
        FROM companies
        WHERE sector_id IS NULL
        """
    ).fetchall()

    missing_industry_links = connection.execute(
        """
        SELECT symbol
        FROM companies
        WHERE industry_id IS NULL
        """
    ).fetchall()

    invalid_sector_links = connection.execute(
        """
        SELECT c.symbol
        FROM companies c
        LEFT JOIN sectors s
            ON c.sector_id = s.id
        WHERE c.sector_id IS NOT NULL
          AND s.id IS NULL
        """
    ).fetchall()

    invalid_industry_links = connection.execute(
        """
        SELECT c.symbol
        FROM companies c
        LEFT JOIN industries i
            ON c.industry_id = i.id
        WHERE c.industry_id IS NOT NULL
          AND i.id IS NULL
        """
    ).fetchall()

    return {
        "companies": total,
        "missing_sector_links": [
            row[0]
            for row in missing_sector_links
        ],
        "missing_industry_links": [
            row[0]
            for row in missing_industry_links
        ],
        "invalid_sector_links": [
            row[0]
            for row in invalid_sector_links
        ],
        "invalid_industry_links": [
            row[0]
            for row in invalid_industry_links
        ],
        "passed": (
            total == EXPECTED_COMPANIES
            and not missing_sector_links
            and not missing_industry_links
            and not invalid_sector_links
            and not invalid_industry_links
        ),
    }


# ============================================================
# DUPLICATE SYMBOL CHECK
# ============================================================

def check_duplicate_symbols(connection):

    duplicates = connection.execute(
        """
        SELECT symbol, COUNT(*)
        FROM companies
        GROUP BY symbol
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    return {
        "duplicate_groups": len(duplicates),
        "duplicates": [
            {
                "symbol": row[0],
                "count": row[1],
            }
            for row in duplicates
        ],
        "passed": len(duplicates) == 0,
    }


# ============================================================
# TEXT / MASTER MAPPING CHECK
# ============================================================

def check_mapping_consistency(connection):

    rows = connection.execute(
        """
        SELECT
            c.symbol,
            c.sector,
            c.industry,
            s.name AS master_sector,
            i.name AS master_industry
        FROM companies c

        LEFT JOIN sectors s
            ON c.sector_id = s.id

        LEFT JOIN industries i
            ON c.industry_id = i.id

        ORDER BY c.symbol
        """
    ).fetchall()

    mismatches = []

    for row in rows:

        symbol = row[0]
        sector = row[1]
        industry = row[2]
        master_sector = row[3]
        master_industry = row[4]

        if sector != master_sector:
            mismatches.append({
                "symbol": symbol,
                "field": "sector",
                "company_value": sector,
                "master_value": master_sector,
            })

        if industry != master_industry:
            mismatches.append({
                "symbol": symbol,
                "field": "industry",
                "company_value": industry,
                "master_value": master_industry,
            })

    return {
        "companies_checked": len(rows),
        "mismatches": mismatches,
        "passed": (
            len(rows) == EXPECTED_COMPANIES
            and not mismatches
        ),
    }


# ============================================================
# SECTOR COUNT CHECK
# ============================================================

def check_sector_counts(connection):

    rows = connection.execute(
        """
        SELECT
            s.name,
            COUNT(c.id)
        FROM sectors s

        LEFT JOIN companies c
            ON c.sector_id = s.id

        GROUP BY
            s.id,
            s.name

        ORDER BY s.name
        """
    ).fetchall()

    total = sum(
        row[1]
        for row in rows
    )

    return {
        "sector_count": len(rows),
        "stock_total": total,
        "passed": (
            len(rows) == EXPECTED_SECTORS
            and total == EXPECTED_COMPANIES
        ),
    }


# ============================================================
# INDUSTRY COUNT CHECK
# ============================================================

def check_industry_counts(connection):

    rows = connection.execute(
        """
        SELECT
            i.name,
            s.name,
            COUNT(c.id)
        FROM industries i

        INNER JOIN sectors s
            ON i.sector_id = s.id

        LEFT JOIN companies c
            ON c.industry_id = i.id

        GROUP BY
            i.id,
            i.name,
            s.name

        ORDER BY
            i.name,
            s.name
        """
    ).fetchall()

    total = sum(
        row[2]
        for row in rows
    )

    return {
        "industry_mapping_count": len(rows),
        "stock_total": total,
        "passed": (
            len(rows) == EXPECTED_INDUSTRY_MAPPINGS
            and total == EXPECTED_COMPANIES
        ),
    }


# ============================================================
# BUILD REPORT
# ============================================================

def build_report():

    connection = get_connection()

    try:

        universe = check_universe(
            connection
        )

        sectors = check_sectors(
            connection
        )

        industries = check_industries(
            connection
        )

        company_links = check_company_links(
            connection
        )

        duplicate_symbols = (
            check_duplicate_symbols(
                connection
            )
        )

        mapping = (
            check_mapping_consistency(
                connection
            )
        )

        sector_counts = (
            check_sector_counts(
                connection
            )
        )

        industry_counts = (
            check_industry_counts(
                connection
            )
        )

        overall_passed = all([
            universe["passed"],
            sectors["passed"],
            industries["passed"],
            company_links["passed"],
            duplicate_symbols["passed"],
            mapping["passed"],
            sector_counts["passed"],
            industry_counts["passed"],
        ])

        return {
            "report_name": (
                "Week 7 Sector / Industry "
                "Quality Report"
            ),

            "generated_at": (
                datetime.now().isoformat()
            ),

            "overall_passed": overall_passed,

            "universe": universe,

            "sectors": sectors,

            "industries": industries,

            "company_links": company_links,

            "duplicate_symbols": (
                duplicate_symbols
            ),

            "mapping_consistency": mapping,

            "sector_counts": sector_counts,

            "industry_counts": industry_counts,
        }

    finally:

        connection.close()


# ============================================================
# PRINT REPORT
# ============================================================

def print_report(report):

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 7 - SECTOR / INDUSTRY QUALITY REPORT")
    print("=" * 60)

    # --------------------------------------------------------
    # Universe
    # --------------------------------------------------------

    universe = report["universe"]

    print("\nUNIVERSE")
    print("-" * 60)

    print(
        f"Expected stocks : "
        f"{universe['expected']}"
    )

    print(
        f"Database stocks : "
        f"{universe['found']}"
    )

    print(
        "✓ Universe valid"
        if universe["passed"]
        else "❌ Universe validation failed"
    )

    # --------------------------------------------------------
    # Sectors
    # --------------------------------------------------------

    sectors = report["sectors"]

    print("\nSECTOR MASTER")
    print("-" * 60)

    print(
        f"Total sectors       : "
        f"{sectors['total']}"
    )

    print(
        f"Missing names       : "
        f"{sectors['missing_names']}"
    )

    print(
        f"Duplicate names     : "
        f"{sectors['duplicate_names']}"
    )

    print(
        "✓ Sector master valid"
        if sectors["passed"]
        else "❌ Sector master validation failed"
    )

    # --------------------------------------------------------
    # Industries
    # --------------------------------------------------------

    industries = report["industries"]

    print("\nINDUSTRY MASTER")
    print("-" * 60)

    print(
        f"Industry mappings   : "
        f"{industries['total']}"
    )

    print(
        f"Missing names       : "
        f"{industries['missing_names']}"
    )

    print(
        f"Duplicate mappings  : "
        f"{industries['duplicate_mappings']}"
    )

    print(
        f"Invalid sector links: "
        f"{industries['invalid_sector_links']}"
    )

    print(
        "✓ Industry master valid"
        if industries["passed"]
        else "❌ Industry master validation failed"
    )

    # --------------------------------------------------------
    # Company links
    # --------------------------------------------------------

    links = report["company_links"]

    print("\nCOMPANY MASTER LINKS")
    print("-" * 60)

    print(
        f"Companies           : "
        f"{links['companies']}"
    )

    print(
        f"Missing sector links: "
        f"{len(links['missing_sector_links'])}"
    )

    print(
        f"Missing industry links: "
        f"{len(links['missing_industry_links'])}"
    )

    print(
        f"Invalid sector links: "
        f"{len(links['invalid_sector_links'])}"
    )

    print(
        f"Invalid industry links: "
        f"{len(links['invalid_industry_links'])}"
    )

    print(
        "✓ Company links valid"
        if links["passed"]
        else "❌ Company link validation failed"
    )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------

    duplicates = (
        report["duplicate_symbols"]
    )

    print("\nDUPLICATE SYMBOLS")
    print("-" * 60)

    print(
        f"Duplicate groups: "
        f"{duplicates['duplicate_groups']}"
    )

    print(
        "✓ No duplicate symbols"
        if duplicates["passed"]
        else "❌ Duplicate symbols found"
    )

    # --------------------------------------------------------
    # Mapping
    # --------------------------------------------------------

    mapping = (
        report["mapping_consistency"]
    )

    print("\nMASTER MAPPING CONSISTENCY")
    print("-" * 60)

    print(
        f"Companies checked : "
        f"{mapping['companies_checked']}"
    )

    print(
        f"Mismatches        : "
        f"{len(mapping['mismatches'])}"
    )

    print(
        "✓ Company/master mappings consistent"
        if mapping["passed"]
        else "❌ Mapping mismatches found"
    )

    # --------------------------------------------------------
    # Counts
    # --------------------------------------------------------

    sector_counts = (
        report["sector_counts"]
    )

    industry_counts = (
        report["industry_counts"]
    )

    print("\nGROUP COUNT VALIDATION")
    print("-" * 60)

    print(
        f"Sectors             : "
        f"{sector_counts['sector_count']}"
    )

    print(
        f"Sector stock total   : "
        f"{sector_counts['stock_total']}"
    )

    print(
        f"Industry mappings    : "
        f"{industry_counts['industry_mapping_count']}"
    )

    print(
        f"Industry stock total : "
        f"{industry_counts['stock_total']}"
    )

    if (
        sector_counts["passed"]
        and industry_counts["passed"]
    ):
        print(
            "✓ Group counts valid"
        )
    else:
        print(
            "❌ Group count validation failed"
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\nFINAL AUDIT")
    print("-" * 60)

    if report["overall_passed"]:

        print(
            "✓ Universe validation passed"
        )

        print(
            "✓ Sector master validation passed"
        )

        print(
            "✓ Industry master validation passed"
        )

        print(
            "✓ Company links validation passed"
        )

        print(
            "✓ Duplicate symbol validation passed"
        )

        print(
            "✓ Master mapping validation passed"
        )

        print(
            "✓ Group count validation passed"
        )

        print(
            "🎉 WEEK 7 SECTOR / INDUSTRY QUALITY AUDIT PASSED"
        )

    else:

        print(
            "❌ WEEK 7 QUALITY AUDIT REQUIRES REVIEW"
        )

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    report_path = (
        REPORT_DIR
        / "week7_sector_industry_quality_report.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
        )

    print("\nReport saved:")
    print(f"  {report_path}")

    print("=" * 60)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    report = build_report()

    print_report(
        report
    )