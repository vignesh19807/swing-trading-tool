"""
Week 6 - Pipeline Reliability Test

Tests whether a single stock failure is isolated
without stopping the remaining stocks.
"""


def process_stock(symbol, failing_symbol=None):
    """
    Simulate processing one stock.

    A failure is intentionally generated for the
    configured failing symbol.
    """

    print(f"Processing {symbol}...")

    if symbol == failing_symbol:
        raise RuntimeError(
            f"Simulated provider failure for {symbol}"
        )

    print(f"✓ {symbol} processed successfully")
    return True


def run_reliability_test():

    stocks = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    failing_symbol = "WIPRO"

    successful = []
    failed = []

    print("=" * 50)
    print("WEEK 6 - PIPELINE RELIABILITY TEST")
    print("=" * 50)

    for symbol in stocks:

        try:

            process_stock(
                symbol,
                failing_symbol
            )

            successful.append(symbol)

        except Exception as error:

            print(
                f"⚠ {symbol} failed: {error}"
            )

            failed.append(symbol)

            # Important:
            # Continue processing remaining stocks.
            continue

    print("\n" + "-" * 50)
    print("RELIABILITY TEST SUMMARY")
    print("-" * 50)

    print(
        f"Stocks tested : {len(stocks)}"
    )

    print(
        f"Successful    : {len(successful)}"
    )

    print(
        f"Failed        : {len(failed)}"
    )

    print(
        f"Successful stocks: {successful}"
    )

    print(
        f"Failed stocks    : {failed}"
    )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    assert "WIPRO" in failed
    assert "INFY" in successful
    assert "TCS" in successful
    assert "RELIANCE" in successful
    assert "HDFCBANK" in successful

    assert len(successful) == 4
    assert len(failed) == 1

    print("\n✓ Failure isolation passed")
    print("✓ Failed stock did not stop remaining stocks")
    print("✓ Pipeline continued successfully")
    print("\n🎉 WEEK 6 RELIABILITY TEST PASSED")
    print("=" * 50)


if __name__ == "__main__":
    run_reliability_test()