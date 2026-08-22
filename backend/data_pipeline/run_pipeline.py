"""
Week 6 - Reliable Unified Data Pipeline Runner

Orchestrates the complete Data Engineering pipeline.

Flow:
    1. Market Data Collection
    2. Financial Data Collection
    3. Consolidated Quality Audit

Week 6 improvements:
    - Explicit stage status tracking
    - Clear failure reporting
    - Safe stage execution
    - Final overall PASS/FAIL status

This module does NOT perform:
    - Technical scoring
    - Financial scoring
    - Trading decisions
"""

from backend.data_pipeline.load_stock_data import (
    main as load_market_data,
)

from backend.data_pipeline.insert_financial_data import (
    main as load_financial_data,
)

from backend.data_pipeline.consolidated_quality_report import (
    build_report,
    print_report,
)


def run_stage(stage_name, stage_function):
    """
    Execute one pipeline stage safely.

    Returns:
        True  -> stage completed successfully
        False -> stage failed
    """

    print("\n" + "=" * 60)
    print(stage_name)
    print("=" * 60)

    try:

        result = stage_function()

        # Existing loaders may return None even when successful.
        # Completion without an exception is considered success.
        print(
            f"\n✓ {stage_name} completed successfully"
        )

        return True

    except Exception as error:

        print(
            f"\n❌ {stage_name} FAILED"
        )

        print(
            f"Error: {error}"
        )

        return False


def run_audit():
    """
    Run the consolidated data-quality audit safely.

    Returns:
        True  -> audit completed
        False -> audit failed
    """

    try:

        report = build_report()

        print_report(report)

        return True

    except Exception as error:

        print(
            "\n❌ Consolidated Quality Audit FAILED"
        )

        print(
            f"Error: {error}"
        )

        return False


def print_execution_summary(statuses):
    """
    Print the final Week 6 pipeline execution summary.
    """

    print("\n" + "=" * 60)
    print("WEEK 6 PIPELINE EXECUTION SUMMARY")
    print("=" * 60)

    print(
        f"{'Stage':<35} Status"
    )

    print("-" * 60)

    for stage, status in statuses.items():

        if status == "PASSED":

            symbol = "✓"

        elif status == "FAILED":

            symbol = "❌"

        else:

            symbol = "⏭"

        print(
            f"{stage:<35} {symbol} {status}"
        )

    print("-" * 60)


def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 6 - RELIABLE UNIFIED DATA PIPELINE")
    print("=" * 60)

    statuses = {
        "Market Data Pipeline": "PENDING",
        "Financial Data Pipeline": "PENDING",
        "Consolidated Quality Audit": "PENDING",
    }

    # ========================================================
    # STEP 1 — MARKET DATA
    # ========================================================

    market_success = run_stage(
        "STEP 1/3 — MARKET DATA PIPELINE",
        load_market_data,
    )

    if market_success:

        statuses[
            "Market Data Pipeline"
        ] = "PASSED"

    else:

        statuses[
            "Market Data Pipeline"
        ] = "FAILED"

        # Market data is required before the remaining
        # pipeline stages can be considered reliable.
        statuses[
            "Financial Data Pipeline"
        ] = "SKIPPED"

        statuses[
            "Consolidated Quality Audit"
        ] = "SKIPPED"

        print_execution_summary(statuses)

        print(
            "\n❌ WEEK 6 DATA PIPELINE FAILED"
        )

        return False

    # ========================================================
    # STEP 2 — FINANCIAL DATA
    # ========================================================

    financial_success = run_stage(
        "STEP 2/3 — FINANCIAL DATA PIPELINE",
        load_financial_data,
    )

    if financial_success:

        statuses[
            "Financial Data Pipeline"
        ] = "PASSED"

    else:

        statuses[
            "Financial Data Pipeline"
        ] = "FAILED"

        statuses[
            "Consolidated Quality Audit"
        ] = "SKIPPED"

        print_execution_summary(statuses)

        print(
            "\n❌ WEEK 6 DATA PIPELINE FAILED"
        )

        return False

    # ========================================================
    # STEP 3 — CONSOLIDATED QUALITY AUDIT
    # ========================================================

    print("\n" + "=" * 60)
    print("STEP 3/3 — CONSOLIDATED DATA QUALITY AUDIT")
    print("=" * 60)

    audit_success = run_audit()

    if audit_success:

        statuses[
            "Consolidated Quality Audit"
        ] = "PASSED"

    else:

        statuses[
            "Consolidated Quality Audit"
        ] = "FAILED"

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print_execution_summary(statuses)

    overall_success = all(
        status == "PASSED"
        for status in statuses.values()
    )

    if overall_success:

        print(
            "\n✓ Overall Status: PASSED"
        )

        print(
            "\n🎉 WEEK 6 DATA PIPELINE AUTOMATION PASSED"
        )

        print("=" * 60)

        return True

    print(
        "\n❌ Overall Status: FAILED"
    )

    print(
        "\n⚠ WEEK 6 DATA PIPELINE REQUIRES REVIEW"
    )

    print("=" * 60)

    return False


if __name__ == "__main__":

    success = main()

    if not success:

        raise SystemExit(1)