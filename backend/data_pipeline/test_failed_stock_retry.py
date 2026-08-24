"""
Week 9 - Failed Stock Retry Reliability Test

Verifies that:

1. A failed stock can be recorded.
2. The retry service detects the failure.
3. The retry succeeds.
4. The failure is marked resolved.
5. No unresolved failures remain.

The test uses a controlled temporary failure record and
does not intentionally modify trading decisions or signals.
"""

from backend.data_pipeline.failure_report import (
    load_failures,
    save_failures,
    record_failure,
    get_failed_stocks,
)

from backend.data_pipeline.retry_failed_stocks import (
    retry_failed_stocks,
)


TEST_SYMBOL = "TCS"
TEST_STAGE = "technical"
TEST_REASON = "Test retry failure"


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 9 - FAILED STOCK RETRY RELIABILITY TEST")
    print("=" * 60)

    original_failures = load_failures()

    try:

        # ----------------------------------------------------
        # STEP 1 — Create controlled failure
        # ----------------------------------------------------

        print("\nStep 1 — Recording test failure...")

        record_failure(
            TEST_SYMBOL,
            TEST_STAGE,
            TEST_REASON,
        )

        failures = get_failed_stocks()

        test_failure_exists = any(
            failure.get("symbol") == TEST_SYMBOL
            and failure.get("stage") == TEST_STAGE
            for failure in failures
        )

        if test_failure_exists:

            print(
                "  ✓ Test failure recorded"
            )

        else:

            print(
                "  ❌ Test failure was not recorded"
            )

            raise AssertionError(
                "Test failure was not recorded"
            )

        # ----------------------------------------------------
        # STEP 2 — Retry
        # ----------------------------------------------------

        print(
            "\nStep 2 — Running failed-stock retry..."
        )

        retry_success = retry_failed_stocks()

        if retry_success:

            print(
                "  ✓ Retry service completed successfully"
            )

        else:

            print(
                "  ❌ Retry service reported failure"
            )

            raise AssertionError(
                "Retry service failed"
            )

        # ----------------------------------------------------
        # STEP 3 — Verify resolution
        # ----------------------------------------------------

        print(
            "\nStep 3 — Verifying failure resolution..."
        )

        remaining = get_failed_stocks()

        unresolved_test_failure = any(
            failure.get("symbol") == TEST_SYMBOL
            and failure.get("stage") == TEST_STAGE
            for failure in remaining
        )

        if not unresolved_test_failure:

            print(
                "  ✓ Test failure was resolved"
            )

        else:

            print(
                "  ❌ Test failure remains unresolved"
            )

            raise AssertionError(
                "Test failure was not resolved"
            )

        print(
            "\n" + "=" * 60
        )

        print(
            "FAILED STOCK RETRY RELIABILITY SUMMARY"
        )

        print(
            "Tests passed : 3"
        )

        print(
            "Tests failed : 0"
        )

        print(
            "\n🎉 WEEK 9 FAILED STOCK RETRY TEST PASSED"
        )

        print(
            "=" * 60
        )

    finally:

        # ----------------------------------------------------
        # Restore original failure state
        # ----------------------------------------------------

        save_failures(
            original_failures
        )


if __name__ == "__main__":

    main()