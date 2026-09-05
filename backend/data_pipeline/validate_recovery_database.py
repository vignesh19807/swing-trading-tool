"""
Week 12 - Recovery Database Data Validation

Data Engineering responsibility:
    Validate that the recovered database contains complete,
    structurally correct, and synchronized production data.

Safety:
    - Reads only the recovery database.
    - Does not modify production data.
    - Does not modify the recovery database.
    - Does not calculate trading decisions or scores.
"""

from pathlib import Path
import sqlite3


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RECOVERY_DATABASE = (
    PROJECT_ROOT
    / "database"
    / "recovery"
    / "swing_trading_recovery.db"
)


REQUIRED_TABLES = {
    "companies",
    "daily_prices",
    "financial_scores",
    "industries",
    "opportunity_scores",
    "quarterly_results",
    "sectors",
    "signals",
    "technical_indicators",
}


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_connection():
    """Open the recovery database."""

    if not RECOVERY_DATABASE.exists():
        raise FileNotFoundError(
            f"Recovery database not found: {RECOVERY_DATABASE}"
        )

    return sqlite3.connect(RECOVERY_DATABASE)


def get_tables(connection):
    """Return application table names."""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return {row[0] for row in rows}


def get_columns(connection, table):
    """Return columns for a table."""

    rows = connection.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return {row[1] for row in rows}


def get_count(connection, table):
    """Return total rows in a table."""

    return connection.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]


# ============================================================
# VALIDATION
# ============================================================

def validate_recovery_database():

    print("=" * 60)
    print("WEEK 12 - RECOVERY DATA VALIDATION")
    print("=" * 60)

    print(
        f"Recovery database: {RECOVERY_DATABASE}"
    )

    connection = get_connection()

    try:

        failures = []

        # ----------------------------------------------------
        # 1. SQLite integrity
        # ----------------------------------------------------

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print(
            f"\nSQLite integrity : {integrity}"
        )

        if integrity != "ok":
            failures.append(
                "SQLite integrity check failed"
            )

        # ----------------------------------------------------
        # 2. Required tables
        # ----------------------------------------------------

        tables = get_tables(connection)

        missing_tables = (
            REQUIRED_TABLES - tables
        )

        print(
            f"Required tables  : {len(REQUIRED_TABLES)}"
        )

        print(
            f"Found tables     : {len(tables)}"
        )

        if missing_tables:

            print(
                "Missing tables   : "
                + ", ".join(sorted(missing_tables))
            )

            failures.append(
                "Missing tables: "
                + ", ".join(sorted(missing_tables))
            )

        else:

            print(
                "Missing tables   : NONE"
            )

        # ----------------------------------------------------
        # 3. Record counts
        # ----------------------------------------------------

        print("\nRECORD COUNTS")
        print("-" * 60)

        counts = {}

        for table in sorted(REQUIRED_TABLES):

            count = get_count(
                connection,
                table,
            )

            counts[table] = count

            print(
                f"{table:<30} {count:>8}"
            )

        # ----------------------------------------------------
        # 4. Stock universe
        # ----------------------------------------------------

        print("\nSTOCK UNIVERSE VALIDATION")
        print("-" * 60)

        company_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            """
        ).fetchone()[0]

        distinct_symbols = connection.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM companies
            """
        ).fetchone()[0]

        null_symbols = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE symbol IS NULL
               OR TRIM(symbol) = ''
            """
        ).fetchone()[0]

        print(
            f"Companies         : {company_count}"
        )

        print(
            f"Distinct symbols  : {distinct_symbols}"
        )

        print(
            f"Missing symbols   : {null_symbols}"
        )

        if company_count != 100:
            failures.append(
                f"Expected 100 companies, found {company_count}"
            )

        if distinct_symbols != 100:
            failures.append(
                f"Expected 50 distinct symbols, "
                f"found {distinct_symbols}"
            )

        if null_symbols != 0:
            failures.append(
                f"Found {null_symbols} companies with "
                "missing symbols"
            )

        # ----------------------------------------------------
        # 5. Daily price coverage
        # ----------------------------------------------------

        print("\nDAILY PRICE COVERAGE")
        print("-" * 60)

        daily_symbols = connection.execute(
            """
            SELECT COUNT(DISTINCT company_id)
            FROM daily_prices
            """
        ).fetchone()[0]

        daily_rows = counts["daily_prices"]

        companies_without_prices = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies c
            LEFT JOIN daily_prices d
                ON d.company_id = c.id
            WHERE d.company_id IS NULL
            """
        ).fetchone()[0]

        orphan_daily_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices d
            LEFT JOIN companies c
                ON c.id = d.company_id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        print(
            f"Symbols with prices       : {daily_symbols}"
        )

        print(
            f"Daily price rows          : {daily_rows}"
        )

        print(
            f"Companies without prices  : "
            f"{companies_without_prices}"
        )

        print(
            f"Orphan price rows         : "
            f"{orphan_daily_rows}"
        )

        if daily_symbols != 100:
            failures.append(
                "Daily prices do not cover all 50 companies"
            )

        if daily_rows <= 0:
            failures.append(
                "Daily price table is empty"
            )

        if companies_without_prices != 0:
            failures.append(
                "Some companies have no daily price data"
            )

        if orphan_daily_rows != 0:
            failures.append(
                "Daily prices contain orphan company_id values"
            )

        # ----------------------------------------------------
        # 6. Technical indicator coverage
        # ----------------------------------------------------

        print("\nTECHNICAL INDICATOR COVERAGE")
        print("-" * 60)

        technical_symbols = connection.execute(
            """
            SELECT COUNT(DISTINCT company_id)
            FROM technical_indicators
            """
        ).fetchone()[0]

        technical_rows = counts[
            "technical_indicators"
        ]

        companies_without_technical = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies c
            LEFT JOIN technical_indicators t
                ON t.company_id = c.id
            WHERE t.company_id IS NULL
            """
        ).fetchone()[0]

        orphan_technical_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators t
            LEFT JOIN companies c
                ON c.id = t.company_id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        print(
            f"Symbols with indicators    : "
            f"{technical_symbols}"
        )

        print(
            f"Technical rows             : "
            f"{technical_rows}"
        )

        print(
            f"Companies without technical: "
            f"{companies_without_technical}"
        )

        print(
            f"Orphan technical rows      : "
            f"{orphan_technical_rows}"
        )

        if technical_symbols != 100:
            failures.append(
                "Technical indicators do not cover all 50 companies"
            )

        if technical_rows <= 0:
            failures.append(
                "Technical indicator table is empty"
            )

        if companies_without_technical != 0:
            failures.append(
                "Some companies have no technical indicators"
            )

        if orphan_technical_rows != 0:
            failures.append(
                "Technical indicators contain orphan company_id values"
            )

        # ----------------------------------------------------
        # 7. Market / technical synchronization
        # ----------------------------------------------------

        print("\nMARKET / TECHNICAL SYNCHRONIZATION")
        print("-" * 60)

        mismatch = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    c.id AS company_id,
                    COALESCE(d.daily_count, 0) AS daily_count,
                    COALESCE(t.technical_count, 0)
                        AS technical_count
                FROM companies c

                LEFT JOIN (
                    SELECT
                        company_id,
                        COUNT(*) AS daily_count
                    FROM daily_prices
                    GROUP BY company_id
                ) d
                    ON d.company_id = c.id

                LEFT JOIN (
                    SELECT
                        company_id,
                        COUNT(*) AS technical_count
                    FROM technical_indicators
                    GROUP BY company_id
                ) t
                    ON t.company_id = c.id

                WHERE COALESCE(d.daily_count, 0)
                    != COALESCE(t.technical_count, 0)
            )
            """
        ).fetchone()[0]

        print(
            f"Stocks with row-count mismatch : "
            f"{mismatch}"
        )

        if mismatch != 0:
            failures.append(
                "Daily prices and technical indicators "
                "are not synchronized"
            )

        # ----------------------------------------------------
        # 8. Date-level synchronization
        # ----------------------------------------------------

        print("\nDATE-LEVEL SYNCHRONIZATION")
        print("-" * 60)

        missing_technical_dates = connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices d
            LEFT JOIN technical_indicators t
                ON t.company_id = d.company_id
               AND datetime(t.date) = datetime(d.date)
            WHERE t.id IS NULL
            """
        ).fetchone()[0]

        missing_market_dates = connection.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators t
            LEFT JOIN daily_prices d
                ON d.company_id = t.company_id
               AND datetime(d.date) = datetime(t.date)
            WHERE d.id IS NULL
            """
        ).fetchone()[0]

        print(
            f"Daily rows without technical data : "
            f"{missing_technical_dates}"
        )

        print(
            f"Technical rows without daily data : "
            f"{missing_market_dates}"
        )

        if missing_technical_dates != 0:
            failures.append(
                "Some daily price rows have no matching "
                "technical indicator row"
            )

        if missing_market_dates != 0:
            failures.append(
                "Some technical rows have no matching "
                "daily price row"
            )

        # ----------------------------------------------------
        # 9. Quarterly financial data
        # ----------------------------------------------------

        print("\nQUARTERLY FINANCIAL DATA")
        print("-" * 60)

        quarterly_symbols = connection.execute(
            """
            SELECT COUNT(DISTINCT company_id)
            FROM quarterly_results
            """
        ).fetchone()[0]

        quarterly_rows = counts[
            "quarterly_results"
        ]

        orphan_quarterly_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM quarterly_results q
            LEFT JOIN companies c
                ON c.id = q.company_id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        print(
            f"Companies with financial data : "
            f"{quarterly_symbols}"
        )

        print(
            f"Quarterly rows                : "
            f"{quarterly_rows}"
        )

        print(
            f"Orphan financial rows         : "
            f"{orphan_quarterly_rows}"
        )

        if quarterly_rows <= 0:
            failures.append(
                "Quarterly results table is empty"
            )

        if orphan_quarterly_rows != 0:
            failures.append(
                "Quarterly results contain orphan company_id values"
            )

        # ----------------------------------------------------
        # 10. Classification
        # ----------------------------------------------------

        print("\nCLASSIFICATION DATA")
        print("-" * 60)

        sector_count = counts["sectors"]
        industry_count = counts["industries"]

        companies_without_sector = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE sector_id IS NULL
            """
        ).fetchone()[0]

        companies_without_industry = connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE industry_id IS NULL
            """
        ).fetchone()[0]

        print(
            f"Sectors                 : {sector_count}"
        )

        print(
            f"Industries              : {industry_count}"
        )

        print(
            f"Companies without sector  : "
            f"{companies_without_sector}"
        )

        print(
            f"Companies without industry: "
            f"{companies_without_industry}"
        )

        if sector_count <= 0:
            failures.append(
                "Sectors table is empty"
            )

        if industry_count <= 0:
            failures.append(
                "Industries table is empty"
            )

        if companies_without_sector != 0:
            failures.append(
                "Some companies have no sector classification"
            )

        if companies_without_industry != 0:
            failures.append(
                "Some companies have no industry classification"
            )

        # ----------------------------------------------------
        # 11. Required columns
        # ----------------------------------------------------

        print("\nREQUIRED COLUMN VALIDATION")
        print("-" * 60)

        required_columns = {

            "companies": {
                "id",
                "symbol",
                "company_name",
            },

            "daily_prices": {
                "id",
                "company_id",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            },

            "technical_indicators": {
                "id",
                "company_id",
                "date",
                "rsi",
                "macd",
                "ema_20",
                "ema_50",
                "ema_200",
                "atr_14",
            },

            "quarterly_results": {
                "id",
                "company_id",
                "quarter",
                "revenue",
                "net_profit",
                "eps",
            },

        }

        for table, expected in required_columns.items():

            actual = get_columns(
                connection,
                table,
            )

            missing = expected - actual

            if missing:

                print(
                    f"{table:<30} FAIL"
                )

                print(
                    f"  Missing: {sorted(missing)}"
                )

                failures.append(
                    f"{table} missing columns: "
                    + ", ".join(sorted(missing))
                )

            else:

                print(
                    f"{table:<30} OK"
                )

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        print("\n" + "=" * 60)

        if failures:

            print(
                "STATUS: RECOVERY DATA VALIDATION FAILED"
            )

            print("\nFailures:")

            for failure in failures:

                print(
                    f"  - {failure}"
                )

            result = False

        else:

            print(
                "STATUS: RECOVERY DATA VALIDATION PASSED"
            )

            print(
                "All core Data Engineering contracts "
                "are satisfied."
            )

            result = True

        print("=" * 60)

        return result

    finally:

        connection.close()


def main():
    return validate_recovery_database()


if __name__ == "__main__":

    success = main()

    if not success:
        raise SystemExit(1)