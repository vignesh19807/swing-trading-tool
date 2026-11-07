"""
P2.5 Test Suite: Financial Ingestion Pipeline & Pilot Integrity
===============================================================

Comprehensive offline tests covering:
1. Document manager file persistence and SHA-256 fingerprinting.
2. Unit normalizer conversions (Crores vs Lakhs vs INR).
3. Accounting validation (positive revenue, plausible PAT margins).
4. Market session engine (after-market, weekend, holiday, pre-market rules).
5. Ingestion orchestrator end-to-end processing.
6. Repeated ingestion idempotency (deduplication on exchange broadcast ID).
7. Verification that pilot data in staging database queries properly without lookahead.
"""

import pytest
import sqlite3
import pandas as pd
from pathlib import Path

from backend.data_pipeline.financial_filing_retriever import FilingDocumentManager, compute_sha256
from backend.data_pipeline.financial_filing_parser import FilingParser, normalize_to_crores
from backend.data_pipeline.financial_filing_validator import calculate_effective_trading_date, is_trading_day
from backend.data_pipeline.staging_financial_vintage_service import StagingFinancialVintageRepository
from backend.data_pipeline.staging_ingestion_orchestrator import StagingIngestionOrchestrator


def test_01_document_manager_hashing_and_persistence(tmp_path):
    """Verify document manager persists files and computes identical SHA-256."""
    doc_mgr = FilingDocumentManager(tmp_path / "filings")
    content = b"%PDF-1.4 Mock Financial Disclosure for INFY Q1"
    expected_hash = compute_sha256(content)
    
    meta = doc_mgr.preserve_document(
        symbol="INFY",
        quarter="2024-Q1",
        exchange="NSE",
        doc_filename="infy_q1.pdf",
        raw_bytes=content,
        source_url="https://nsearchives.nseindia.com/mock_infy.pdf"
    )
    
    assert meta["source_document_hash"] == expected_hash
    assert Path(meta["local_file_path"]).exists()
    assert Path(meta["local_file_path"]).read_bytes() == content


def test_02_unit_normalizer_conversions():
    """Verify reporting unit conversions to standardized INR Crores."""
    # Crores -> unchanged
    assert normalize_to_crores(5000.0, "CRORES") == 5000.0
    assert normalize_to_crores(5000.0, "CR") == 5000.0
    
    # Lakhs -> divided by 100
    assert normalize_to_crores(50000.0, "LAKHS") == 500.0
    assert normalize_to_crores(100.0, "LAKHS") == 1.0
    
    # INR -> divided by 10,000,000
    assert normalize_to_crores(100000000.0, "INR") == 10.0


def test_03_parser_accounting_ratios_calculation():
    """Verify parser computes valid margins and ROE from accounting line items."""
    raw = {
        "reported_unit": "CRORES",
        "revenue": 1000.0,
        "operating_expenses": 700.0,
        "operating_profit": 300.0,
        "net_profit": 200.0,
        "eps": 10.0,
        "total_assets": 5000.0,
        "total_equity": 2000.0,
        "total_debt": 500.0,
        "current_liabilities": 1000.0
    }
    parsed = FilingParser.parse_filing_payload(raw)
    assert parsed["revenue"] == 1000.0
    assert parsed["operating_margin"] == 0.30
    assert parsed["net_margin"] == 0.20
    assert parsed["roe"] == 0.10  # 200 / 2000
    assert parsed["debt_equity"] == 0.25  # 500 / 2000
    assert parsed["roce"] == 0.075  # 300 / (5000 - 1000)


def test_04_effective_trading_date_sessions():
    """Verify market hours and holiday mapping for effective trading dates."""
    # 1. Pre-market on Friday July 19, 2024 (08:30 IST) -> Same Day (2024-07-19)
    assert calculate_effective_trading_date("2024-07-19 08:30:00") == "2024-07-19"
    
    # 2. Intraday during session (14:15 IST on Thursday Aug 1, 2024) -> Same Day (2024-08-01)
    assert calculate_effective_trading_date("2024-08-01 14:15:00") == "2024-08-01"
    
    # 3. After continuous market close (17:30 IST on Thursday July 11, 2024) -> Next Day (2024-07-12)
    assert calculate_effective_trading_date("2024-07-11 17:30:00") == "2024-07-12"
    
    # 4. Weekend filing on Saturday July 20, 2024 (12:30 IST) -> Next Monday (2024-07-22)
    assert calculate_effective_trading_date("2024-07-20 12:30:00") == "2024-07-22"
    
    # 5. Date-only conservative fallback -> Next Trading Day
    assert calculate_effective_trading_date("2024-07-11") == "2024-07-12"


@pytest.mark.requires_preseeded_db
def test_05_staging_database_pilot_query_integrity():
    """Verify point-in-time querying against actual staging database records."""
    from backend.data_pipeline.staging_financial_vintage_service import STAGING_DATABASE_PATH
    repo = StagingFinancialVintageRepository(STAGING_DATABASE_PATH)
    
    # TCS: Q1 announced July 11 (effective July 12); Q2 announced Oct 10 (effective Oct 11)
    # 1. Evaluating on 2024-07-10 -> No records
    df_pre = repo.get_point_in_time_vintages("TCS", "2024-07-10", allow_provisional=True)
    assert df_pre.empty
    
    # 2. Evaluating on 2024-08-01 -> Only Q1 visible
    df_q1 = repo.get_point_in_time_vintages("TCS", "2024-08-01", allow_provisional=True)
    assert len(df_q1) == 1
    assert df_q1.iloc[0]["quarter"] == "2024-Q1"
    assert df_q1.iloc[0]["revenue"] == 62613.0
    assert df_q1.iloc[0]["net_profit"] == 12040.0
    
    # 3. Evaluating on 2024-10-15 -> Both Q1 and Q2 visible
    df_both = repo.get_point_in_time_vintages("TCS", "2024-10-15", allow_provisional=True)
    assert len(df_both) == 2
    assert df_both.iloc[0]["quarter"] == "2024-Q1"
    assert df_both.iloc[1]["quarter"] == "2024-Q2"
    assert df_both.iloc[1]["revenue"] == 64259.0
    assert df_both.iloc[1]["net_profit"] == 11909.0


def test_06_duplicate_broadcast_rejection(tmp_path):
    """Verify that inserting the same exchange broadcast ID twice raises IntegrityError."""
    db_file = tmp_path / "staging_financial_expansion.db"
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, symbol TEXT UNIQUE);")
    conn.execute("INSERT INTO companies VALUES (1, 'INFY');")
    conn.commit()
    conn.close()
    
    from backend.database.migrate_staging_financial_vintages import run_migration
    run_migration(db_file)
    
    repo = StagingFinancialVintageRepository(db_file)
    doc_mgr = FilingDocumentManager(tmp_path / "docs")
    orchestrator = StagingIngestionOrchestrator(repo, doc_mgr)
    
    filing_args = {
        "symbol": "INFY",
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_DUP_TEST_01",
        "publication_timestamp": "2024-07-18 15:45:00",
        "raw_accounting_data": {"reported_unit": "CRORES", "revenue": 39315.0, "net_profit": 6368.0, "eps": 15.35},
        "source_url": "https://nsearchives.nseindia.com/dup.pdf",
        "raw_document_bytes": b"content",
        "doc_filename": "dup.pdf"
    }
    
    # First insert succeeds
    v_id = orchestrator.ingest_filing(**filing_args)
    assert v_id > 0
    
    # Second insert with identical broadcast ID fails via UNIQUE constraint
    with pytest.raises(sqlite3.IntegrityError):
        orchestrator.ingest_filing(**filing_args)

