"""
Week 7 - Sector / Industry Master Data Migration

Responsibilities:
    1. Create sectors master table
    2. Create industries master table
    3. Populate master data from STOCK_UNIVERSE
    4. Add sector_id and industry_id to companies
    5. Link all companies to their master records
    6. Verify the migration
    7. Preserve existing sector/industry text columns

This migration is designed to be idempotent.
It can safely be executed more than once.

No trading logic is performed here.
"""

import sqlite3
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


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """
    Normalize text for comparisons and master-data keys.
    """

    if value is None:
        return ""

    return " ".join(
        str(value).strip().split()
    )


# ============================================================
# CREATE MASTER TABLES
# ============================================================

def create_master_tables(cursor):
    """
    Create sectors and industries master tables.
    """

    cursor.execute("DROP TABLE IF EXISTS industries")
    cursor.execute("DROP TABLE IF EXISTS sectors")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS industries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sector_id INTEGER NOT NULL,

            FOREIGN KEY (sector_id)
                REFERENCES sectors(id),

            UNIQUE(name, sector_id)
        )
        """
    )


# ============================================================
# ADD COMPANY FOREIGN KEY COLUMNS
# ============================================================

def add_company_columns(cursor):
    """
    Add sector_id and industry_id to companies
    if they do not already exist.
    """

    columns = {
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(companies)"
        ).fetchall()
    }

    if "sector_id" not in columns:

        cursor.execute(
            """
            ALTER TABLE companies
            ADD COLUMN sector_id INTEGER
            """
        )

        print(
            "✓ Added companies.sector_id"
        )

    else:

        print(
            "✓ companies.sector_id already exists"
        )

    if "industry_id" not in columns:

        cursor.execute(
            """
            ALTER TABLE companies
            ADD COLUMN industry_id INTEGER
            """
        )

        print(
            "✓ Added companies.industry_id"
        )

    else:

        print(
            "✓ companies.industry_id already exists"
        )


# ============================================================
# POPULATE SECTORS
# ============================================================

def populate_sectors(cursor):
    """
    Insert all unique sectors from STOCK_UNIVERSE.
    """

    sectors = sorted(
        {
            normalize_text(
                stock["sector"]
            )
            for stock in STOCK_UNIVERSE
            if normalize_text(
                stock["sector"]
            )
        }
    )

    for sector in sectors:

        cursor.execute(
            """
            INSERT OR IGNORE INTO sectors (
                name
            )
            VALUES (?)
            """,
            (sector,)
        )

    return sectors


# ============================================================
# POPULATE INDUSTRIES
# ============================================================

def populate_industries(cursor):
    """
    Insert unique industry + sector relationships
    from STOCK_UNIVERSE.
    """

    mappings = sorted(
        {
            (
                normalize_text(
                    stock["industry"]
                ),
                normalize_text(
                    stock["sector"]
                ),
            )
            for stock in STOCK_UNIVERSE
            if normalize_text(
                stock["industry"]
            )
        }
    )

    inserted = 0

    for industry, sector in mappings:

        row = cursor.execute(
            """
            SELECT id
            FROM sectors
            WHERE name = ?
            """,
            (sector,)
        ).fetchone()

        if row is None:

            raise RuntimeError(
                f"Sector not found for industry "
                f"{industry}: {sector}"
            )

        sector_id = row[0]

        cursor.execute(
            """
            INSERT OR IGNORE INTO industries (
                name,
                sector_id
            )
            VALUES (?, ?)
            """,
            (
                industry,
                sector_id,
            )
        )

        inserted += 1

    return mappings


# ============================================================
# LINK COMPANIES
# ============================================================

def link_companies(cursor):
    """
    Link every company to its sector and industry
    master records using the existing text values.
    """

    companies = cursor.execute(
        """
        SELECT
            id,
            symbol,
            sector,
            industry
        FROM companies
        ORDER BY symbol
        """
    ).fetchall()

    updated = 0
    failed = []

    for (
        company_id,
        symbol,
        sector,
        industry,
    ) in companies:

        sector_name = normalize_text(
            sector
        )

        industry_name = normalize_text(
            industry
        )

        sector_row = cursor.execute(
            """
            SELECT id
            FROM sectors
            WHERE name = ?
            """,
            (sector_name,)
        ).fetchone()

        if sector_row is None:

            failed.append(
                (
                    symbol,
                    "sector",
                    sector_name,
                )
            )

            continue

        sector_id = sector_row[0]

        industry_row = cursor.execute(
            """
            SELECT id
            FROM industries
            WHERE name = ?
              AND sector_id = ?
            """,
            (
                industry_name,
                sector_id,
            )
        ).fetchone()

        if industry_row is None:

            failed.append(
                (
                    symbol,
                    "industry",
                    industry_name,
                )
            )

            continue

        industry_id = industry_row[0]

        cursor.execute(
            """
            UPDATE companies
            SET
                sector_id = ?,
                industry_id = ?
            WHERE id = ?
            """,
            (
                sector_id,
                industry_id,
                company_id,
            )
        )

        updated += 1

    return updated, failed


# ============================================================
# CREATE INDEXES
# ============================================================

def create_indexes(cursor):
    """
    Create indexes used by sector/industry queries.
    """

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_companies_sector_id
        ON companies(sector_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_companies_industry_id
        ON companies(industry_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_industries_sector_id
        ON industries(sector_id)
        """
    )

    print(
        "✓ Sector/industry indexes created"
    )


# ============================================================
# VERIFY MIGRATION
# ============================================================

def verify_migration(cursor):
    """
    Verify that the complete 50-stock universe
    is correctly linked.
    """

    company_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM companies
        """
    ).fetchone()[0]

    sector_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM sectors
        """
    ).fetchone()[0]

    industry_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM industries
        """
    ).fetchone()[0]

    unlinked_sectors = cursor.execute(
        """
        SELECT COUNT(*)
        FROM companies
        WHERE sector_id IS NULL
        """
    ).fetchone()[0]

    unlinked_industries = cursor.execute(
        """
        SELECT COUNT(*)
        FROM companies
        WHERE industry_id IS NULL
        """
    ).fetchone()[0]

    invalid_sector_links = cursor.execute(
        """
        SELECT COUNT(*)
        FROM companies c
        LEFT JOIN sectors s
            ON c.sector_id = s.id
        WHERE c.sector_id IS NOT NULL
          AND s.id IS NULL
        """
    ).fetchone()[0]

    invalid_industry_links = cursor.execute(
        """
        SELECT COUNT(*)
        FROM companies c
        LEFT JOIN industries i
            ON c.industry_id = i.id
        WHERE c.industry_id IS NOT NULL
          AND i.id IS NULL
        """
    ).fetchone()[0]

    return {
        "companies": company_count,
        "sectors": sector_count,
        "industries": industry_count,
        "unlinked_sectors": unlinked_sectors,
        "unlinked_industries": unlinked_industries,
        "invalid_sector_links": invalid_sector_links,
        "invalid_industry_links":
            invalid_industry_links,
    }


# ============================================================
# PRINT VERIFICATION
# ============================================================

def print_verification(result):
    """
    Print migration verification results.
    """

    print(
        "\n------------------------------------------"
    )

    print(
        "WEEK 7 MASTER DATA VERIFICATION"
    )

    print(
        "------------------------------------------"
    )

    print(
        f"Companies       : "
        f"{result['companies']}"
    )

    print(
        f"Sectors         : "
        f"{result['sectors']}"
    )

    print(
        f"Industries      : "
        f"{result['industries']}"
    )

    print(
        f"Unlinked sectors: "
        f"{result['unlinked_sectors']}"
    )

    print(
        f"Unlinked industry links: "
        f"{result['unlinked_industries']}"
    )

    print(
        f"Invalid sector links: "
        f"{result['invalid_sector_links']}"
    )

    print(
        f"Invalid industry links: "
        f"{result['invalid_industry_links']}"
    )

    passed = (
        result["companies"] == 50
        and result["sectors"] == 16
        and result["industries"] == 32
        and result["unlinked_sectors"] == 0
        and result["unlinked_industries"] == 0
        and result["invalid_sector_links"] == 0
        and result["invalid_industry_links"] == 0
    )

    if passed:

        print(
            "\n✓ 50 companies verified"
        )

        print(
            "✓ 16 sectors verified"
        )

        print(
            "✓ 32 industries verified"
        )

        print(
            "✓ All companies linked"
        )

        print(
            "✓ All foreign-key references valid"
        )

        print(
            "\n🎉 WEEK 7 MASTER DATA MIGRATION PASSED"
        )

    else:

        print(
            "\n❌ WEEK 7 MASTER DATA MIGRATION FAILED"
        )

    return passed


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "WEEK 7 - SECTOR / INDUSTRY MASTER DATA"
    )

    print("=" * 60)

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        cursor = connection.cursor()

        cursor.execute(
            "PRAGMA foreign_keys = ON"
        )

        # ----------------------------------------------------
        # Step 1
        # ----------------------------------------------------

        print(
            "\n[1/6] Creating master tables..."
        )

        create_master_tables(
            cursor
        )

        print(
            "✓ Master tables ready"
        )

        # ----------------------------------------------------
        # Step 2
        # ----------------------------------------------------

        print(
            "\n[2/6] Adding company master-data links..."
        )

        add_company_columns(
            cursor
        )

        # ----------------------------------------------------
        # Step 3
        # ----------------------------------------------------

        print(
            "\n[3/6] Populating sectors..."
        )

        sectors = populate_sectors(
            cursor
        )

        print(
            f"✓ Sectors available: "
            f"{len(sectors)}"
        )

        # ----------------------------------------------------
        # Step 4
        # ----------------------------------------------------

        print(
            "\n[4/6] Populating industries..."
        )

        industries = populate_industries(
            cursor
        )

        print(
            f"✓ Industry mappings available: "
            f"{len(industries)}"
        )

        # ----------------------------------------------------
        # Step 5
        # ----------------------------------------------------

        print(
            "\n[5/6] Linking companies..."
        )

        updated, failed = link_companies(
            cursor
        )

        print(
            f"✓ Companies processed: "
            f"{updated}"
        )

        if failed:

            print(
                "\n❌ Company linking failures:"
            )

            for item in failed:

                print(
                    f"   {item}"
                )

            connection.rollback()

            raise RuntimeError(
                "Company linking failed. "
                "Migration rolled back."
            )

        # ----------------------------------------------------
        # Step 6
        # ----------------------------------------------------

        print(
            "\n[6/6] Creating indexes..."
        )

        create_indexes(
            cursor
        )

        # ----------------------------------------------------
        # Verification BEFORE COMMIT
        # ----------------------------------------------------

        result = verify_migration(
            cursor
        )

        passed = print_verification(
            result
        )

        if not passed:

            connection.rollback()

            print(
                "\n❌ Migration rolled back."
            )

            return False

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

        print(
            "\n✓ Migration committed successfully"
        )

        print(
            "\nExisting sector/industry text columns "
            "were preserved."
        )

        print(
            "=" * 60
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "\n❌ Migration failed."
        )

        print(
            f"Error: {error}"
        )

        print(
            "All changes were rolled back."
        )

        return False

    finally:

        connection.close()


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)