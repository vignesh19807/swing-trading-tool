"""
Comprehensive Unit & Integration Test Suite for P2.7 - P2.11
============================================================

Tests:
1. P2.7 — Binary Validation (magic bytes, PDF structure, EOF, size heuristics)
2. P2.7 — Operator-Assisted Submission & Manifest Requirements
3. P2.8 — Scope-Safe Extraction (Consolidated vs Standalone separation)
4. P2.8 — Commercial Banking Solvency (D/E=NULL, ROCE=NULL, customer deposits)
5. P2.9 — Historical PIT Eligibility & Market Calendar (market hours, holidays, weekends)
6. P2.9 — PIT Gating (PROVISIONAL_DEMO, QUARANTINED, SUPERSEDED, VERIFIED_ELIGIBLE)
7. P2.10 — Historical Lineage & Invariant Enforcement
8. P2.11 — 7 Independent Historical Scenario Verifications
"""

import os
import tempfile
import shutil
import sqlite3
import pytest

pytestmark = pytest.mark.requires_preseeded_db
from pathlib import Path
from datetime import date

from backend.data_pipeline.financial_filing_retriever import (
    validate_pdf_binary,
    compute_sha256,
    AuthenticDocumentRetriever,
)
from backend.data_pipeline.financial_filing_parser import (
    ScopeSafeFilingParser,
    normalize_to_crores,
)
from backend.data_pipeline.historical_pit_service import (
    is_market_trading_day,
    get_next_market_trading_day,
    determine_effective_trading_date,
    PointInTimeEligibilityService,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DB = (PROJECT_ROOT / "database" / "staging_financial_expansion.db").resolve()


@pytest.fixture
def temp_db(tmp_path):
    """Create isolated temporary SQLite DB fixture cloned from staging DB."""
    db_copy = tmp_path / "temp_staging.db"
    shutil.copy(STAGING_DB, db_copy)
    return db_copy


# =============================================================================
# P2.7 TESTS: Authentic Document Retrieval & Binary Validation
# =============================================================================

def test_p2_7_valid_pdf_binary():
    """Valid PDF binary passes all structural and integrity checks."""
    valid_pdf_content = (
        b"%PDF-1.7\r\n"
        b"1 0 obj\r\n<< /Type /Catalog /Pages 2 0 R >>\r\nendobj\r\n"
        b"2 0 obj\r\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\r\nendobj\r\n"
        b"3 0 obj\r\n<< /Type /Page /Parent 2 0 R >>\r\nendobj\r\n"
        b"xref\r\n0 4\r\n0000000000 65535 f\r\n"
        b"startxref\r\n180\r\n%%EOF\r\n"
    )
    res = validate_pdf_binary(valid_pdf_content)
    assert res.is_valid_binary is True
    assert res.magic_bytes_valid is True
    assert res.structure_valid is True
    assert res.eof_marker_valid is True
    assert res.page_count == 1
    assert len(res.validation_errors) == 0


def test_p2_7_corrupt_pdf_binary_rejected():
    """Corrupt or non-PDF binary fails validation."""
    corrupt_bytes = b"NOT_A_PDF_DOCUMENT_TEXT_CONTENT"
    res = validate_pdf_binary(corrupt_bytes)
    assert res.is_valid_binary is False
    assert res.magic_bytes_valid is False
    assert len(res.validation_errors) > 0


def test_p2_7_operator_submission_requires_manifest(tmp_path):
    """Operator submission without manifest is rejected."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    doc = inbox / "test_doc.pdf"
    doc.write_bytes(b"%PDF-1.4 dummy")
    retriever = AuthenticDocumentRetriever(inbox_dir=inbox)
    result = retriever.process_operator_submission("test_doc.pdf", "missing_manifest.json")
    assert result["retrieval_status"] == "MANIFEST_MISSING"


# =============================================================================
# P2.8 TESTS: Scope-Safe Financial Extraction & Banking Normalization
# =============================================================================

def test_p2_8_corporate_parsing_distinguishes_revenue_scope():
    """Corporate parser extracts revenue from operations and enforces scope."""
    payload = {
        "symbol": "TCS",
        "quarter": "2024-Q1",
        "filing_scope": "CONSOLIDATED",
        "revenue_from_operations": 62613.0,
        "total_income": 63500.0,
        "net_profit": 12040.0,
        "eps": 33.28,
        "total_equity": 91000.0,
        "total_debt": 0.0,
    }
    parsed = ScopeSafeFilingParser.parse_filing_payload(payload)
    assert parsed["filing_scope"] == "CONSOLIDATED"
    assert parsed["revenue"] == 62613.0
    assert parsed["revenue_from_operations"] == 62613.0
    assert parsed["total_income"] == 63500.0
    assert parsed["debt_equity"] == 0.0
    assert parsed["is_banking_institution"] == 0


def test_p2_8_banking_metrics_enforce_null_solvency():
    """Banking institutions have corporate D/E and ROCE strictly enforced as NULL."""
    payload = {
        "symbol": "HDFCBANK",
        "quarter": "2024-Q2",
        "filing_scope": "CONSOLIDATED",
        "is_bank": True,
        "total_income": 121457.0,
        "net_profit": 17830.0,
        "eps": 23.40,
        "net_interest_income": 30111.0,
        "customer_deposits": 2500100.0,
        "capital_adequacy_ratio": 19.80,
        "gross_npa_pct": 1.36,
        "net_npa_pct": 0.41,
        "total_equity": 455000.0,
    }
    parsed = ScopeSafeFilingParser.parse_filing_payload(payload)
    assert parsed["is_banking_institution"] == 1
    assert parsed["debt_equity"] is None
    assert parsed["roce"] is None
    assert parsed["total_debt"] is None
    assert parsed["customer_deposits"] == 2500100.0
    assert parsed["capital_adequacy_ratio"] == 19.80


def test_p2_8_scope_mixing_rejection():
    """Attempting to mix standalone banking metrics into consolidated filing raises error."""
    payload = {
        "symbol": "HDFCBANK",
        "quarter": "2024-Q2",
        "filing_scope": "CONSOLIDATED",
        "is_scope_mixed": True,
        "is_bank": True,
        "total_income": 121457.0,
        "net_profit": 17830.0,
        "eps": 23.40,
    }
    with pytest.raises(ValueError, match="Scope Safety Violation"):
        ScopeSafeFilingParser.parse_filing_payload(payload)


# =============================================================================
# P2.9 TESTS: Market Calendar & PIT Eligibility
# =============================================================================

def test_p2_9_after_market_announcement_moves_to_next_trading_day():
    """Announcement after 15:30 IST is effective next trading day."""
    # Thursday 2024-07-11 15:38:49 IST -> Effective Friday 2024-07-12
    eff = determine_effective_trading_date("2024-07-11 15:38:49")
    assert eff == "2024-07-12"


def test_p2_9_friday_after_market_moves_to_monday():
    """Friday evening announcement moves past weekend to Monday."""
    # Friday 2024-07-19 19:16:04 IST -> Effective Monday 2024-07-22
    eff = determine_effective_trading_date("2024-07-19 19:16:04")
    assert eff == "2024-07-22"


def test_p2_9_saturday_announcement_moves_to_monday():
    """Saturday board meeting outcome moves to Monday."""
    # Saturday 2024-07-20 14:15:17 IST -> Effective Monday 2024-07-22
    eff = determine_effective_trading_date("2024-07-20 14:15:17")
    assert eff == "2024-07-22"


def test_p2_9_during_market_announcement_same_day():
    """Announcement during active continuous trading (e.g. 14:15 IST) is effective same day."""
    # Tuesday 2024-10-29 14:58:48 IST -> Effective same day 2024-10-29
    eff = determine_effective_trading_date("2024-10-29 14:58:48")
    assert eff == "2024-10-29"


# =============================================================================
# P2.10 & P2.11 TESTS: Scenario Testing & Database Invariant Enforcement
# =============================================================================

def test_p2_11_historical_scenario_1_before_original_publication(temp_db):
    """Scenario 1: Before publication, no financial records are eligible."""
    pit = PointInTimeEligibilityService(temp_db)
    # TCS Q1 was published on 2024-07-11 (effective 2024-07-12)
    record = pit.get_eligible_vintage_as_of("TCS", "2024-07-10")
    assert record is None


def test_p2_11_historical_scenario_2_on_first_eligible_trading_date(temp_db):
    """Scenario 2: On first eligible trading date, authentic verified record is available."""
    pit = PointInTimeEligibilityService(temp_db)
    record = pit.get_eligible_vintage_as_of("TCS", "2024-07-12")
    assert record is not None
    assert record["id"] == 18
    assert record["quarter"] == "2024-Q1"
    assert record["revenue"] == 62613.0
    assert record["research_eligibility"] == "VERIFIED_ELIGIBLE"


def test_p2_11_historical_scenario_3_and_4_revision_supersession(temp_db):
    """Scenario 3 & 4: Before revision effective date, parent record is used; after revision, new record is used."""
    pit = PointInTimeEligibilityService(temp_db)
    # Between 2024-07-22 and 2024-10-14, Reliance Q1 is latest active
    r_q1 = pit.get_eligible_vintage_as_of("RELIANCE", "2024-08-01")
    assert r_q1 is not None
    assert r_q1["quarter"] == "2024-Q1"
    assert r_q1["revenue"] == 231784.0

    # On 2024-10-15, Reliance Q2 becomes effective
    r_q2 = pit.get_eligible_vintage_as_of("RELIANCE", "2024-10-15")
    assert r_q2 is not None
    assert r_q2["quarter"] == "2024-Q2"
    assert r_q2["revenue"] == 236217.0


def test_p2_11_historical_scenario_quarantine_blocking(temp_db):
    """Quarantined records (HDFCBANK) are strictly blocked from research and scoring."""
    pit = PointInTimeEligibilityService(temp_db)
    record = pit.get_eligible_vintage_as_of("HDFCBANK", "2024-11-01")
    assert record is None  # All HDFCBANK consolidated records remain QUARANTINED


def test_p2_11_database_trigger_blocks_illegal_deletion(temp_db):
    """Database triggers block any attempt to delete historical vintages."""
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    with pytest.raises(sqlite3.IntegrityError, match="Illegal deletion"):
        c.execute("DELETE FROM quarterly_financial_vintages WHERE id = 18")
    conn.close()


def test_p2_11_database_trigger_blocks_financial_mutation(temp_db):
    """Database triggers block mutating reported figures on existing vintages."""
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    with pytest.raises(sqlite3.IntegrityError, match="Illegal mutation"):
        c.execute("UPDATE quarterly_financial_vintages SET revenue = 99999.0 WHERE id = 18")
    conn.close()


# =============================================================================
# P2.13 TESTS: Financial Discrepancy Resolution & Fail-Closed PIT Enforcement
# =============================================================================

def test_p2_13_adani_q2_extraction_correction_supersession(temp_db):
    """
    P2.13 Issue A: Verify Vintage 28 supersedes Vintage 25 with corrected revenue and EPS.
    Vintage 25 retains original reported figures but marked SUPERSEDED.
    Vintage 28 has corrected revenue (22,608.07) and EPS (14.82) with EXTRACTION_CORRECTION.
    """
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    v25 = dict(c.execute("SELECT * FROM quarterly_financial_vintages WHERE id = 25").fetchone())
    v28 = dict(c.execute("SELECT * FROM quarterly_financial_vintages WHERE id = 28").fetchone())
    conn.close()

    # Predecessor Vintage 25 integrity
    assert v25["revenue"] == 22644.5
    assert v25["eps"] == 15.27
    assert v25["research_eligibility"] == "SUPERSEDED"
    assert v25["superseded_by_vintage_id"] == 28

    # Corrected Vintage 28 integrity
    assert v28["revenue"] == 22608.07
    assert v28["revenue_from_operations"] == 22608.07
    assert v28["total_income"] == 23196.18
    assert v28["net_profit"] == 1741.75
    assert v28["eps"] == 14.82
    assert v28["version_sequence"] == 4
    assert v28["parent_vintage_id"] == 25
    assert v28["supersedes_vintage_id"] == 25
    assert v28["superseded_by_vintage_id"] is None
    assert v28["company_filing_type"] == "ORIGINAL"
    assert v28["internal_revision_type"] == "EXTRACTION_CORRECTION"
    assert v28["verification_status"] == "VERIFIED"
    assert v28["research_eligibility"] == "VERIFIED_ELIGIBLE"
    assert v28["published_at"] == "2024-10-29 14:58:48"
    assert v28["effective_trading_date"] == "2024-10-29"


def test_p2_13_adani_pit_lookahead_query(temp_db):
    """
    P2.13 Issue A: Point-in-Time queries for ADANIENT:
    - Before 2024-10-29: returns Q1 (Vintage 24).
    - On/After 2024-10-29: returns Q2 (Vintage 28 with 22,608.07 Cr), NOT superseded Vintage 25.
    """
    pit = PointInTimeEligibilityService(temp_db)

    # 1. Day before Q2 release: only Q1 is eligible
    r_before = pit.get_eligible_vintage_as_of("ADANIENT", "2024-10-28")
    assert r_before is not None
    assert r_before["id"] == 24
    assert r_before["quarter"] == "2024-Q1"
    assert r_before["revenue"] == 25472.4

    # 2. On Q2 release effective date: returns corrected Vintage 28
    r_on = pit.get_eligible_vintage_as_of("ADANIENT", "2024-10-29")
    assert r_on is not None
    assert r_on["id"] == 28
    assert r_on["quarter"] == "2024-Q2"
    assert r_on["revenue"] == 22608.07
    assert r_on["net_profit"] == 1741.75
    assert r_on["eps"] == 14.82


def test_p2_13_pit_calendar_fail_closed_boundaries(temp_db):
    """
    P2.13 Issue D: PIT service strictly fails closed when evaluation date
    falls outside authenticated calendar window [2024-01-01 to 2025-12-31].
    """
    pit = PointInTimeEligibilityService(temp_db)

    # Future unverified date (> 2025-12-31) must fail closed
    with pytest.raises(ValueError, match="Fail-Closed"):
        pit.get_eligible_vintage_as_of("TCS", "2026-01-01")

    # Past unverified date (< 2024-01-01) must fail closed
    with pytest.raises(ValueError, match="Fail-Closed"):
        pit.get_eligible_vintage_as_of("TCS", "2023-12-31")

    # Function-level fail-closed check
    with pytest.raises(ValueError, match="Fail-Closed"):
        is_market_trading_day(date(2026, 6, 1))

    with pytest.raises(ValueError, match="Fail-Closed"):
        determine_effective_trading_date("2026-06-01 10:00:00")


def test_p2_13_hdfc_bank_quarantined_records_remain_blocked(temp_db):
    """
    P2.13 Issue B: HDFCBANK scanned filings without OCR verification
    remain strictly QUARANTINED and blocked from research eligibility.
    """
    pit = PointInTimeEligibilityService(temp_db)
    # Attempting to fetch eligible HDFCBANK vintage returns None
    rec = pit.get_eligible_vintage_as_of("HDFCBANK", "2024-10-25")
    assert rec is None

    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    hdfc_vintages = c.execute(
        "SELECT id, quarter, verification_status, research_eligibility FROM quarterly_financial_vintages WHERE company_id = 5"
    ).fetchall()
    conn.close()

    assert len(hdfc_vintages) >= 4
    for r in hdfc_vintages:
        # All HDFC records must be QUARANTINED, PROVISIONAL_DEMO, or SUPERSEDED
        assert r["research_eligibility"] in ("QUARANTINED", "PROVISIONAL_DEMO", "SUPERSEDED")
        assert r["research_eligibility"] != "VERIFIED_ELIGIBLE"


