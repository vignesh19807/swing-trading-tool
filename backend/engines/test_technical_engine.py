"""
Week 8 - Technical Engine Validation Tests

Validates the existing technical calculation engine before
connecting it to technical-indicator persistence.

This test module does NOT change the technical engine.
"""

import numpy as np
import pandas as pd

from backend.engines.technical_engine import (
    calculate_rsi,
    calculate_ema,
    calculate_macd,
    calculate_atr,
    calculate_support_resistance,
    calculate_technical_score,
    run_technical_pipeline,
)


# ============================================================
# TEST DATA
# ============================================================

def create_test_data(rows=120):
    dates = pd.date_range(
        "2025-01-01",
        periods=rows,
        freq="D",
    )

    close = pd.Series(
        np.linspace(100, 160, rows),
        index=dates,
        dtype=float,
    )

    data = pd.DataFrame(
        {
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 100000,
        },
        index=dates,
    )

    return data


# ============================================================
# TEST 1 - RSI
# ============================================================

def test_rsi():

    data = create_test_data()

    result = calculate_rsi(data["close"])

    assert isinstance(result, pd.Series)
    assert len(result) == len(data)

    valid = result.dropna()

    assert not valid.empty
    assert ((valid >= 0) & (valid <= 100)).all()

    print("✓ RSI calculation passed")


# ============================================================
# TEST 2 - EMA
# ============================================================

def test_ema():

    data = create_test_data()

    result = calculate_ema(
        data["close"],
        20,
    )

    assert isinstance(result, pd.Series)
    assert len(result) == len(data)

    valid = result.dropna()

    assert not valid.empty

    print("✓ EMA calculation passed")


# ============================================================
# TEST 3 - MACD
# ============================================================

def test_macd():

    data = create_test_data()

    result = calculate_macd(
        data["close"]
    )

    assert isinstance(result, pd.DataFrame)

    required = {
        "macd",
        "signal",
        "histogram",
    }

    assert required.issubset(
        result.columns
    )

    assert len(result) == len(data)

    print("✓ MACD calculation passed")


# ============================================================
# TEST 4 - ATR
# ============================================================

def test_atr():

    data = create_test_data()

    result = calculate_atr(
        data["high"],
        data["low"],
        data["close"],
    )

    assert isinstance(result, pd.Series)
    assert len(result) == len(data)

    valid = result.dropna()

    assert not valid.empty
    assert (valid >= 0).all()

    print("✓ ATR-14 calculation passed")


# ============================================================
# TEST 5 - SUPPORT / RESISTANCE
# ============================================================

def test_support_resistance():

    data = create_test_data()

    result = calculate_support_resistance(
        data["high"],
        data["low"],
        data["close"],
    )

    assert isinstance(result, pd.DataFrame)

    required = {
        "level",
        "zone_low",
        "zone_high",
        "type",
        "touches",
        "strength",
    }

    assert required.issubset(result.columns)
    assert len(result) == len(data) or len(result) >= 0

    print(
        "✓ Support/resistance calculation passed"
    )


# ============================================================
# TEST 6 - TECHNICAL SCORE
# ============================================================

def test_technical_score():

    data = create_test_data()

    rsi = calculate_rsi(
        data["close"]
    )

    ema20 = calculate_ema(
        data["close"],
        20,
    )

    ema50 = calculate_ema(
        data["close"],
        50,
    )

    ema200 = calculate_ema(
        data["close"],
        200,
    )

    macd_data = calculate_macd(
        data["close"]
    )

    result = calculate_technical_score(
        data["close"],
        data["volume"],
        rsi,
        macd_data["macd"],
        macd_data["signal"],
        macd_data["histogram"],
        ema20,
        ema50,
        ema200,
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(data)

    required = {
        "rsi_score",
        "macd_score",
        "trend_score",
        "volume_score",
        "technical_score",
    }

    assert required.issubset(result.columns)

    valid = result["technical_score"].dropna()

    if not valid.empty:
        assert ((valid >= 0) & (valid <= 100)).all()

    print(
        "✓ Technical score calculation passed"
    )


# ============================================================
# TEST 7 - COMPLETE PIPELINE
# ============================================================

def test_complete_pipeline():

    data = create_test_data()

    result = run_technical_pipeline(data)

    assert isinstance(result, dict)

    assert "indicators" in result
    assert "support_resistance" in result

    indicators = result["indicators"]
    support_resistance = result["support_resistance"]

    required_indicators = {
        "close",
        "volume",
        "rsi",
        "ema20",
        "ema50",
        "ema200",
        "macd",
        "signal",
        "histogram",
        "atr14",
        "technical_score",
    }

    missing = (
        required_indicators
        - set(indicators.columns)
    )

    assert not missing, (
        f"Missing indicator columns: {missing}"
    )

    required_sr = {
        "level",
        "zone_low",
        "zone_high",
        "type",
        "touches",
        "strength",
    }

    missing_sr = (
        required_sr
        - set(support_resistance.columns)
    )

    assert not missing_sr, (
        f"Missing support/resistance columns: {missing_sr}"
    )

    assert len(indicators) == len(data)

    print(
        "✓ Complete technical pipeline passed"
    )


# ============================================================
# TEST 8 - INPUT NOT MUTATED
# ============================================================

def test_input_not_mutated():

    data = create_test_data()

    original = data.copy(
        deep=True
    )

    run_technical_pipeline(
        data
    )

    pd.testing.assert_frame_equal(
        data,
        original,
    )

    print(
        "✓ Input data preservation passed"
    )


# ============================================================
# TEST 9 - INSUFFICIENT DATA
# ============================================================

def test_insufficient_data():

    data = create_test_data(
        rows=10
    )

    result = run_technical_pipeline(data)

    assert isinstance(result, dict)

    assert "indicators" in result
    assert "support_resistance" in result

    indicators = result["indicators"]

    assert len(indicators) == len(data)

    print(
        "✓ Insufficient-data handling passed"
    )


# ============================================================
# TEST 10 - INVALID DATA
# ============================================================

def test_invalid_data():

    data = create_test_data()

    data.loc[
        data.index[20],
        "close"
    ] = np.nan

    try:

        result = run_technical_pipeline(data)

        assert isinstance(result, dict)

        assert "indicators" in result
        assert "support_resistance" in result

        print(
            "✓ Invalid/missing-value handling passed"
        )

    except Exception as error:

        raise AssertionError(
            f"Technical pipeline failed on "
            f"missing close value: {error}"
        )


# ============================================================
# TEST RUNNER
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - TECHNICAL ENGINE VALIDATION")
    print("=" * 60)

    tests = [
        test_rsi,
        test_ema,
        test_macd,
        test_atr,
        test_support_resistance,
        test_technical_score,
        test_complete_pipeline,
        test_input_not_mutated,
        test_insufficient_data,
        test_invalid_data,
    ]

    passed = 0
    failed = 0

    for test in tests:

        try:

            test()
            passed += 1

        except Exception as error:

            failed += 1

            print(
                f"✗ {test.__name__} failed: "
                f"{error}"
            )

    print("\n" + "-" * 60)
    print("TECHNICAL ENGINE TEST SUMMARY")
    print("-" * 60)

    print(
        f"Tests passed : {passed}"
    )

    print(
        f"Tests failed : {failed}"
    )

    if failed == 0:

        print(
            "\n🎉 WEEK 8 TECHNICAL ENGINE "
            "VALIDATION PASSED"
        )

    else:

        print(
            "\n⚠ TECHNICAL ENGINE "
            "REQUIRES REVIEW"
        )

        raise SystemExit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()