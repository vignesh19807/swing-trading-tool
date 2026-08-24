"""
Week 9 - Failed Stock Retry Service

Purpose:
    Retry stocks recorded by the persistent failure-reporting service.

Flow:
    failed_stocks.json
        ↓
    load unresolved failures
        ↓
    retry stock processing
        ↓
    success -> mark resolved
    failure -> keep unresolved

This module does NOT:
    - generate BUY/SELL signals
    - make trading decisions
    - calculate financial scores
"""

from backend.data_pipeline.failure_report import (
    get_failed_stocks,
    record_failure,
    mark_resolved,
)

from backend.data_pipeline.technical_indicator_service import (
    save_technical_indicators,
)


def retry_technical_stock(symbol):
    """
    Retry technical-indicator processing for one stock.

    Returns:
        True  -> successful
        False -> failed
    """

    symbol = symbol.upper().strip()

    try:

        records = save_technical_indicators(
            symbol
        )

        if records <= 0:

            record_failure(
                symbol,
                "technical",
                "retry produced no records",
            )

            return False

        mark_resolved(
            symbol,
            "technical",
        )

        return True

    except Exception as error:

        record_failure(
            symbol,
            "technical",
            str(error),
        )

        return False


def retry_failed_stocks():
    """
    Retry all unresolved failed stocks.
    """

    failures = get_failed_stocks()

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 9 - FAILED STOCK RETRY SERVICE")
    print("=" * 60)

    print(
        f"\nUnresolved failures: {len(failures)}"
    )

    if not failures:

        print(
            "\n✓ No failed stocks require retry."
        )

        return True

    successful = 0
    failed = 0

    for failure in failures:

        symbol = failure.get("symbol")
        stage = failure.get("stage")

        print(
            "\n" + "-" * 60
        )

        print(
            f"Retrying {symbol}"
        )

        print(
            f"Stage: {stage}"
        )

        if stage != "technical":

            print(
                f"⚠ Unsupported retry stage: {stage}"
            )

            failed += 1
            continue

        if retry_technical_stock(symbol):

            successful += 1

            print(
                f"✓ {symbol} retry succeeded"
            )

        else:

            failed += 1

            print(
                f"❌ {symbol} retry failed"
            )

    print(
        "\n" + "=" * 60
    )

    print(
        "RETRY SUMMARY"
    )

    print(
        f"Attempted : {len(failures)}"
    )

    print(
        f"Successful: {successful}"
    )

    print(
        f"Failed    : {failed}"
    )

    print(
        "=" * 60
    )

    return failed == 0


def main():

    success = retry_failed_stocks()

    if success:

        print(
            "\n🎉 WEEK 9 FAILED STOCK RETRY PASSED"
        )

    else:

        print(
            "\n⚠ WEEK 9 FAILED STOCK RETRY REQUIRES REVIEW"
        )

    return success


if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)