"""
Week 8 - Technical Indicator Persistence Reliability Tests

Validates the persistence service before processing the full
100-stock universe.
"""

import sqlite3

from backend.data_pipeline.technical_indicator_service import (
    save_technical_indicators,
    get_technical_indicators,
    get_latest_technical_indicators,
)


# ============================================================
# PROJECT DATABASE
# ============================================================

DATABASE_PATH = "database/swing_trading.db"


# ============================================================
# TEST STOCKS
# ============================================================

TEST_STOCKS = [
    "INFY",
    "TCS",
    "WIPRO",
]


# ============================================================
# TEST 1 - STOCK PERSISTENCE
# ============================================================

def test_stock_persistence(symbol):

    records = save_technical_indicators(
        symbol
    )

    assert records > 0, (
        f"{symbol}: no records processed"
    )

    data = get_technical_indicators(
        symbol
    )

    assert not data.empty, (
        f"{symbol}: no stored records"
    )

    required_columns = {
        "symbol",
        "date",
        "rsi",
        "macd",
        "macd_signal",
        "ema_20",
        "ema_50",
        "ema_200",
        "macd_histogram",
        "atr_14",
        "technical_score",
    }

    missing = (
        required_columns
        - set(data.columns)
    )

    assert not missing, (
        f"{symbol}: missing columns {missing}"
    )

    print(
        f"✓ {symbol}: {len(data)} technical records stored"
    )

    return len(data)


# ============================================================
# TEST 2 - LATEST RECORD
# ============================================================

def test_latest_record(symbol):

    latest = get_latest_technical_indicators(
        symbol
    )

    assert latest is not None

    assert latest["symbol"] == symbol

    assert latest["date"]

    print(
        f"✓ {symbol}: latest technical record available"
    )


# ============================================================
# TEST 3 - DUPLICATE PROTECTION
# ============================================================

def test_duplicate_protection(symbol, expected_count):

    # Run persistence again.
    save_technical_indicators(
        symbol
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        company_id = connection.execute(
            """
            SELECT id
            FROM companies
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()[0]

        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators
            WHERE company_id = ?
            """,
            (company_id,),
        ).fetchone()[0]

        duplicate_groups = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT company_id, date
                FROM technical_indicators
                WHERE company_id = ?
                GROUP BY company_id, date
                HAVING COUNT(*) > 1
            )
            """,
            (company_id,),
        ).fetchone()[0]

    finally:

        connection.close()

    assert total == expected_count, (
        f"{symbol}: expected {expected_count}, "
        f"found {total}"
    )

    assert duplicate_groups == 0, (
        f"{symbol}: duplicate groups found"
    )

    print(
        f"✓ {symbol}: duplicate protection passed"
    )


# ============================================================
# TEST 4 - INVALID SYMBOL
# ============================================================

def test_invalid_symbol():

    result = save_technical_indicators(
        "INVALID_SYMBOL"
    )

    assert result == 0

    data = get_technical_indicators(
        "INVALID_SYMBOL"
    )

    assert data.empty

    latest = get_latest_technical_indicators(
        "INVALID_SYMBOL"
    )

    assert latest is None

    print(
        "✓ Invalid symbol handled safely"
    )


# ============================================================
# TEST 5 - DATABASE INTEGRITY
# ============================================================

def test_database_integrity():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        required = {
            "rsi",
            "macd",
            "macd_signal",
            "ema_20",
            "ema_50",
            "ema_200",
            "macd_histogram",
            "atr_14",
            "technical_score",
        }

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(technical_indicators)"
            ).fetchall()
        }

        missing = required - columns

        assert not missing, (
            f"Missing database columns: {missing}"
        )

        foreign_key_errors = connection.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators ti
            LEFT JOIN companies c
                ON ti.company_id = c.id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        assert foreign_key_errors == 0

    finally:

        connection.close()

    print(
        "✓ Database integrity passed"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - TECHNICAL PERSISTENCE RELIABILITY TEST")
    print("=" * 60)

    passed = 0
    failed = 0

    counts = {}

    # --------------------------------------------------------
    # Test stocks
    # --------------------------------------------------------

    for symbol in TEST_STOCKS:

        print(
            "\n" + "-" * 50
        )

        print(
            f"TESTING {symbol}"
        )

        print(
            "-" * 50
        )

        try:

            count = test_stock_persistence(
                symbol
            )

            counts[symbol] = count

            test_latest_record(
                symbol
            )

            test_duplicate_protection(
                symbol,
                count,
            )

            passed += 3

        except Exception as error:

            failed += 1

            print(
                f"✗ {symbol} failed: {error}"
            )

    # --------------------------------------------------------
    # Invalid symbol
    # --------------------------------------------------------

    try:

        test_invalid_symbol()

        passed += 1

    except Exception as error:

        failed += 1

        print(
            f"✗ Invalid symbol test failed: {error}"
        )

    # --------------------------------------------------------
    # Database integrity
    # --------------------------------------------------------

    try:

        test_database_integrity()

        passed += 1

    except Exception as error:

        failed += 1

        print(
            f"✗ Database integrity failed: {error}"
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "TECHNICAL PERSISTENCE RELIABILITY SUMMARY"
    )

    print(
        "=" * 60
    )

    print(
        f"Tests passed : {passed}"
    )

    print(
        f"Tests failed : {failed}"
    )

    print(
        "\nStored record counts:"
    )

    for symbol, count in counts.items():

        print(
            f"  {symbol:<10}: {count}"
        )

    if failed == 0:

        print(
            "\n🎉 WEEK 8 TECHNICAL PERSISTENCE "
            "RELIABILITY TEST PASSED"
        )

    else:

        print(
            "\n⚠ TECHNICAL PERSISTENCE "
            "REQUIRES REVIEW"
        )

        raise SystemExit(1)

    print(
        "=" * 60
    )


if __name__ == "__main__":

    main()