"""
Week 8 - Entry / Exit Input Service Reliability Tests

Validates the standardized Data Engineer -> Logic/Risk Engine
input contract.
"""

from backend.data_pipeline.entry_exit_input_service import (
    get_entry_exit_inputs,
    get_entry_exit_inputs_for_stocks,
)


# ============================================================
# TEST STOCKS
# ============================================================

TEST_STOCKS = [
    "INFY",
    "HDFCBANK",
    "TCS",
    "SUNPHARMA",
    "RELIANCE",
]


# ============================================================
# REQUIRED CONTRACT FIELDS
# ============================================================

REQUIRED_FIELDS = {
    "symbol",
    "timestamp",
    "current_price",
    "recent_high",
    "recent_low",
    "swing_high",
    "swing_low",
    "atr_14",
    "support_levels",
    "resistance_levels",
    "data_quality",
    "missing_inputs",
    "source",
}


# ============================================================
# TEST 1 - VALID STOCK CONTRACT
# ============================================================

def test_valid_stock(symbol):

    result = get_entry_exit_inputs(
        symbol
    )

    missing_fields = (
        REQUIRED_FIELDS
        - set(result.keys())
    )

    assert not missing_fields, (
        f"{symbol}: missing contract fields "
        f"{missing_fields}"
    )

    assert result["data_quality"] == "VALID"

    assert result["current_price"] is not None
    assert result["recent_high"] is not None
    assert result["recent_low"] is not None
    assert result["swing_high"] is not None
    assert result["swing_low"] is not None
    assert result["atr_14"] is not None

    assert result["timestamp"]

    assert result["support_levels"]
    assert result["resistance_levels"]

    assert result["missing_inputs"] == []

    print(
        f"✓ {symbol}: valid input contract"
    )


# ============================================================
# TEST 2 - PRICE LOGIC
# ============================================================

def test_price_inputs(symbol):

    result = get_entry_exit_inputs(
        symbol
    )

    assert (
        result["recent_high"]
        >= result["recent_low"]
    )

    assert (
        result["current_price"] > 0
    )

    assert (
        result["atr_14"] > 0
    )

    print(
        f"✓ {symbol}: price/ATR inputs valid"
    )


# ============================================================
# TEST 3 - TIMESTAMP STANDARDIZATION
# ============================================================

def test_timestamp(symbol):

    result = get_entry_exit_inputs(
        symbol
    )

    timestamp = result["timestamp"]

    assert timestamp is not None

    assert "T" in timestamp

    print(
        f"✓ {symbol}: timestamp standardized"
    )


# ============================================================
# TEST 4 - SUPPORT / RESISTANCE CONTRACT
# ============================================================

def test_support_resistance(symbol):

    result = get_entry_exit_inputs(
        symbol
    )

    supports = result[
        "support_levels"
    ]

    resistances = result[
        "resistance_levels"
    ]

    assert supports
    assert resistances

    for level in supports:

        assert level["level"] is not None
        assert level["zone_low"] is not None
        assert level["zone_high"] is not None
        assert level["touches"] >= 1
        assert level["strength"] >= 1

        assert (
            level["zone_low"]
            <= level["level"]
            <= level["zone_high"]
        )

    for level in resistances:

        assert level["level"] is not None
        assert level["zone_low"] is not None
        assert level["zone_high"] is not None
        assert level["touches"] >= 1
        assert level["strength"] >= 1

        assert (
            level["zone_low"]
            <= level["level"]
            <= level["zone_high"]
        )

    print(
        f"✓ {symbol}: support/resistance inputs valid"
    )


# ============================================================
# TEST 5 - INVALID SYMBOL
# ============================================================

def test_invalid_symbol():

    result = get_entry_exit_inputs(
        "INVALID_SYMBOL"
    )

    assert result["data_quality"] in {
        "INVALID",
        "INCOMPLETE",
    }

    assert result["current_price"] is None
    assert result["atr_14"] is None

    assert result["missing_inputs"]

    print(
        "✓ Invalid symbol handled safely"
    )


# ============================================================
# TEST 6 - INVALID LOOKBACK
# ============================================================

def test_invalid_lookback():

    try:

        get_entry_exit_inputs(
            "INFY",
            lookback=0,
        )

        raise AssertionError(
            "lookback=0 should fail"
        )

    except ValueError:

        pass

    try:

        get_entry_exit_inputs(
            "INFY",
            lookback=-10,
        )

        raise AssertionError(
            "negative lookback should fail"
        )

    except ValueError:

        pass

    try:

        get_entry_exit_inputs(
            "INFY",
            lookback="120",
        )

        raise AssertionError(
            "string lookback should fail"
        )

    except TypeError:

        pass

    print(
        "✓ Invalid lookback handled safely"
    )


# ============================================================
# TEST 7 - NO ARBITRARY FALLBACK VALUES
# ============================================================

def test_no_arbitrary_fallback():

    result = get_entry_exit_inputs(
        "INVALID_SYMBOL"
    )

    assert result["current_price"] is None
    assert result["recent_high"] is None
    assert result["recent_low"] is None
    assert result["swing_high"] is None
    assert result["swing_low"] is None
    assert result["atr_14"] is None

    print(
        "✓ Missing inputs are not replaced with arbitrary values"
    )


# ============================================================
# TEST 8 - MULTI-STOCK FAILURE ISOLATION
# ============================================================

def test_multi_stock_failure_isolation():

    stocks = [
        "INFY",
        "INVALID_SYMBOL",
        "TCS",
    ]

    results = get_entry_exit_inputs_for_stocks(
        stocks
    )

    assert len(results) == 3

    valid_results = [
        result
        for result in results
        if result["symbol"]
        in {"INFY", "TCS"}
    ]

    invalid_results = [
        result
        for result in results
        if result["symbol"]
        == "INVALID_SYMBOL"
    ]

    assert len(valid_results) == 2
    assert len(invalid_results) == 1

    for result in valid_results:

        assert result[
            "data_quality"
        ] == "VALID"

    assert invalid_results[0][
        "data_quality"
    ] in {
        "INVALID",
        "INCOMPLETE",
    }

    print(
        "✓ Multi-stock failure isolation passed"
    )


# ============================================================
# TEST 9 - SOURCE DOCUMENTATION
# ============================================================

def test_source_documentation():

    result = get_entry_exit_inputs(
        "INFY"
    )

    source = result["source"]

    assert source["market_data"]
    assert source["technical_data"]
    assert source["atr"]
    assert source["support_resistance"]

    print(
        "✓ Input sources documented"
    )


# ============================================================
# TEST 10 - FIVE-STOCK INTEGRATION
# ============================================================

def test_five_stock_integration():

    results = get_entry_exit_inputs_for_stocks(
        TEST_STOCKS
    )

    assert len(results) == 5

    for result in results:

        assert result[
            "data_quality"
        ] == "VALID"

        assert result[
            "current_price"
        ] is not None

        assert result[
            "atr_14"
        ] is not None

        assert result[
            "support_levels"
        ]

        assert result[
            "resistance_levels"
        ]

    print(
        "✓ Five-stock integration passed"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - ENTRY / EXIT INPUT RELIABILITY TEST")
    print("=" * 60)

    passed = 0
    failed = 0

    # --------------------------------------------------------
    # Five-stock contract tests
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

        tests = [
            lambda s=symbol: test_valid_stock(s),
            lambda s=symbol: test_price_inputs(s),
            lambda s=symbol: test_timestamp(s),
            lambda s=symbol: test_support_resistance(s),
        ]

        for test in tests:

            try:

                test()
                passed += 1

            except Exception as error:

                failed += 1

                print(
                    f"✗ {symbol} test failed: "
                    f"{error}"
                )

    # --------------------------------------------------------
    # General reliability tests
    # --------------------------------------------------------

    tests = [
        (
            "Invalid symbol",
            test_invalid_symbol,
        ),
        (
            "Invalid lookback",
            test_invalid_lookback,
        ),
        (
            "No arbitrary fallback",
            test_no_arbitrary_fallback,
        ),
        (
            "Failure isolation",
            test_multi_stock_failure_isolation,
        ),
        (
            "Source documentation",
            test_source_documentation,
        ),
        (
            "Five-stock integration",
            test_five_stock_integration,
        ),
    ]

    for name, test in tests:

        try:

            test()
            passed += 1

        except Exception as error:

            failed += 1

            print(
                f"✗ {name} failed: {error}"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "ENTRY / EXIT INPUT RELIABILITY SUMMARY"
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

    if failed == 0:

        print(
            "\n🎉 WEEK 8 ENTRY / EXIT INPUT "
            "RELIABILITY TEST PASSED"
        )

    else:

        print(
            "\n⚠ ENTRY / EXIT INPUT SERVICE "
            "REQUIRES REVIEW"
        )

        raise SystemExit(1)

    print(
        "=" * 60
    )


if __name__ == "__main__":

    main()