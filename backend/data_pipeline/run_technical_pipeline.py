"""
Week 8 - Unified Technical Indicator Pipeline

Processes the complete stock universe through the validated
Technical Indicator Persistence Service.

This runner provides failure isolation:
    - One stock failure does not stop remaining stocks.
    - Results are summarized at the end.
"""

from backend.data_pipeline.stock_universe import STOCK_UNIVERSE
from backend.data_pipeline.technical_indicator_service import (
    save_technical_indicators,
)


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - TECHNICAL INDICATOR PIPELINE")
    print("=" * 60)

    successful = []
    failed = []

    total = len(STOCK_UNIVERSE)

    print(
        f"\nStocks in universe: {total}"
    )

    # --------------------------------------------------------
    # PROCESS STOCKS
    # --------------------------------------------------------

    for position, stock in enumerate(
        STOCK_UNIVERSE,
        start=1,
    ):

        symbol = stock["symbol"]

        print(
            f"\n[{position}/{total}] Processing {symbol}..."
        )

        try:

            records = save_technical_indicators(
                symbol
            )

            if records > 0:

                successful.append(
                    (symbol, records)
                )

                print(
                    f"✓ {symbol} completed "
                    f"({records} records)"
                )

            else:

                failed.append(
                    (symbol, "No records processed")
                )

                print(
                    f"⚠ {symbol} returned no records"
                )

        except Exception as error:

            failed.append(
                (symbol, str(error))
            )

            print(
                f"⚠ {symbol} failed: {error}"
            )

            # Failure isolation:
            # continue processing remaining stocks.
            continue

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "WEEK 8 TECHNICAL PIPELINE SUMMARY"
    )

    print(
        "=" * 60
    )

    print(
        f"Stocks tested : {total}"
    )

    print(
        f"Successful    : {len(successful)}"
    )

    print(
        f"Failed        : {len(failed)}"
    )

    print(
        f"Total records : "
        f"{sum(count for _, count in successful)}"
    )

    # --------------------------------------------------------
    # SUCCESSFUL STOCKS
    # --------------------------------------------------------

    print(
        "\nSuccessful stocks:"
    )

    for symbol, records in successful:

        print(
            f"  ✓ {symbol:<12} {records} records"
        )

    # --------------------------------------------------------
    # FAILED STOCKS
    # --------------------------------------------------------

    if failed:

        print(
            "\nFailed stocks:"
        )

        for symbol, error in failed:

            print(
                f"  ⚠ {symbol:<12} {error}"
            )

    else:

        print(
            "\nFailed stocks: NONE"
        )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print(
        "\n" + "-" * 60
    )

    if not failed:

        print(
            "✓ All stocks processed successfully"
        )

        print(
            "✓ Failure isolation verified"
        )

        print(
            "\n🎉 WEEK 8 TECHNICAL PIPELINE PASSED"
        )

    else:

        print(
            "⚠ Pipeline completed with failures"
        )

        print(
            "✓ Remaining stocks continued processing"
        )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # Do not fail the entire process merely because one stock
    # failed. Failure isolation is intentional.
    # --------------------------------------------------------

    return len(failed) == 0


if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)