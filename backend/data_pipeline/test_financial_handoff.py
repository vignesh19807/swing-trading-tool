"""
Financial Data → Logic Handoff Test
===================================

Verifies that the Logic Engineer can consume
financial data through financial_service.py
without accessing SQLite directly.
"""

from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_latest_financial_data,
)


TEST_STOCKS = [
    "INFY",
    "TCS",
    "WIPRO",
    "RELIANCE",
    "HDFCBANK",
]


REQUIRED_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "industry",
    "quarter",
    "revenue",
    "net_profit",
    "eps",
    "roe",
    "roce",
    "debt_equity",
    "operating_margin",
    "net_margin",
]


def main():

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("FINANCIAL DATA → LOGIC HANDOFF TEST")
    print("==========================================")

    passed = 0
    failed = 0

    for symbol in TEST_STOCKS:

        print("\n------------------------------------------")
        print(f"Testing {symbol}...")
        print("------------------------------------------")

        data = get_financial_data(symbol)

        # ----------------------------------------------------
        # Data existence
        # ----------------------------------------------------

        if data.empty:

            print(
                "❌ No financial data returned"
            )

            failed += 1
            continue

        print(
            f"✓ Records: {len(data)}"
        )

        # ----------------------------------------------------
        # Required columns
        # ----------------------------------------------------

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

            failed += 1
            continue

        print(
            "✓ Required financial columns present"
        )

        # ----------------------------------------------------
        # Symbol consistency
        # ----------------------------------------------------

        if not (data["symbol"] == symbol).all():

            print(
                "❌ Symbol mismatch detected"
            )

            failed += 1
            continue

        print(
            "✓ Symbol mapping correct"
        )

        # ----------------------------------------------------
        # Chronological order
        # ----------------------------------------------------

        if not data["quarter"].is_monotonic_increasing:

            print(
                "❌ Financial records not "
                "chronologically sorted"
            )

            failed += 1
            continue

        print(
            "✓ Financial records sorted chronologically"
        )

        # ----------------------------------------------------
        # Latest record
        # ----------------------------------------------------

        latest = get_latest_financial_data(
            symbol
        )

        if latest is None:

            print(
                "❌ Latest financial record unavailable"
            )

            failed += 1
            continue

        print(
            f"✓ Latest quarter: "
            f"{latest['quarter']}"
        )

        # ----------------------------------------------------
        # Revenue / profit sanity
        # ----------------------------------------------------

        numeric_check_passed = True

        for column in [
            "revenue",
            "net_profit",
            "eps",
        ]:

            values = data[column].dropna()

            if not values.map(
                lambda value: isinstance(
                    value,
                    (int, float)
                )
            ).all():

                numeric_check_passed = False

                print(
                    f"❌ Invalid values in {column}"
                )

        if not numeric_check_passed:

            failed += 1
            continue

        print(
            "✓ Financial numeric fields valid"
        )

        # ----------------------------------------------------
        # Handoff successful
        # ----------------------------------------------------

        print(
            f"✓ {symbol} financial handoff successful"
        )

        passed += 1

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

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
        f"Tests failed  : {failed}"
    )

    print(
        "------------------------------------------"
    )

    if failed == 0:

        print(
            "🎉 FINANCIAL DATA → LOGIC HANDOFF PASSED"
        )

        print(
            "Logic Engineer can consume financial "
            "data through Financial Data Service."
        )

    else:

        print(
            "⚠ FINANCIAL HANDOFF REQUIRES REVIEW"
        )

    print(
        "=========================================="
    )


if __name__ == "__main__":

    main()