"""
Week 5 - Unified Data Pipeline Runner

Orchestrates the existing Data Engineering pipeline.

Flow:
    Market Data Collection
            ↓
    Financial Data Collection
            ↓
    Consolidated Quality Audit

This module does NOT perform:
    - Technical scoring
    - Financial scoring
    - Trading decisions
"""

from backend.data_pipeline.load_stock_data import main as load_market_data
from backend.data_pipeline.insert_financial_data import (
    main as load_financial_data,
)
from backend.data_pipeline.consolidated_quality_report import (
    build_report,
    print_report,
)


def main():
    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 5 - UNIFIED DATA PIPELINE")
    print("=" * 60)

    # --------------------------------------------------------
    # STEP 1 — MARKET DATA
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("STEP 1/3 — MARKET DATA PIPELINE")
    print("=" * 60)

    try:
        load_market_data()
    except Exception as error:
        print("\n❌ Market data pipeline failed.")
        print(f"Error: {error}")
        return False

    # --------------------------------------------------------
    # STEP 2 — FINANCIAL DATA
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("STEP 2/3 — FINANCIAL DATA PIPELINE")
    print("=" * 60)

    try:
        load_financial_data()
    except Exception as error:
        print("\n❌ Financial data pipeline failed.")
        print(f"Error: {error}")
        return False

    # --------------------------------------------------------
    # STEP 3 — CONSOLIDATED QUALITY AUDIT
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("STEP 3/3 — CONSOLIDATED DATA QUALITY AUDIT")
    print("=" * 60)

    try:
        report = build_report()
        print_report(report)
    except Exception as error:
        print("\n❌ Consolidated quality audit failed.")
        print(f"Error: {error}")
        return False

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("WEEK 5 UNIFIED DATA PIPELINE COMPLETE")
    print("=" * 60)

    print("✓ Market data pipeline completed")
    print("✓ Financial data pipeline completed")
    print("✓ Consolidated quality audit completed")

    print("\n🎉 DATA PIPELINE AUTOMATION PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()

    if not success:
        raise SystemExit(1)