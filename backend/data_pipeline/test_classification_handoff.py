"""
Week 7 - Classification Data → Logic Handoff Test

Purpose:
    Verify that the Logic Engineering layer can consume
    sector and industry data through classification_service.

This test does NOT:
    - access SQLite directly from the test logic
    - calculate scores
    - rank stocks
    - make trading decisions
"""

from backend.data_pipeline.classification_service import (
    get_company_classification,
    get_sector_stocks,
    get_industry_stocks,
    get_all_classifications,
)


# ============================================================
# TEST STOCKS
# ============================================================

TEST_STOCKS = [
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "RELIANCE",
    "TCS",
]


# ============================================================
# TEST COMPANY CLASSIFICATION
# ============================================================

def test_company_classification():

    print("\n" + "-" * 50)
    print("TEST 1 - COMPANY CLASSIFICATION")
    print("-" * 50)

    passed = 0
    failed = 0

    for symbol in TEST_STOCKS:

        print(f"Testing {symbol}...")

        result = get_company_classification(
            symbol
        )

        if result is None:

            print(
                f"❌ {symbol}: classification not found"
            )

            failed += 1
            continue

        required_fields = [
            "symbol",
            "company_name",
            "sector",
            "industry",
        ]

        missing = [
            field
            for field in required_fields
            if not result.get(field)
        ]

        if missing:

            print(
                f"❌ {symbol}: missing {missing}"
            )

            failed += 1
            continue

        if result["symbol"] != symbol:

            print(
                f"❌ {symbol}: symbol mismatch"
            )

            failed += 1
            continue

        print(
            f"✓ {symbol}: "
            f"{result['sector']} → "
            f"{result['industry']}"
        )

        passed += 1

    return passed, failed


# ============================================================
# TEST SECTOR LOOKUP
# ============================================================

def test_sector_lookup():

    print("\n" + "-" * 50)
    print("TEST 2 - SECTOR STOCK LOOKUP")
    print("-" * 50)

    sector = "Information Technology"

    stocks = get_sector_stocks(
        sector
    )

    expected = {
        "HCLTECH",
        "INFY",
        "TCS",
        "TECHM",
        "WIPRO",
    }

    actual = set(stocks)

    print(
        f"Sector: {sector}"
    )

    print(
        f"Stocks returned: {len(stocks)}"
    )

    print(
        f"Stocks: {stocks}"
    )

    if actual == expected:

        print(
            "✓ Sector lookup passed"
        )

        return 1, 0

    print(
        "❌ Sector lookup failed"
    )

    print(
        f"Expected: {sorted(expected)}"
    )

    print(
        f"Actual:   {sorted(actual)}"
    )

    return 0, 1


# ============================================================
# TEST INDUSTRY LOOKUP
# ============================================================

def test_industry_lookup():

    print("\n" + "-" * 50)
    print("TEST 3 - INDUSTRY STOCK LOOKUP")
    print("-" * 50)

    industry = "IT Services"

    stocks = get_industry_stocks(
        industry
    )

    expected = {
        "HCLTECH",
        "INFY",
        "TCS",
        "TECHM",
        "WIPRO",
    }

    actual = set(stocks)

    print(
        f"Industry: {industry}"
    )

    print(
        f"Stocks returned: {len(stocks)}"
    )

    print(
        f"Stocks: {stocks}"
    )

    if actual == expected:

        print(
            "✓ Industry lookup passed"
        )

        return 1, 0

    print(
        "❌ Industry lookup failed"
    )

    print(
        f"Expected: {sorted(expected)}"
    )

    print(
        f"Actual:   {sorted(actual)}"
    )

    return 0, 1


# ============================================================
# TEST COMPLETE CLASSIFICATION DATA
# ============================================================

def test_all_classifications():

    print("\n" + "-" * 50)
    print("TEST 4 - COMPLETE CLASSIFICATION DATA")
    print("-" * 50)

    data = get_all_classifications()

    expected_columns = [
        "symbol",
        "company_name",
        "sector",
        "industry",
    ]

    if list(data.columns) != expected_columns:

        print(
            "❌ Column structure mismatch"
        )

        print(
            f"Expected: {expected_columns}"
        )

        print(
            f"Actual:   {data.columns.tolist()}"
        )

        return 0, 1

    if len(data) != 50:

        print(
            f"❌ Expected 100 companies, "
            f"received {len(data)}"
        )

        return 0, 1

    missing = data[
        data[
            [
                "symbol",
                "company_name",
                "sector",
                "industry",
            ]
        ].isnull().any(axis=1)
    ]

    if not missing.empty:

        print(
            "❌ Missing classification values"
        )

        print(
            missing.to_string(
                index=False
            )
        )

        return 0, 1

    print(
        "✓ 50 companies returned"
    )

    print(
        "✓ Required columns present"
    )

    print(
        "✓ No missing classification values"
    )

    return 1, 0


# ============================================================
# TEST INVALID SYMBOL
# ============================================================

def test_invalid_symbol():

    print("\n" + "-" * 50)
    print("TEST 5 - INVALID SYMBOL")
    print("-" * 50)

    result = get_company_classification(
        "INVALID_SYMBOL"
    )

    if result is None:

        print(
            "✓ Invalid symbol handled safely"
        )

        return 1, 0

    print(
        "❌ Invalid symbol returned data"
    )

    return 0, 1


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 50)
    print("SWING TRADING PLATFORM")
    print("WEEK 7 - CLASSIFICATION DATA → LOGIC HANDOFF")
    print("=" * 50)

    total_passed = 0
    total_failed = 0

    # --------------------------------------------------------
    # Test 1
    # --------------------------------------------------------

    passed, failed = (
        test_company_classification()
    )

    total_passed += passed
    total_failed += failed

    # --------------------------------------------------------
    # Test 2
    # --------------------------------------------------------

    passed, failed = (
        test_sector_lookup()
    )

    total_passed += passed
    total_failed += failed

    # --------------------------------------------------------
    # Test 3
    # --------------------------------------------------------

    passed, failed = (
        test_industry_lookup()
    )

    total_passed += passed
    total_failed += failed

    # --------------------------------------------------------
    # Test 4
    # --------------------------------------------------------

    passed, failed = (
        test_all_classifications()
    )

    total_passed += passed
    total_failed += failed

    # --------------------------------------------------------
    # Test 5
    # --------------------------------------------------------

    passed, failed = (
        test_invalid_symbol()
    )

    total_passed += passed
    total_failed += failed

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 50)
    print("CLASSIFICATION HANDOFF SUMMARY")
    print("=" * 50)

    print(
        f"Tests passed : {total_passed}"
    )

    print(
        f"Tests failed : {total_failed}"
    )

    print("-" * 50)

    if total_failed == 0:

        print(
            "🎉 CLASSIFICATION DATA → LOGIC HANDOFF PASSED"
        )

        print(
            "Logic Engineer can consume sector and "
            "industry data through Classification Service."
        )

        print("=" * 50)

        return True

    print(
        "❌ CLASSIFICATION DATA → LOGIC HANDOFF FAILED"
    )

    print(
        "Review the failed tests before continuing."
    )

    print("=" * 50)

    return False


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)