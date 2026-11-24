"""
backend/tests/migration/test_migration_checksum.py
==================================================
Tests for Phase 7.2C deterministic canonical SHA-256 checksumming.

Validates:
1. Canonical serialization formatting across all market fields.
2. Float rounding normalization (eliminating IEEE 754 noise).
3. Order-independent hashing (lexicographical sorting produces identical hash).
4. Sensitivity to value modifications (single bit/cent diff changes hash).
5. Financial vintage canonical hash sensitivity.
"""

from scripts.migration.common import (
    canonical_market_data_serialize,
    canonical_market_data_hash,
    canonical_exact_market_data_hash,
    canonical_financial_vintage_serialize,
    canonical_financial_vintage_hash,
    canonical_exact_financial_vintage_hash,
    canonical_quarantine_serialize,
    canonical_quarantine_hash,
    canonical_exact_quarantine_hash,
    FINANCIAL_TOLERANCE,
    MARKET_PRICE_TOLERANCE,
    classify_market_record,
    classify_financial_record,
    ConflictCategory
)

def test_canonical_market_data_serialization():
    row = {
        "symbol": "infy ",
        "date": "2026-11-01T00:00:00",
        "open": 1500.5,
        "high": 1520.123456,
        "low": 1490.0,
        "close": 1510.99999,
        "adjusted_close": None,
        "volume": 100000.0
    }
    serialized = canonical_market_data_serialize(row)
    assert serialized == "INFY|2026-11-01|1500.5000|1520.1235|1490.0000|1511.0000|NULL|100000"


def test_order_independent_market_checksum():
    row1 = {"symbol": "INFY", "date": "2026-11-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 102.0, "volume": 1000}
    row2 = {"symbol": "TCS", "date": "2026-11-01", "open": 200.0, "high": 205.0, "low": 195.0, "close": 202.0, "volume": 2000}
    
    hash_forward = canonical_market_data_hash([row1, row2])
    hash_reverse = canonical_market_data_hash([row2, row1])
    
    assert hash_forward == hash_reverse
    assert len(hash_forward) == 64


def test_market_checksum_sensitivity():
    row = {"symbol": "INFY", "date": "2026-11-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 102.0, "volume": 1000}
    base_hash = canonical_market_data_hash([row])
    
    # 1 cent change in close price
    row_alt = dict(row, close=102.01)
    alt_hash = canonical_market_data_hash([row_alt])
    
    assert base_hash != alt_hash

    # Change in volume
    row_vol = dict(row, volume=1001)
    vol_hash = canonical_market_data_hash([row_vol])
    assert base_hash != vol_hash


def test_financial_vintage_checksum_sensitivity():
    v1 = {
        "symbol": "HDFCBANK",
        "quarter": "2026-Q1",
        "version_sequence": 1,
        "period_start_date": "2025-04-01",
        "period_end_date": "2025-06-30",
        "verification_status": "AUTHENTIC_VERIFIED",
        "research_eligibility": "VERIFIED_ELIGIBLE",
        "publication_timestamp": "2025-07-20 14:00:00+05:30",
        "revenue": 50000.0,
        "net_profit": 15000.0,
        "source_document_hash": "HASH123"
    }
    h1 = canonical_financial_vintage_hash([v1])
    
    # Status changed to UNVERIFIED
    v2 = dict(v1, verification_status="AUTHENTIC_UNVERIFIED")
    h2 = canonical_financial_vintage_hash([v2])
    assert h1 != h2

    # Revenue changed
    v3 = dict(v1, revenue=50000.5)
    h3 = canonical_financial_vintage_hash([v3])
    assert h1 != h3


def test_quarantine_serialization_and_hash_sensitivity():
    """Validates deterministic serialization and hash sensitivity for quarantined legacy records."""
    q1 = {
        "symbol": "TCS",
        "quarter": "2025-Q1",
        "revenue": 60000.0,
        "net_profit": 12000.0,
        "eps": 32.5,
        "roe": 0.35,
        "roce": 0.42,
        "debt_equity": 0.05,
        "operating_margin": 0.25,
        "net_margin": 0.20,
        "publication_date": "2025-07-15",
        "quarantine_reason": "LEGACY_UNVERIFIED",
        "original_id": 42,
        "original_table": "quarterly_results"
    }
    s1 = canonical_quarantine_serialize(q1)
    assert "TCS|2025-Q1|60000.0000|12000.0000|32.5000|0.3500|0.4200|0.0500|0.2500|0.2000|2025-07-15|LEGACY_UNVERIFIED|42|quarterly_results" == s1

    h1 = canonical_quarantine_hash([q1])
    assert len(h1) == 64

    # Altering original_id changes hash
    q2 = dict(q1, original_id=43)
    assert canonical_quarantine_hash([q2]) != h1

    # Altering original_table changes hash
    q3 = dict(q1, original_table="custom_import")
    assert canonical_quarantine_hash([q3]) != h1

    # Order independence
    qa = dict(q1, symbol="INFY")
    qb = dict(q1, symbol="WIPRO")
    assert canonical_quarantine_hash([qa, qb]) == canonical_quarantine_hash([qb, qa])


def test_precision_policy_boundaries():
    """
    Validates the explicit numeric precision policy (Audit G):
    - 0.0001 Cr difference must alter the hash.
    - NULL vs 0.0 must produce distinct serializations.
    """
    row_base = {"symbol": "INFY", "date": "2026-11-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 100.0001, "volume": 1000}
    row_diff = {"symbol": "INFY", "date": "2026-11-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 100.0002, "volume": 1000}
    assert canonical_market_data_hash([row_base]) != canonical_market_data_hash([row_diff])

    # NULL vs 0.0
    r_null = {"symbol": "INFY", "date": "2026-11-01", "open": None, "high": 105.0, "low": 95.0, "close": 100.0, "volume": 1000}
    r_zero = {"symbol": "INFY", "date": "2026-11-01", "open": 0.0, "high": 105.0, "low": 95.0, "close": 100.0, "volume": 1000}
    assert canonical_market_data_serialize(r_null) != canonical_market_data_serialize(r_zero)


def test_exact_migration_integrity_checksum():
    """
    Validates Phase 7.2C.7 Exact Migration Integrity Hashing:
    - In exact mode, differences beyond 4 decimal places (e.g. 100.00001 vs 100.00002)
      MUST alter the hash, proving zero silent rounding or truncation.
    """
    row1 = {"symbol": "INFY", "date": "2026-11-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 100.00001, "volume": 1000}
    row2 = {"symbol": "INFY", "date": "2026-11-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 100.00002, "volume": 1000}
    
    # In standard statutory mode (4 decimals), these round to 100.0000
    assert canonical_market_data_hash([row1], exact=False) == canonical_market_data_hash([row2], exact=False)
    
    # In exact migration integrity mode, these MUST be strictly differentiated!
    h1_exact = canonical_exact_market_data_hash([row1])
    h2_exact = canonical_exact_market_data_hash([row2])
    assert h1_exact != h2_exact, "Exact migration hashing silently masked sub-4-decimal precision difference!"

    # Financial vintage exact hashing check
    v1 = {"symbol": "TCS", "quarter": "2026-Q1", "revenue": 50000.123456}
    v2 = {"symbol": "TCS", "quarter": "2026-Q1", "revenue": 50000.123459}
    assert canonical_financial_vintage_hash([v1], exact=False) == canonical_financial_vintage_hash([v2], exact=False)
    assert canonical_exact_financial_vintage_hash([v1]) != canonical_exact_financial_vintage_hash([v2])


def test_financial_tolerance_policy_separation():
    """
    Validates architectural separation between:
    1. Financial tolerance policy (1e-4 = 0.0001 Cr = Rs. 1,000 / 0.0001 INR)
    2. Exact migration integrity hashing
    """
    assert FINANCIAL_TOLERANCE == 1e-4
    assert MARKET_PRICE_TOLERANCE == 1e-4

    # 1. Market record within tolerance -> MATCHING
    src_m = {"open": 100.0, "high": 105.0, "low": 95.0, "close": 102.00004, "volume": 1000}
    dst_m = {"open": 100.0, "high": 105.0, "low": 95.0, "close": 102.00001, "volume": 1000} # Delta: 0.00003 < 1e-4
    cat_m, diffs_m = classify_market_record(src_m, dst_m)
    assert cat_m == ConflictCategory.MATCHING
    assert diffs_m is None

    # Market record exceeding tolerance -> CONFLICTING
    dst_m_conflict = dict(dst_m, close=102.0002) # Delta: 0.00016 > 1e-4
    cat_mc, diffs_mc = classify_market_record(src_m, dst_m_conflict)
    assert cat_mc == ConflictCategory.CONFLICTING
    assert "close" in diffs_mc

    # 2. Financial vintage record within tolerance -> MATCHING
    src_f = {"revenue": 50000.00004, "net_profit": 15000.0, "eps": 25.0}
    dst_f = {"revenue": 50000.00001, "net_profit": 15000.0, "eps": 25.0} # Delta: 0.00003 < 1e-4
    cat_f, diffs_f = classify_financial_record(src_f, dst_f)
    assert cat_f == ConflictCategory.MATCHING
    assert diffs_f is None

    # Financial record exceeding tolerance -> CONFLICTING
    dst_f_conflict = dict(dst_f, revenue=50000.0002) # Delta: 0.00016 > 1e-4
    cat_fc, diffs_fc = classify_financial_record(src_f, dst_f_conflict)
    assert cat_fc == ConflictCategory.CONFLICTING
    assert "revenue" in diffs_fc

