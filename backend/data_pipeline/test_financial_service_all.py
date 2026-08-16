"""
50-Stock Financial Service Handoff Test
========================================

Week 3 Final Data → Logic verification.

Verifies that all 50 stocks can be consumed through
financial_service.py.

This test does NOT:
    - fetch from yfinance
    - modify the database
    - calculate financial scores

It only tests the Data Engineer → Logic Engineer interface.
"""

from backend.data_pipeline.stock_universe import (
    STOCK_UNIVERSE,
)

from backend.data_pipeline.financial_service import (
    get_financial_data,
)


# ============================================================
# REQUIRED FINANCIAL COLUMNS
# ============================================================

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


# ============================================================
# GET SYMBOLS
# ============================================================

def get_symbols():

    symbols = []

    for stock in STOCK_UNIVERSE:

        if isinstance(stock, dict):

            symbol = stock.get("symbol")

        else:

            symbol = str(stock)

        if symbol:

            symbols.append(
                symbol.upper().strip()
            )

    return symbols


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("50-STOCK FINANCIAL SERVICE TEST")
    print("==========================================")

    symbols = get_symbols()

    print(
        f"\nStocks in universe: {len(symbols)}"
    )

    passed = 0
    failed = 0

    failures = []

    # ========================================================
    # TEST EACH STOCK
    # ========================================================

    for index, symbol in enumerate(
        symbols,
        start=1
    ):

        print(
            "\n------------------------------------------"
        )

        print(
            f"[{index}/{len(symbols)}] Testing {symbol}"
        )

        print(
            "------------------------------------------"
        )

        # ----------------------------------------------------
        # Get financial data through service
        # ----------------------------------------------------

        try:

            data = get_financial_data(
                symbol
            )

        except Exception as error:

            print(
                f"❌ Service error: {error}"
            )

            failures.append(
                (symbol, "service error")
            )

            failed += 1

            continue

        # ----------------------------------------------------
        # Check data exists
        # ----------------------------------------------------

        if data.empty:

            print(
                "❌ No financial records returned"
            )

            failures.append(
                (symbol, "no financial data")
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

            failures.append(
                (
                    symbol,
                    "missing columns"
                )
            )

            failed += 1

            continue

        print(
            "✓ Required columns present"
        )

        # ----------------------------------------------------
        # Symbol consistency
        # ----------------------------------------------------

        if not (
            data["symbol"] == symbol
        ).all():

            print(
                "❌ Symbol mapping incorrect"
            )

            failures.append(
                (
                    symbol,
                    "symbol mismatch"
                )
            )

            failed += 1

            continue

        print(
            "✓ Symbol mapping correct"
        )

        # ----------------------------------------------------
        # Quarter validation
        # ----------------------------------------------------

        if data["quarter"].isna().any():

            print(
                "❌ Missing quarter values"
            )

            failures.append(
                (
                    symbol,
                    "missing quarter"
                )
            )

            failed += 1

            continue

        print(
            "✓ Quarter values present"
        )

        # ----------------------------------------------------
        # Chronological order
        # ----------------------------------------------------

        if not data[
            "quarter"
        ].is_monotonic_increasing:

            print(
                "❌ Records not chronologically sorted"
            )

            failures.append(
                (
                    symbol,
                    "incorrect order"
                )
            )

            failed += 1

            continue

        print(
            "✓ Records sorted chronologically"
        )

        # ----------------------------------------------------
        # Duplicate quarter check
        # ----------------------------------------------------

        duplicate_quarters = (
            data["quarter"]
            .duplicated()
            .sum()
        )

        if duplicate_quarters > 0:

            print(
                f"❌ Duplicate quarters: "
                f"{duplicate_quarters}"
            )

            failures.append(
                (
                    symbol,
                    "duplicate quarters"
                )
            )

            failed += 1

            continue

        print(
            "✓ No duplicate quarters"
        )

        # ----------------------------------------------------
        # Numeric data check
        # ----------------------------------------------------

        numeric_columns = [
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]

        numeric_valid = True

        for column in numeric_columns:

            values = data[
                column
            ].dropna()

            converted = (
                values.astype(float)
            )

            if converted.isna().any():

                numeric_valid = False

                print(
                    f"❌ Invalid numeric values "
                    f"in {column}"
                )

                break

        if not numeric_valid:

            failures.append(
                (
                    symbol,
                    "invalid numeric data"
                )
            )

            failed += 1

            continue

        print(
            "✓ Financial numeric fields valid"
        )

        # ----------------------------------------------------
        # Handoff successful
        # ----------------------------------------------------

        print(
            f"✓ {symbol} handoff successful"
        )

        passed += 1

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "50-STOCK FINANCIAL SERVICE TEST SUMMARY"
    )

    print(
        "=========================================="
    )

    print(
        f"Stocks tested : {len(symbols)}"
    )

    print(
        f"Tests passed  : {passed}"
    )

    print(
        f"Tests failed  : {failed}"
    )

    # --------------------------------------------------------
    # Failure details
    # --------------------------------------------------------

    if failures:

        print(
            "\nFailures:"
        )

        for symbol, reason in failures:

            print(
                f"  ❌ {symbol}: {reason}"
            )

    print(
        "\n------------------------------------------"
    )

    if failed == 0:

        print(
            "🎉 50-STOCK FINANCIAL SERVICE TEST PASSED"
        )

        print(
            "Logic Engineer can consume financial "
            "data for the full stock universe."
        )

    else:

        print(
            "⚠ FINANCIAL SERVICE TEST REQUIRES REVIEW"
        )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()