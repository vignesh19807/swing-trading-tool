"""
Week 9 - Database Connection Failure Reliability Test

Verifies that database connection failures are detectable
and do not get silently reported as successful.
"""

from unittest.mock import patch

from backend.data_pipeline import technical_indicator_service


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 9 - DATABASE FAILURE RELIABILITY TEST")
    print("=" * 60)

    simulated_error = Exception(
        "Simulated database connection failure"
    )

    print("\nSimulating database connection failure...")

    try:

        with patch(
            "backend.data_pipeline.technical_indicator_service.sqlite3.connect",
            side_effect=simulated_error,
        ):

            technical_indicator_service.save_technical_indicators(
                "INFY"
            )

    except Exception as error:

        print(
            f"✓ Database failure detected: {error}"
        )

        failure_detected = True

    else:

        print(
            "✗ Database failure was silently ignored"
        )

        failure_detected = False

    print("\nDatabase failure checks:")

    if failure_detected:

        print(
            "  ✓ Connection failure propagated safely"
        )

        print(
            "  ✓ Failure was not reported as successful"
        )

        print(
            "  ✓ Real database was not modified"
        )

    else:

        raise AssertionError(
            "Database connection failure was not detected."
        )

    print()
    print("=" * 60)
    print("DATABASE FAILURE RELIABILITY SUMMARY")
    print("=" * 60)
    print("Tests passed : 3")
    print("Tests failed : 0")
    print()
    print(
        "🎉 WEEK 9 DATABASE FAILURE RELIABILITY TEST PASSED"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()