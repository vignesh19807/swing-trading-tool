"""
Week 8 - Stop / Target Input Service Reliability Tests

Validates the standardized stop-loss and target inputs
provided to the Logic / Risk Engine.

This test suite verifies inputs only.
It does NOT validate BUY/SELL decisions.
"""

from backend.data_pipeline.stop_target_input_service import (
    get_stop_target_inputs,
    get_stop_target_inputs_for_stocks,
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
# TEST 1 - VALID CONTRACT
# ============================================================

def test_valid_contract(symbol):

    result = get_stop_target_inputs(
        symbol
    )

    required_fields = {
        "symbol",
        "timestamp",
        "current_price",
        "atr_14",
        "swing_high",
        "swing_low",
        "support_levels",
        "resistance_levels",
        "nearest_support",
        "nearest_resistance",
        "atr_multiplier",
        "atr_stop_distance",
        "atr_stop_reference",
        "risk_distance_to_support",
        "reward_distance_to_resistance",
        "data_quality",
        "missing_inputs",
        "decision",
        "source",
    }

    missing = (
        required_fields
        - set(result.keys())
    )

    assert not missing, (
        f"{symbol}: missing fields {missing}"
    )

    assert result["data_quality"] in {"VALID", "INCOMPLETE"}, (
        f"{symbol}: unexpected data quality {result['data_quality']}"
    )

    print(
        f"✓ {symbol}: stop/target contract valid"
    )


# ============================================================
# TEST 2 - ATR INPUTS
# ============================================================

def test_atr_inputs(symbol):

    result = get_stop_target_inputs(
        symbol
    )

    assert result["atr_14"] is not None
    assert result["atr_14"] > 0

    assert result[
        "atr_multiplier"
    ] > 0

    assert result[
        "atr_stop_distance"
    ] is not None

    assert result[
        "atr_stop_distance"
    ] > 0

    assert result[
        "atr_stop_reference"
    ] is not None

    expected_distance = (
        result["atr_14"]
        * result["atr_multiplier"]
    )

    assert abs(
        result["atr_stop_distance"]
        - expected_distance
    ) < 1e-9

    print(
        f"✓ {symbol}: ATR stop inputs valid"
    )


# ============================================================
# TEST 3 - SUPPORT / RESISTANCE
# ============================================================

def test_levels(symbol):

    result = get_stop_target_inputs(
        symbol
    )

    price = result[
        "current_price"
    ]

    support = result[
        "nearest_support"
    ]

    resistance = result[
        "nearest_resistance"
    ]

    assert price is not None

    # Support is optional when no valid support exists
    if support is not None:
        assert support["level"] < price
        assert result["risk_distance_to_support"] > 0
    else:
        assert "nearest_support" in result["missing_inputs"]
        assert result["risk_distance_to_support"] is None

    # Resistance is optional when no valid resistance exists
    if resistance is not None:
        assert resistance["level"] > price
        assert result["reward_distance_to_resistance"] > 0
    else:
        assert "nearest_resistance" in result["missing_inputs"]
        assert result["reward_distance_to_resistance"] is None

    print(
        f"✓ {symbol}: support/resistance inputs handled correctly"
    )


# ============================================================
# TEST 4 - RISK / REWARD INPUTS
# ============================================================

def test_risk_reward_inputs(symbol):

    result = get_stop_target_inputs(
        symbol
    )

    price = result["current_price"]
    support = result["nearest_support"]
    resistance = result["nearest_resistance"]

    assert price is not None

    if support is not None:

        expected_risk = price - support["level"]

        assert abs(
            result["risk_distance_to_support"]
            - expected_risk
        ) < 1e-9

    else:

        assert result["risk_distance_to_support"] is None

    if resistance is not None:

        expected_reward = resistance["level"] - price

        assert abs(
            result["reward_distance_to_resistance"]
            - expected_reward
        ) < 1e-9

    else:

        assert result["reward_distance_to_resistance"] is None

    print(
        f"✓ {symbol}: risk/reward inputs handled correctly"
    )


# ============================================================
# TEST 5 - NO TRADING DECISION
# ============================================================

def test_no_trading_decision(symbol):

    result = get_stop_target_inputs(
        symbol
    )

    assert result[
        "decision"
    ] is None

    print(
        f"✓ {symbol}: no BUY/SELL decision generated"
    )


# ============================================================
# TEST 6 - TIMESTAMP
# ============================================================

def test_timestamp(symbol):

    result = get_stop_target_inputs(
        symbol
    )

    timestamp = result[
        "timestamp"
    ]

    assert timestamp is not None
    assert "T" in timestamp

    print(
        f"✓ {symbol}: timestamp standardized"
    )


# ============================================================
# TEST 7 - INVALID SYMBOL
# ============================================================

def test_invalid_symbol():

    result = get_stop_target_inputs(
        "INVALID_SYMBOL"
    )

    assert result[
        "data_quality"
    ] in {
        "INVALID",
        "INCOMPLETE",
    }

    assert result[
        "current_price"
    ] is None

    assert result[
        "atr_14"
    ] is None

    assert result[
        "atr_stop_reference"
    ] is None

    assert result[
        "missing_inputs"
    ]

    assert result[
        "decision"
    ] is None

    print(
        "✓ Invalid symbol handled safely"
    )


# ============================================================
# TEST 8 - INVALID ATR MULTIPLIER
# ============================================================

def test_invalid_atr_multiplier():

    try:

        get_stop_target_inputs(
            "INFY",
            atr_multiplier=0,
        )

        raise AssertionError(
            "Zero ATR multiplier should fail"
        )

    except ValueError:

        pass

    try:

        get_stop_target_inputs(
            "INFY",
            atr_multiplier=-1,
        )

        raise AssertionError(
            "Negative ATR multiplier should fail"
        )

    except ValueError:

        pass

    try:

        get_stop_target_inputs(
            "INFY",
            atr_multiplier="1.5",
        )

        raise AssertionError(
            "String ATR multiplier should fail"
        )

    except TypeError:

        pass

    print(
        "✓ Invalid ATR multiplier handled safely"
    )


# ============================================================
# TEST 9 - MULTI-STOCK FAILURE ISOLATION
# ============================================================

def test_multi_stock_failure_isolation():

    stocks = [
        "INFY",
        "INVALID_SYMBOL",
        "TCS",
    ]

    results = get_stop_target_inputs_for_stocks(
        stocks
    )

    assert len(results) == 3

    infy = results[0]
    invalid = results[1]
    tcs = results[2]

    assert infy["symbol"] == "INFY"
    assert tcs["symbol"] == "TCS"

    assert infy[
        "data_quality"
    ] == "VALID"

    assert tcs[
        "data_quality"
    ] == "VALID"

    assert invalid[
        "symbol"
    ] == "INVALID_SYMBOL"

    assert invalid[
        "data_quality"
    ] in {
        "INVALID",
        "INCOMPLETE",
    }

    print(
        "✓ Multi-stock failure isolation passed"
    )


# ============================================================
# TEST 10 - FIVE-STOCK INTEGRATION
# ============================================================

def test_five_stock_integration():

    results = get_stop_target_inputs_for_stocks(
        TEST_STOCKS
    )

    assert len(results) == 5

    for result in results:

        assert result["current_price"] is not None
        assert result["atr_14"] is not None
        assert result["atr_stop_reference"] is not None
        assert result["decision"] is None

        if result["data_quality"] == "VALID":

            assert result["nearest_support"] is not None
            assert result["nearest_resistance"] is not None
            assert result["risk_distance_to_support"] > 0
            assert result["reward_distance_to_resistance"] > 0

        elif result["data_quality"] == "INCOMPLETE":

            assert result["missing_inputs"]

        else:

            raise AssertionError(
                f"Unexpected data quality: "
                f"{result['data_quality']}"
            )

    print(
        "✓ Five-stock stop/target integration handled successfully"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - STOP / TARGET INPUT RELIABILITY TEST")
    print("=" * 60)

    passed = 0
    failed = 0

    # --------------------------------------------------------
    # Per-stock tests
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
            lambda s=symbol:
                test_valid_contract(s),

            lambda s=symbol:
                test_atr_inputs(s),

            lambda s=symbol:
                test_levels(s),

            lambda s=symbol:
                test_risk_reward_inputs(s),

            lambda s=symbol:
                test_no_trading_decision(s),

            lambda s=symbol:
                test_timestamp(s),
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
    # General tests
    # --------------------------------------------------------

    tests = [
        (
            "Invalid symbol",
            test_invalid_symbol,
        ),
        (
            "Invalid ATR multiplier",
            test_invalid_atr_multiplier,
        ),
        (
            "Failure isolation",
            test_multi_stock_failure_isolation,
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
        "STOP / TARGET INPUT RELIABILITY SUMMARY"
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
            "\n🎉 WEEK 8 STOP / TARGET INPUT "
            "RELIABILITY TEST PASSED"
        )

    else:

        print(
            "\n⚠ STOP / TARGET INPUT SERVICE "
            "REQUIRES REVIEW"
        )

        raise SystemExit(1)

    print(
        "=" * 60
    )


if __name__ == "__main__":

    main()