import sqlite3
import sys
from pathlib import Path

# Force stdout/stderr to use UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')



# ============================================================
# PROJECT / DATABASE PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


# ============================================================
# REQUIRED PROJECT TABLES
# ============================================================
REQUIRED_TABLES = {
    "companies",
    "daily_prices",
    "quarterly_results",
    "technical_indicators",
    "financial_scores",
    "opportunity_scores",
    "signals",
    "sectors",
    "industries",
}
EXPECTED_COMPANIES = 50



# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return sqlite3.connect(DATABASE_PATH)


# ============================================================
# 1. VERIFY DATABASE TABLES
# ============================================================

def verify_tables(cursor):

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = {row[0] for row in cursor.fetchall()}

    print("\n======================================")
    print("DATABASE TABLE VERIFICATION")
    print("======================================")

    for table in sorted(tables):
        print(f"✓ {table}")

    missing_tables = REQUIRED_TABLES - tables
    unexpected_tables = tables - REQUIRED_TABLES

    print("--------------------------------------")
    print(f"Project tables found: {len(tables)}")

    if missing_tables:
        print("\n❌ Missing required tables:")

        for table in sorted(missing_tables):
            print(f"   - {table}")

    if unexpected_tables:
        print("\n⚠ Unexpected project tables:")

        for table in sorted(unexpected_tables):
            print(f"   - {table}")

    if not missing_tables and not unexpected_tables:
        print("✓ All 10 required project tables are present")

    return tables


# ============================================================
# 2. VERIFY COMPANIES
# ============================================================

def verify_companies(cursor):

    cursor.execute("""
        SELECT
            id,
            symbol,
            company_name,
            sector,
            exchange
        FROM companies
        ORDER BY id
    """)

    companies = cursor.fetchall()

    print("\n======================================")
    print("COMPANY VERIFICATION")
    print("======================================")

    for company in companies:

        company_id = company[0]
        symbol = company[1]
        company_name = company[2]
        sector = company[3]
        exchange = company[4]

        print(
            f"{company_id}. "
            f"{symbol} | "
            f"{company_name} | "
            f"{sector} | "
            f"{exchange}"
        )

    print("--------------------------------------")
    print(f"Total companies: {len(companies)}")

    return companies


# ============================================================
# 3. PRICE RECORD COUNT PER COMPANY
# ============================================================

def verify_price_counts(cursor):

    cursor.execute("""
        SELECT
            c.symbol,
            COUNT(dp.id)
        FROM companies c
        LEFT JOIN daily_prices dp
            ON c.id = dp.company_id
        GROUP BY c.id, c.symbol
        ORDER BY c.symbol
    """)

    results = cursor.fetchall()

    print("\n======================================")
    print("PRICE RECORDS PER COMPANY")
    print("======================================")

    for symbol, count in results:

        print(
            f"{symbol:<12} {count} records"
        )

    return results


# ============================================================
# 4. DATE RANGE
# ============================================================

def verify_date_ranges(cursor):

    cursor.execute("""
        SELECT
            c.symbol,
            MIN(dp.date),
            MAX(dp.date)
        FROM companies c
        JOIN daily_prices dp
            ON c.id = dp.company_id
        GROUP BY c.id, c.symbol
        ORDER BY c.symbol
    """)

    results = cursor.fetchall()

    print("\n======================================")
    print("DATE RANGE VERIFICATION")
    print("======================================")

    for symbol, oldest, newest in results:

        print(
            f"{symbol:<12} "
            f"{oldest} → {newest}"
        )

    return results


# ============================================================
# 5. TOTAL PRICE RECORDS
# ============================================================

def verify_total_records(cursor):

    cursor.execute("""
        SELECT COUNT(*)
        FROM daily_prices
    """)

    total = cursor.fetchone()[0]

    print("\n======================================")
    print("TOTAL PRICE RECORDS")
    print("======================================")

    print(f"Total daily price records: {total}")

    return total


# ============================================================
# 6. DUPLICATE RECORD CHECK
# ============================================================

def verify_duplicates(cursor):

    cursor.execute("""
        SELECT
            company_id,
            date,
            COUNT(*)
        FROM daily_prices
        GROUP BY company_id, date
        HAVING COUNT(*) > 1
    """)

    duplicates = cursor.fetchall()

    print("\n======================================")
    print("DUPLICATE RECORD CHECK")
    print("======================================")

    if not duplicates:

        print("✓ No duplicate records found")

    else:

        print(
            f"⚠ Found {len(duplicates)} duplicate groups"
        )

        for duplicate in duplicates:

            company_id, date, count = duplicate

            print(
                f"Company ID: {company_id} | "
                f"Date: {date} | "
                f"Count: {count}"
            )

    return duplicates


# ============================================================
# 7. MISSING OHLC CHECK
# ============================================================

def verify_missing_ohlc(cursor):

    cursor.execute("""
        SELECT COUNT(*)
        FROM daily_prices
        WHERE open IS NULL
           OR high IS NULL
           OR low IS NULL
           OR close IS NULL
    """)

    missing = cursor.fetchone()[0]

    print("\n======================================")
    print("MISSING OHLC CHECK")
    print("======================================")

    if missing == 0:

        print("✓ No missing OHLC values")

    else:

        print(
            f"⚠ {missing} records have missing OHLC values"
        )

    return missing


# ============================================================
# 8. INVALID PRICE CHECK
# ============================================================

def verify_invalid_prices(cursor):

    cursor.execute("""
        SELECT COUNT(*)
        FROM daily_prices
        WHERE open <= 0
           OR high <= 0
           OR low <= 0
           OR close <= 0
    """)

    invalid = cursor.fetchone()[0]

    print("\n======================================")
    print("INVALID PRICE CHECK")
    print("======================================")

    if invalid == 0:

        print("✓ No invalid price values")

    else:

        print(
            f"⚠ {invalid} records contain invalid prices"
        )

    return invalid


# ============================================================
# 9. INVALID VOLUME CHECK
# ============================================================

def verify_volume(cursor):

    cursor.execute("""
        SELECT COUNT(*)
        FROM daily_prices
        WHERE volume < 0
    """)

    invalid = cursor.fetchone()[0]

    print("\n======================================")
    print("VOLUME VALIDATION")
    print("======================================")

    if invalid == 0:

        print("✓ No negative volume values")

    else:

        print(
            f"⚠ {invalid} records have negative volume"
        )

    return invalid


# ============================================================
# 10. OHLC LOGIC CHECK
# ============================================================

def verify_ohlc_logic(cursor):

    cursor.execute("""
        SELECT COUNT(*)
        FROM daily_prices
        WHERE high < low
           OR high < open
           OR high < close
           OR low > open
           OR low > close
    """)

    invalid = cursor.fetchone()[0]

    print("\n======================================")
    print("OHLC LOGIC VALIDATION")
    print("======================================")

    if invalid == 0:

        print("✓ OHLC relationships are valid")

    else:

        print(
            f"⚠ {invalid} records have invalid OHLC relationships"
        )

    return invalid


# ============================================================
# 11. DATABASE SUMMARY
# ============================================================

def database_summary(cursor):

    cursor.execute("""
        SELECT COUNT(*)
        FROM companies
    """)

    companies = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM daily_prices
    """)

    prices = cursor.fetchone()[0]

    print("\n======================================")
    print("DATABASE SUMMARY")
    print("======================================")

    print(f"Companies       : {companies}")
    print(f"Price records   : {prices}")
    print(f"Database file   : {DATABASE_PATH}")


# ============================================================
# 12. MAIN VALIDATION
# ============================================================

def main():

    print("\n")
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("DATABASE DATA VALIDATION")
    print("==========================================")

    # --------------------------------------------------------
    # Check database exists
    # --------------------------------------------------------

    if not DATABASE_PATH.exists():

        print("❌ ERROR: Database file does not exist.")
        print(f"Expected location: {DATABASE_PATH}")

        return

    # --------------------------------------------------------
    # Connect to database
    # --------------------------------------------------------

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Run validation checks
    # --------------------------------------------------------

    tables = verify_tables(cursor)

    companies = verify_companies(cursor)
    company_count = len(companies)

    price_counts = verify_price_counts(cursor)

    date_ranges = verify_date_ranges(cursor)

    total_records = verify_total_records(cursor)

    duplicates = verify_duplicates(cursor)

    missing_ohlc = verify_missing_ohlc(cursor)

    invalid_prices = verify_invalid_prices(cursor)

    invalid_volume = verify_volume(cursor)

    invalid_ohlc = verify_ohlc_logic(cursor)

    database_summary(cursor)

    # --------------------------------------------------------
    # Close database
    # --------------------------------------------------------

    connection.close()

    # ========================================================
    # FINAL DATA QUALITY RESULT
    # ========================================================

    print("\n==========================================")
    print("FINAL DATA QUALITY RESULT")
    print("==========================================")

    checks_passed = True

    # --------------------------------------------------------
    # TABLE CHECK
    # --------------------------------------------------------

    if tables == REQUIRED_TABLES:

        print(f"✓ {len(REQUIRED_TABLES)} required project tables")

    else:

        print("❌ Required project table check failed")

        checks_passed = False

    # --------------------------------------------------------
    # COMPANY CHECK
    # --------------------------------------------------------

    if company_count == EXPECTED_COMPANIES:
        print(f"✓ {EXPECTED_COMPANIES} companies")
    else:
        print(
        f"❌ Expected {EXPECTED_COMPANIES} companies, "
        f"found {company_count}"
     )
        checks_passed = False

    # --------------------------------------------------------
    # PRICE RECORD CHECK
    # --------------------------------------------------------

    if total_records > 0:

        print("✓ Price records exist")

    else:

        print("❌ No price records found")

        checks_passed = False

    # --------------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------------

    if not duplicates:

        print("✓ No duplicate records")

    else:

        print("❌ Duplicate records found")

        checks_passed = False

    # --------------------------------------------------------
    # MISSING OHLC CHECK
    # --------------------------------------------------------

    if missing_ohlc == 0:

        print("✓ No missing OHLC values")

    else:

        print("❌ Missing OHLC values found")

        checks_passed = False

    # --------------------------------------------------------
    # INVALID PRICE CHECK
    # --------------------------------------------------------

    if invalid_prices == 0:

        print("✓ No invalid price values")

    else:

        print("❌ Invalid price values found")

        checks_passed = False

    # --------------------------------------------------------
    # VOLUME CHECK
    # --------------------------------------------------------

    if invalid_volume == 0:

        print("✓ No negative volume values")

    else:

        print("❌ Invalid volume values found")

        checks_passed = False

    # --------------------------------------------------------
    # OHLC LOGIC CHECK
    # --------------------------------------------------------

    if invalid_ohlc == 0:

        print("✓ OHLC relationships valid")

    else:

        print("❌ Invalid OHLC relationships found")

        checks_passed = False

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print("------------------------------------------")

    if checks_passed:

        print("🎉 DATA VALIDATION PASSED")

    else:

        print("⚠ DATA VALIDATION FAILED")

    print("==========================================\n")

    return checks_passed


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()