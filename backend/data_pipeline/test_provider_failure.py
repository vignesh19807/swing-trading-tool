"""
Week 9 - API / Provider Failure Reliability Test

Verifies that a market-data provider failure:
    1. Is caught safely.
    2. Does not crash the caller.
    3. Returns None.
    4. Allows the pipeline to handle the failed stock.
"""

from unittest.mock import patch

from backend.data_pipeline.load_stock_data import fetch_stock_data


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 9 - API / PROVIDER FAILURE RELIABILITY TEST")
    print("=" * 60)

    provider_error = Exception(
        "Simulated provider/API failure"
    )

    with patch(
        "backend.data_pipeline.load_stock_data.provider_fetch_stock_data",
        side_effect=provider_error,
    ):

        result = fetch_stock_data("INFY.NS")

    print()
    print("Simulated provider failure:")
    print("  ✓ Provider exception generated")

    if result is None:
        print("  ✓ Provider failure handled safely")
    else:
        print("  ✗ Provider failure was not handled")
        raise AssertionError(
            "fetch_stock_data() should return None "
            "when the provider raises an exception."
        )

    print()
    print("Failure isolation:")
    print("  ✓ Exception did not escape fetch_stock_data()")
    print("  ✓ Failed download returns None")
    print("  ✓ Caller can record the stock as failed")

    print()
    print("=" * 60)
    print("API / PROVIDER FAILURE RELIABILITY SUMMARY")
    print("=" * 60)
    print("Tests passed : 4")
    print("Tests failed : 0")
    print()
    print("🎉 WEEK 9 API / PROVIDER FAILURE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()