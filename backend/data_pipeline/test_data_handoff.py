"""
Data → Logic Engineer Handoff Test
===================================

Verifies that the Data Service provides clean,
usable market data to the Logic Engineering layer.
"""

from backend.data_pipeline.data_service import (
    get_stock_data,
    get_available_stocks,
)


# ============================================================
# CONFIGURATION
# ============================================================

TEST_STOCKS = [
    "INFY",
    "TCS",
    "WIPRO",
    "RELIANCE",
    "HDFCBANK",
]


REQUIRED_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


# ============================================================
# TEST DATA SERVICE
# ============================================================

def test_stock(symbol):

    print(
        f"\nTesting {symbol}..."
    )

    data = get_stock_data(symbol)

    # --------------------------------------------------------
    # DATA EXISTS
    # --------------------------------------------------------

    if data is None or data.empty:

        print(
            f"❌ {symbol}: No data returned"
        )

        return False

    print(
        f"✓ Records: {len(data)}"
    )

    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:

        print(
            f"❌ Missing columns: "
            f"{missing_columns}"
        )

        return False

    print(
        "✓ Required columns present"
    )

    # --------------------------------------------------------
    # DATE ORDER
    # --------------------------------------------------------

    if not data["date"].is_monotonic_increasing:

        print(
            "❌ Data is not chronologically sorted"
        )

        return False

    print(
        "✓ Data sorted chronologically"
    )

    # --------------------------------------------------------
    # MISSING VALUES
    # --------------------------------------------------------

    critical_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    if data[critical_columns].isnull().any().any():

        print(
            "❌ Missing critical values"
        )

        return False

    print(
        "✓ No missing critical values"
    )

    # --------------------------------------------------------
    # PRICE VALIDATION
    # --------------------------------------------------------

    if (data["close"] <= 0).any():

        print(
            "❌ Invalid close prices"
        )

        return False

    print(
        "✓ Valid close prices"
    )

    # --------------------------------------------------------
    # LOGIC ENGINEER CALCULATION TEST
    # --------------------------------------------------------

    data["daily_return"] = (
        data["close"].pct_change()
    )

    print(
        "✓ Technical calculation possible"
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print(
        f"✓ {symbol} handoff successful"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n=========================================="
    )

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "DATA → LOGIC HANDOFF TEST"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # AVAILABLE STOCKS
    # --------------------------------------------------------

    stocks = get_available_stocks()

    print(
        f"\nAvailable stocks: {len(stocks)}"
    )

    if len(stocks) < 50:

        print(
            "❌ Expected at least 50 stocks"
        )

        return False

    print(
        "✓ 50-stock universe available"
    )

    # --------------------------------------------------------
    # TEST REPRESENTATIVE STOCKS
    # --------------------------------------------------------

    passed = 0

    for symbol in TEST_STOCKS:

        if test_stock(symbol):

            passed += 1

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print(
        "\n------------------------------------------"
    )

    print(
        f"Stocks tested : {len(TEST_STOCKS)}"
    )

    print(
        f"Tests passed  : {passed}"
    )

    print(
        f"Tests failed  : "
        f"{len(TEST_STOCKS) - passed}"
    )

    print(
        "------------------------------------------"
    )

    if passed == len(TEST_STOCKS):

        print(
            "🎉 DATA → LOGIC HANDOFF PASSED"
        )

        print(
            "Logic Engineer can consume "
            "market data through Data Service."
        )

        print(
            "=========================================="
        )

        return True

    print(
        "❌ DATA → LOGIC HANDOFF FAILED"
    )

    print(
        "=========================================="
    )

    return False


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)