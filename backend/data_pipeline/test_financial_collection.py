"""
Week 3 Financial Collection Test
=================================

Tests financial collection and validation
on five representative NSE stocks.

No database insertion is performed.
"""

from backend.data_pipeline.financial_data import (
    fetch_financial_data,
)

from backend.data_pipeline.financial_validator import (
    validate_financial_data,
)


TEST_STOCKS = [
    "INFY",
    "TCS",
    "RELIANCE",
    "WIPRO",
    "HDFCBANK",
]


def main():

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("5-STOCK FINANCIAL DATA TEST")
    print("==========================================")

    successful = 0
    failed = 0

    for symbol in TEST_STOCKS:

        print("\n------------------------------------------")
        print(f"Testing {symbol}")
        print("------------------------------------------")

        data = fetch_financial_data(symbol)

        if data is None:

            print(f"❌ {symbol}: Collection failed")
            failed += 1
            continue

        valid, report = validate_financial_data(
            symbol,
            data
        )

        print(
            f"Records returned: {len(data)}"
        )

        print(
            f"Missing values: "
            f"{sum(report['missing_values'].values())}"
        )

        print(
            f"Duplicate records: "
            f"{report['duplicate_records']}"
        )

        print(
            f"Invalid periods: "
            f"{report['invalid_periods']}"
        )

        print(
            f"Errors: "
            f"{len(report['errors'])}"
        )

        if valid:

            print(
                f"✓ {symbol}: STRUCTURE VALID"
            )

            successful += 1

        else:

            print(
                f"❌ {symbol}: REQUIRES REVIEW"
            )

            failed += 1

    print("\n==========================================")
    print("5-STOCK FINANCIAL TEST SUMMARY")
    print("==========================================")

    print(
        f"Stocks tested : {len(TEST_STOCKS)}"
    )

    print(
        f"Successful    : {successful}"
    )

    print(
        f"Failed        : {failed}"
    )

    print("------------------------------------------")

    if failed == 0:

        print(
            "🎉 5-STOCK FINANCIAL COLLECTION PASSED"
        )

    else:

        print(
            "⚠ SOME STOCKS REQUIRE REVIEW"
        )

    print("==========================================")


if __name__ == "__main__":

    main()