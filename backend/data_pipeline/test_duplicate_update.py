"""
Week 9 - Duplicate Update Reliability Test

Verifies that the same daily market record cannot be inserted twice.
"""

import sqlite3

from backend.data_pipeline.load_stock_data import insert_daily_prices


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 9 - DUPLICATE UPDATE RELIABILITY TEST")
    print("=" * 60)

    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()

    # Create isolated test table with the same uniqueness rule.
    cursor.execute("""
        CREATE TABLE daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            adjusted_close REAL,
            UNIQUE(company_id, date)
        )
    """)

    # Use a small DataFrame.
    import pandas as pd

    test_date = "2026-08-24"

    data = pd.DataFrame([
        {
            "date": pd.Timestamp(test_date),
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 103.0,
            "volume": 10000,
            "adjusted_close": 103.0,
        }
    ])

    company_id = 1

    print("\nFirst insertion:")

    inserted_1, skipped_1 = insert_daily_prices(
        cursor,
        company_id,
        data,
    )

    print(f"  Inserted: {inserted_1}")
    print(f"  Skipped : {skipped_1}")

    print("\nSecond insertion of identical record:")

    inserted_2, skipped_2 = insert_daily_prices(
        cursor,
        company_id,
        data,
    )

    print(f"  Inserted: {inserted_2}")
    print(f"  Skipped : {skipped_2}")

    stored_date = pd.Timestamp(test_date).isoformat()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM daily_prices
        WHERE company_id = ?
          AND date = ?
        """,
        (company_id, stored_date),
    )

    record_count = cursor.fetchone()[0]

    print("\nDuplicate protection checks:")

    if inserted_1 == 1:
        print("  ✓ First update inserted the record")
    else:
        raise AssertionError(
            "First insertion should insert one record."
        )

    if inserted_2 == 0 and skipped_2 == 1:
        print("  ✓ Second update skipped the duplicate")
    else:
        raise AssertionError(
            "Second insertion should be skipped."
        )

    if record_count == 1:
        print("  ✓ Database contains exactly one record")
    else:
        raise AssertionError(
            f"Expected exactly one record, found {record_count}."
        )

    print()
    print("=" * 60)
    print("DUPLICATE UPDATE RELIABILITY SUMMARY")
    print("=" * 60)
    print("Tests passed : 3")
    print("Tests failed : 0")
    print()
    print("🎉 WEEK 9 DUPLICATE UPDATE RELIABILITY TEST PASSED")
    print("=" * 60)

    connection.close()


if __name__ == "__main__":
    main()