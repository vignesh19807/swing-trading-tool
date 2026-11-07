"""
P2.5.2 Test Suite: Pilot Financial Remediation & Authentic Document Preservation
================================================================================

Comprehensive verification suite covering:
1. Preservation and non-deletion of original 10 pilot records (IDs 1-10).
2. Explicit superseded lineage connecting original records to remediation records.
3. Revenue normalization separating Net Revenue from Operations, Gross Revenue, and Total Income.
4. HDFC Bank scope alignment (Standalone vs Consolidated) and banking sector metrics (NII, CAR, NPA, D/E nullification).
5. Document store classification marking test fixtures as TEST_MOCK_ARTIFACT and SOURCE_DOCUMENT_UNAVAILABLE.
6. Strict Point-in-Time ranking prioritizing remediated records for current evaluation dates.
7. Production database isolation and hash immutability.
"""

import pytest
import sqlite3

pytestmark = pytest.mark.requires_preseeded_db
import hashlib
import json
from pathlib import Path
import pandas as pd

from backend.data_pipeline.staging_financial_vintage_service import StagingFinancialVintageRepository
from backend.data_pipeline.financial_filing_retriever import FilingDocumentManager
from backend.data_pipeline.financial_filing_parser import FilingParser

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DB_PATH = (PROJECT_ROOT / "database" / "staging_financial_expansion.db").resolve()
PRODUCTION_DB_PATH = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()
DOCS_STORE_PATH = (PROJECT_ROOT / "database" / "staging_filings_store").resolve()

EXPECTED_PROD_HASH = "1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8"


def test_01_original_pilot_records_preserved():
    """Verify all 10 original pilot records (IDs 1-10) remain intact in staging."""
    conn = sqlite3.connect(STAGING_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, company_id, quarter, version_sequence, superseded_by_vintage_id FROM quarterly_financial_vintages WHERE id <= 10 ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 10, f"Expected 10 original records preserved, found {len(rows)}"

    # Check TCS and INFY: originally un-superseded in P2.5, now superseded by authentic filings 18-21
    for r in rows[:4]:
        vintage_id, company_id, quarter, ver, superseded_by = r
        assert ver == 1
        assert superseded_by in (None, 18, 19, 20, 21), f"TCS/INFY vintage {vintage_id} has invalid supersession: {superseded_by}"

    # Check RELIANCE, HDFCBANK, ADANIENT are linked to remediation records
    superseded_expected = {
        5: 11,  # RELIANCE Q1 -> 11
        6: 12,  # RELIANCE Q2 -> 12
        7: 15,  # HDFCBANK Q1 -> 15
        8: 16,  # HDFCBANK Q2 -> 16
        9: 13,  # ADANIENT Q1 -> 13
        10: 14  # ADANIENT Q2 -> 14
    }
    for r in rows[4:]:
        vintage_id, company_id, quarter, ver, superseded_by = r
        assert ver == 1
        assert superseded_by == superseded_expected[vintage_id], (
            f"Vintage {vintage_id} should be superseded by {superseded_expected[vintage_id]}, got {superseded_by}"
        )


def test_02_revenue_normalization_line_items():
    """Verify revenue from operations vs gross revenue vs total income separation."""
    repo = StagingFinancialVintageRepository(STAGING_DB_PATH)

    # 1. RELIANCE Q1 FY25 Remediated (ID 11)
    v11 = repo.get_vintage_by_id(11)
    assert v11 is not None
    assert v11["revenue"] == 236217.0  # Net revenue from operations
    assert v11["revenue_from_operations"] == 236217.0
    assert v11["gross_revenue"] == 257823.0
    assert v11["total_income"] == 239856.0
    assert v11["remediation_type"] == "INTERNAL_EXTRACTION_CORRECTION"
    assert "₹236,217 Cr" in v11["remediation_notes"]

    # 2. RELIANCE Q2 FY25 Remediated (ID 12)
    v12 = repo.get_vintage_by_id(12)
    assert v12 is not None
    assert v12["revenue"] == 235481.0
    assert v12["revenue_from_operations"] == 235481.0
    assert v12["gross_revenue"] == 258027.0
    assert v12["total_income"] == 240316.0

    # 3. ADANIENT Q1 FY25 Remediated (ID 13)
    v13 = repo.get_vintage_by_id(13)
    assert v13 is not None
    assert v13["revenue"] == 25472.40  # Net of other income
    assert v13["revenue_from_operations"] == 25472.40
    assert v13["total_income"] == 26067.0
    assert v13["remediation_type"] == "INTERNAL_EXTRACTION_CORRECTION"

    # 4. ADANIENT Q2 FY25 Remediated (ID 14)
    v14 = repo.get_vintage_by_id(14)
    assert v14 is not None
    assert v14["revenue"] == 22608.0
    assert v14["revenue_from_operations"] == 22608.0
    assert v14["total_income"] == 23196.0


def test_03_hdfc_bank_scope_and_sector_metrics():
    """Verify HDFC Bank scope alignment and banking metric rules."""
    repo = StagingFinancialVintageRepository(STAGING_DB_PATH)

    # 1. HDFC Bank Q1 FY25 Banking Remediated (ID 15)
    v15 = repo.get_vintage_by_id(15)
    assert v15 is not None
    assert v15["debt_equity"] is None  # D/E must be NULL for banks
    assert v15["total_debt"] is None
    assert v15["customer_deposits"] == 2379100.0
    assert v15["net_interest_income"] == 29837.0
    assert v15["capital_adequacy_ratio"] == 19.33
    assert v15["gross_npa_pct"] == 1.33
    assert v15["net_npa_pct"] == 0.39
    assert v15["remediation_type"] == "SECTOR_BANKING_METRICS_REMEDIATION"

    # 2. HDFC Bank Q2 FY25 Consolidated Scope Aligned (ID 16)
    v16 = repo.get_vintage_by_id(16)
    assert v16 is not None
    assert v16["filing_scope"] == "CONSOLIDATED"
    assert v16["revenue"] == 121457.0  # Consolidated Total Income
    assert v16["total_income"] == 121457.0
    assert v16["net_profit"] == 17830.0  # Consolidated PAT
    assert v16["debt_equity"] is None
    assert v16["customer_deposits"] == 2500100.0
    assert v16["net_interest_income"] == 30111.0
    assert v16["remediation_type"] == "SCOPE_ALIGNMENT_CORRECTION"

    # 3. HDFC Bank Q2 FY25 Standalone Scope (ID 17)
    v17 = repo.get_vintage_by_id(17)
    assert v17 is not None
    assert v17["filing_scope"] == "STANDALONE"
    assert v17["revenue"] == 85499.64  # Standalone Total Income
    assert v17["net_profit"] == 16821.0  # Standalone PAT
    assert v17["debt_equity"] is None


def test_04_document_store_metadata_classification():
    """Verify document manager sidecar files are classified correctly for mocks and authentic filings."""
    # 1. Verify the 10 original mock artifact sidecars
    mock_files = list(DOCS_STORE_PATH.glob("*/*_Results.json"))
    assert len(mock_files) == 10, f"Expected 10 mock document metadata files, found {len(mock_files)}"

    for jf in mock_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        assert data.get("document_classification") == "TEST_MOCK_ARTIFACT", (
            f"File {jf.name} missing TEST_MOCK_ARTIFACT classification"
        )
        assert data.get("retrieval_status") == "SOURCE_DOCUMENT_UNAVAILABLE", (
            f"File {jf.name} missing SOURCE_DOCUMENT_UNAVAILABLE status"
        )
        assert data.get("source_document_url", "").startswith("https://"), (
            f"File {jf.name} missing authentic source URL"
        )

    # 2. Verify the 10 authentic exchange filings retrieved in P2.7-P2.10
    authentic_files = list(DOCS_STORE_PATH.glob("*/*_NSE_*.json"))
    assert len(authentic_files) == 10, f"Expected 10 authentic exchange metadata files, found {len(authentic_files)}"
    for af in authentic_files:
        data = json.loads(af.read_text(encoding="utf-8"))
        assert data.get("document_classification") == "AUTHENTIC_EXCHANGE_FILING", (
            f"File {af.name} missing AUTHENTIC_EXCHANGE_FILING classification"
        )
        assert data.get("retrieval_status") == "RETRIEVED_AUTHENTIC", (
            f"File {af.name} missing RETRIEVED_AUTHENTIC status"
        )


def test_05_pit_evaluation_prioritizes_remediations():
    """Verify point-in-time ranking prioritizes latest authentic and remediated vintages for current date."""
    repo = StagingFinancialVintageRepository(STAGING_DB_PATH)

    # Current evaluation date: 2026-11-04
    eval_date = "2026-11-04"

    # RELIANCE: Authentic exchange records (IDs 22 & 23, v3) supersede remediation records (IDs 11 & 12, v2)
    df_rel = repo.get_point_in_time_vintages("RELIANCE", eval_date, "CONSOLIDATED", allow_provisional=True)
    assert len(df_rel) == 2
    assert list(df_rel["vintage_id"]) == [22, 23]
    assert list(df_rel["version_sequence"]) == [3, 3]
    assert list(df_rel["revenue"]) == [231784.0, 236217.0]

    # HDFCBANK Consolidated: Quarantined in P2.5.3 due to scope/metric flaws; PIT returns empty
    df_hdfc = repo.get_point_in_time_vintages("HDFCBANK", eval_date, "CONSOLIDATED", allow_provisional=True)
    assert df_hdfc.empty, "Quarantined HDFC Bank consolidated vintages (15 & 16) must not be returned in PIT queries"

    # ADANIENT: Authentic exchange records (IDs 24 & 28, v3 & v4) supersede remediation records (IDs 13 & 14, v2)
    df_adani = repo.get_point_in_time_vintages("ADANIENT", eval_date, "CONSOLIDATED", allow_provisional=True)
    assert len(df_adani) == 2
    assert list(df_adani["vintage_id"]) == [24, 28]
    assert list(df_adani["version_sequence"]) == [3, 4]
    assert list(df_adani["revenue"]) == [25472.40, 22608.07]

    # TCS: Authentic exchange records (IDs 18 & 19, v2) supersede original provisional records (IDs 1 & 2, v1)
    df_tcs = repo.get_point_in_time_vintages("TCS", eval_date, "CONSOLIDATED", allow_provisional=True)
    assert len(df_tcs) == 2
    assert list(df_tcs["vintage_id"]) == [18, 19]
    assert list(df_tcs["version_sequence"]) == [2, 2]

    # INFY: Authentic exchange records (IDs 20 & 21, v2) supersede original provisional records (IDs 3 & 4, v1)
    df_infy = repo.get_point_in_time_vintages("INFY", eval_date, "CONSOLIDATED", allow_provisional=True)
    assert len(df_infy) == 2
    assert list(df_infy["vintage_id"]) == [20, 21]
    assert list(df_infy["version_sequence"]) == [2, 2]


def test_06_production_database_untouched():
    """Verify production database remains strictly untouched and unmodified."""
    with open(PRODUCTION_DB_PATH, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    assert actual_hash == EXPECTED_PROD_HASH, (
        f"CRITICAL SAFETY VIOLATION: Production database hash changed! "
        f"Expected {EXPECTED_PROD_HASH}, got {actual_hash}"
    )

