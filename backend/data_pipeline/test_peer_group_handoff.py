"""
Week 7 - Peer Group Data → Logic Handoff Test

Purpose:
    Verify that the Logic Engineering layer can consume
    sector and industry peer groups through peer_group_service.

This test does NOT:
    - access SQLite directly
    - calculate scores
    - rank stocks
    - make trading decisions
"""

from backend.data_pipeline.peer_group_service import (
    get_company_classification,
    get_sector_peers,
    get_industry_peers,
    get_peer_group,
    get_sector_summary,
    get_industry_summary,
)


# ============================================================
# TEST STOCKS
# ============================================================

TEST_STOCKS = [
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "RELIANCE",
    "TCS",
]


# ============================================================
# TEST 1 - COMPANY CLASSIFICATION
# ============================================================

def test_company_classification():

    print("\n" + "-" * 50)
    print("TEST 1 - COMPANY CLASSIFICATION")
    print("-" * 50)

    passed = 0
    failed = 0

    for symbol in TEST_STOCKS:

        print(f"Testing {symbol}...")

        result = get_company_classification(symbol)

        if result is None:
            print(f"❌ {symbol}: classification not found")
            failed += 1
            continue

        if (
            not result.get("symbol")
            or not result.get("sector")
            or not result.get("industry")
        ):
            print(f"❌ {symbol}: incomplete classification")
            failed += 1
            continue

        print(
            f"✓ {symbol}: "
            f"{result['sector']} → "
            f"{result['industry']}"
        )

        passed += 1

    return passed, failed


# ============================================================
# TEST 2 - SECTOR PEER CONSISTENCY
# ============================================================

def test_sector_peers():

    print("\n" + "-" * 50)
    print("TEST 2 - SECTOR PEER CONSISTENCY")
    print("-" * 50)

    passed = 0
    failed = 0

    for symbol in TEST_STOCKS:

        classification = get_company_classification(symbol)
        peers = get_sector_peers(symbol)

        if classification is None:
            print(f"❌ {symbol}: classification unavailable")
            failed += 1
            continue

        if not peers:
            print(f"❌ {symbol}: no sector peers returned")
            failed += 1
            continue

        if symbol not in peers:
            print(f"❌ {symbol}: stock missing from sector peers")
            failed += 1
            continue

        # Verify every peer belongs to the same sector.
        valid = True

        for peer in peers:

            peer_classification = (
                get_company_classification(peer)
            )

            if peer_classification is None:
                valid = False
                break

            if (
                peer_classification["sector"]
                != classification["sector"]
            ):
                valid = False
                break

        if not valid:
            print(
                f"❌ {symbol}: sector peer mismatch"
            )
            failed += 1
            continue

        print(
            f"✓ {symbol}: "
            f"{len(peers)} sector peers"
        )

        passed += 1

    return passed, failed


# ============================================================
# TEST 3 - INDUSTRY PEER CONSISTENCY
# ============================================================

def test_industry_peers():

    print("\n" + "-" * 50)
    print("TEST 3 - INDUSTRY PEER CONSISTENCY")
    print("-" * 50)

    passed = 0
    failed = 0

    for symbol in TEST_STOCKS:

        classification = get_company_classification(symbol)
        peers = get_industry_peers(symbol)

        if classification is None:
            print(f"❌ {symbol}: classification unavailable")
            failed += 1
            continue

        if not peers:
            print(f"❌ {symbol}: no industry peers returned")
            failed += 1
            continue

        if symbol not in peers:
            print(
                f"❌ {symbol}: "
                f"stock missing from industry peers"
            )
            failed += 1
            continue

        valid = True

        for peer in peers:

            peer_classification = (
                get_company_classification(peer)
            )

            if peer_classification is None:
                valid = False
                break

            if (
                peer_classification["industry"]
                != classification["industry"]
            ):
                valid = False
                break

        if not valid:
            print(
                f"❌ {symbol}: industry peer mismatch"
            )
            failed += 1
            continue

        print(
            f"✓ {symbol}: "
            f"{len(peers)} industry peers"
        )

        passed += 1

    return passed, failed


# ============================================================
# TEST 4 - COMPLETE PEER GROUP
# ============================================================

def test_complete_peer_group():

    print("\n" + "-" * 50)
    print("TEST 4 - COMPLETE PEER GROUP")
    print("-" * 50)

    passed = 0
    failed = 0

    required_fields = [
        "symbol",
        "sector",
        "industry",
        "sector_peers",
        "industry_peers",
    ]

    for symbol in TEST_STOCKS:

        result = get_peer_group(symbol)

        if result is None:
            print(
                f"❌ {symbol}: peer group not found"
            )
            failed += 1
            continue

        missing = [
            field
            for field in required_fields
            if field not in result
        ]

        if missing:
            print(
                f"❌ {symbol}: missing fields {missing}"
            )
            failed += 1
            continue

        if symbol not in result["sector_peers"]:
            print(
                f"❌ {symbol}: missing from sector peers"
            )
            failed += 1
            continue

        if symbol not in result["industry_peers"]:
            print(
                f"❌ {symbol}: missing from industry peers"
            )
            failed += 1
            continue

        print(
            f"✓ {symbol}: complete peer group"
        )

        passed += 1

    return passed, failed


# ============================================================
# TEST 5 - SUMMARY COVERAGE
# ============================================================

def test_summary_coverage():

    print("\n" + "-" * 50)
    print("TEST 5 - SUMMARY COVERAGE")
    print("-" * 50)

    passed = 0
    failed = 0

    sector_summary = get_sector_summary()
    industry_summary = get_industry_summary()

    # There should be exactly 16 sector rows.
    if len(sector_summary) != 16:
        print(
            f"❌ Expected 16 sectors, "
            f"received {len(sector_summary)}"
        )
        failed += 1
    else:
        print("✓ 16 sectors available")
        passed += 1

    # There should be exactly 32 industry-sector rows.
    if len(industry_summary) != 32:
        print(
            f"❌ Expected 32 industry mappings, "
            f"received {len(industry_summary)}"
        )
        failed += 1
    else:
        print("✓ 32 industry mappings available")
        passed += 1

    # Total sector stock counts should equal 50.
    sector_total = int(
        sector_summary["stock_count"].sum()
    )

    if sector_total != 100:
        print(
            f"❌ Sector summary total is {sector_total}, "
            f"expected 50"
        )
        failed += 1
    else:
        print("✓ Sector summary covers all 50 companies")
        passed += 1

    # Total industry mapping counts should equal 50.
    industry_total = int(
        industry_summary["stock_count"].sum()
    )

    if industry_total != 50:
        print(
            f"❌ Industry summary total is {industry_total}, "
            f"expected 50"
        )
        failed += 1
    else:
        print("✓ Industry summary covers all 50 companies")
        passed += 1

    return passed, failed


# ============================================================
# TEST 6 - INVALID SYMBOL
# ============================================================

def test_invalid_symbol():

    print("\n" + "-" * 50)
    print("TEST 6 - INVALID SYMBOL")
    print("-" * 50)

    sector_peers = get_sector_peers(
        "INVALID_SYMBOL"
    )

    industry_peers = get_industry_peers(
        "INVALID_SYMBOL"
    )

    peer_group = get_peer_group(
        "INVALID_SYMBOL"
    )

    if sector_peers != []:
        print(
            "❌ Invalid symbol returned sector peers"
        )
        return 0, 1

    if industry_peers != []:
        print(
            "❌ Invalid symbol returned industry peers"
        )
        return 0, 1

    if peer_group is not None:
        print(
            "❌ Invalid symbol returned peer group"
        )
        return 0, 1

    print(
        "✓ Invalid symbol handled safely"
    )

    return 1, 0


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 50)
    print("SWING TRADING PLATFORM")
    print("WEEK 7 - PEER GROUP DATA → LOGIC HANDOFF")
    print("=" * 50)

    total_passed = 0
    total_failed = 0

    tests = [
        test_company_classification,
        test_sector_peers,
        test_industry_peers,
        test_complete_peer_group,
        test_summary_coverage,
        test_invalid_symbol,
    ]

    for test in tests:

        passed, failed = test()

        total_passed += passed
        total_failed += failed

    print("\n" + "=" * 50)
    print("PEER GROUP HANDOFF SUMMARY")
    print("=" * 50)

    print(
        f"Tests passed : {total_passed}"
    )

    print(
        f"Tests failed : {total_failed}"
    )

    print("-" * 50)

    if total_failed == 0:

        print(
            "🎉 PEER GROUP DATA → LOGIC HANDOFF PASSED"
        )

        print(
            "Logic Engineer can consume sector and "
            "industry peer groups through Peer Group Service."
        )

        print("=" * 50)

        return True

    print(
        "❌ PEER GROUP DATA → LOGIC HANDOFF FAILED"
    )

    print(
        "Review the failed tests before continuing."
    )

    print("=" * 50)

    return False


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = main()

    if not success:
        raise SystemExit(1)