"""
P2.4 Test Suite: Staging Financial Vintage Schema & Point-in-Time Integrity
===========================================================================

Comprehensive test suite validating:
1. Schema creation & idempotency.
2. Database isolation (rejection of production path).
3. Foreign key constraints & CHECK constraints.
4. Append-only triggers (rejection of updates/deletions on verified records).
5. Point-in-time isolation (leakage prevention across restatement dates).
6. Scope isolation (CONSOLIDATED vs STANDALONE).
7. Quarantine of synthetic placeholder records.
8. Deterministic chronological query ordering.
"""

import sqlite3
import pytest
import pandas as pd
from pathlib import Path

from backend.database.migrate_staging_financial_vintages import (
    run_migration,
    VINTAGES_TABLE_SQL,
    INDEXES_SQL,
    APPEND_ONLY_TRIGGER_SQL,
    DELETE_PROTECTION_TRIGGER_SQL,
    verify_target_database,
    PRODUCTION_DATABASE_PATH,
)
from backend.data_pipeline.staging_financial_vintage_service import (
    StagingFinancialVintageRepository,
    is_synthetic_record,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create an isolated temporary SQLite database imitating staging schema."""
    db_file = tmp_path / "staging_financial_expansion.db"
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Create minimal companies table
    conn.execute("""
    CREATE TABLE companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE NOT NULL,
        company_name TEXT NOT NULL
    );
    """)
    conn.execute("INSERT INTO companies (id, symbol, company_name) VALUES (1, 'INFY', 'Infosys Limited');")
    conn.execute("INSERT INTO companies (id, symbol, company_name) VALUES (2, 'TCS', 'Tata Consultancy Services');")
    conn.commit()
    conn.close()
    
    # Run migration
    run_migration(db_file)
    return db_file


def test_01_migration_idempotency(temp_db):
    """Verify repeated execution of the migration script is completely safe and idempotent."""
    assert run_migration(temp_db) is True
    assert run_migration(temp_db) is True


def test_02_production_rejection_safety():
    """Verify that attempting to point the staging migration to production raises a critical safety error."""
    with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
        verify_target_database(PRODUCTION_DATABASE_PATH)

    with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
        StagingFinancialVintageRepository(PRODUCTION_DATABASE_PATH)


def test_03_foreign_key_enforcement(temp_db):
    """Verify foreign key constraint on company_id."""
    repo = StagingFinancialVintageRepository(temp_db)
    invalid_data = {
        "company_id": 9999,  # Non-existent company
        "quarter": "2024-Q2",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_9999_01",
        "publication_timestamp": "2024-07-15 16:00:00",
        "effective_trading_date": "2024-07-16",
        "revenue": 5000.0,
        "operating_expenses": 3500.0,
        "operating_profit": 1500.0,
        "net_profit": 1100.0,
        "eps": 25.0,
        "total_assets": 20000.0,
        "total_equity": 15000.0,
        "total_debt": 1000.0,
        "current_liabilities": 4000.0,
        "roe": 0.073,
        "roce": 0.093,
        "debt_equity": 0.067,
        "operating_margin": 0.30,
        "net_margin": 0.22,
        "source_document_url": "https://nsearchives.nseindia.com/test.pdf",
        "source_document_hash": "e" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Test"
    }
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_vintage(invalid_data)


def test_04_check_constraint_filing_type(temp_db):
    """Verify CHECK constraint rejects invalid filing_type."""
    repo = StagingFinancialVintageRepository(temp_db)
    data = {
        "company_id": 1,
        "quarter": "2024-Q2",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "INVALID_TYPE",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_01",
        "publication_timestamp": "2024-07-15 16:00:00",
        "effective_trading_date": "2024-07-16",
        "revenue": 5000.0,
        "operating_expenses": 3500.0,
        "operating_profit": 1500.0,
        "net_profit": 1100.0,
        "eps": 25.0,
        "total_assets": 20000.0,
        "total_equity": 15000.0,
        "total_debt": 1000.0,
        "current_liabilities": 4000.0,
        "roe": 0.073,
        "roce": 0.093,
        "debt_equity": 0.067,
        "operating_margin": 0.30,
        "net_margin": 0.22,
        "source_document_url": "https://nsearchives.nseindia.com/test.pdf",
        "source_document_hash": "a" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Test"
    }
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_vintage(data)


def test_05_synthetic_placeholder_rejection(temp_db):
    """Verify that known placeholder values (10000, 1500, 15) are strictly rejected by the repository."""
    repo = StagingFinancialVintageRepository(temp_db)
    data = {
        "company_id": 1,
        "quarter": "2024-Q2",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_SYNTH_01",
        "publication_timestamp": "2024-07-15 16:00:00",
        "effective_trading_date": "2024-07-16",
        "revenue": 10000.0,
        "operating_expenses": 8000.0,
        "operating_profit": 2000.0,
        "net_profit": 1500.0,
        "eps": 15.0,
        "total_assets": 20000.0,
        "total_equity": 15000.0,
        "total_debt": 1000.0,
        "current_liabilities": 4000.0,
        "roe": 0.18,
        "roce": 0.22,
        "debt_equity": 0.35,
        "operating_margin": 0.20,
        "net_margin": 0.15,
        "source_document_url": "https://nsearchives.nseindia.com/fake.pdf",
        "source_document_hash": "f" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Test"
    }
    with pytest.raises(ValueError, match="REJECTED_SYNTHETIC"):
        repo.insert_vintage(data)


def test_06_append_only_trigger_prevents_updates(temp_db):
    """Verify SQLite triggers prevent in-place mutation of verified records."""
    repo = StagingFinancialVintageRepository(temp_db)
    data = {
        "company_id": 1,
        "quarter": "2024-Q2",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_INFY_01",
        "publication_timestamp": "2024-07-18 15:45:00",
        "effective_trading_date": "2024-07-19",
        "revenue": 39315.0,
        "operating_expenses": 30000.0,
        "operating_profit": 9315.0,
        "net_profit": 6368.0,
        "eps": 15.35,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.075,
        "roce": 0.11,
        "debt_equity": 0.0,
        "operating_margin": 0.237,
        "net_margin": 0.162,
        "source_document_url": "https://nsearchives.nseindia.com/real_infy.pdf",
        "source_document_hash": "1" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Real Q1 FY25"
    }
    v_id = repo.insert_vintage(data)

    # Attempting to mutate revenue must fail via trigger
    with repo.get_connection() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="Illegal mutation"):
            conn.execute("UPDATE quarterly_financial_vintages SET revenue = 99999.0 WHERE id = ?", (v_id,))

    # Attempting to delete verified vintage must fail via trigger
    with repo.get_connection() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="Illegal deletion"):
            conn.execute("DELETE FROM quarterly_financial_vintages WHERE id = ?", (v_id,))


def test_07_point_in_time_restatement_isolation(temp_db):
    """
    CRITICAL POINT-IN-TIME TEST:
    Filing V1 is published on 2024-07-18 (effective 2024-07-19).
    Restatement V2 is published on 2024-09-10 (effective 2024-09-11).
    
    1. Evaluating on 2024-07-15 must see NOTHING (insufficient data).
    2. Evaluating on 2024-08-01 must see V1 (Original revenue 39315.0).
    3. Evaluating on 2024-09-05 must STILL see V1 (Original revenue 39315.0).
    4. Evaluating on 2024-09-15 must see V2 (Restated revenue 39500.0).
    """
    repo = StagingFinancialVintageRepository(temp_db)
    
    # Original Filing V1
    v1_data = {
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_INFY_V1",
        "publication_timestamp": "2024-07-18 15:45:00",
        "effective_trading_date": "2024-07-19",
        "revenue": 39315.0,
        "operating_expenses": 30000.0,
        "operating_profit": 9315.0,
        "net_profit": 6368.0,
        "eps": 15.35,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.075,
        "roce": 0.11,
        "debt_equity": 0.0,
        "operating_margin": 0.237,
        "net_margin": 0.162,
        "source_document_url": "https://nsearchives.nseindia.com/infy_v1.pdf",
        "source_document_hash": "1" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Original Q1 FY25"
    }
    v1_id = repo.insert_vintage(v1_data)

    # Restatement V2
    v2_data = {
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "RESTATED",
        "version_sequence": 2,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_INFY_V2",
        "publication_timestamp": "2024-09-10 16:00:00",
        "effective_trading_date": "2024-09-11",
        "revenue": 39500.0,  # Restated higher
        "operating_expenses": 30000.0,
        "operating_profit": 9500.0,
        "net_profit": 6500.0,
        "eps": 15.70,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.076,
        "roce": 0.112,
        "debt_equity": 0.0,
        "operating_margin": 0.241,
        "net_margin": 0.165,
        "source_document_url": "https://nsearchives.nseindia.com/infy_v2.pdf",
        "source_document_hash": "2" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Restated Corrigendum"
    }
    v2_id = repo.insert_vintage(v2_data)
    repo.supersede_vintage(v1_id, v2_id)

    # 1. Evaluation on 2024-07-15: Before V1 effective date (2024-07-19)
    df_pre = repo.get_point_in_time_vintages("INFY", "2024-07-15")
    assert df_pre.empty

    # 2. Evaluation on 2024-08-01: After V1 effective date, before V2 announcement
    df_aug = repo.get_point_in_time_vintages("INFY", "2024-08-01")
    assert len(df_aug) == 1
    assert df_aug.iloc[0]["version_sequence"] == 1
    assert df_aug.iloc[0]["revenue"] == 39315.0
    assert df_aug.iloc[0]["filing_type"] == "ORIGINAL"

    # 3. Evaluation on 2024-09-05: Before V2 effective date (2024-09-11)
    df_sep_early = repo.get_point_in_time_vintages("INFY", "2024-09-05")
    assert len(df_sep_early) == 1
    assert df_sep_early.iloc[0]["version_sequence"] == 1
    assert df_sep_early.iloc[0]["revenue"] == 39315.0

    # 4. Evaluation on 2024-09-15: After V2 effective date
    df_sep_late = repo.get_point_in_time_vintages("INFY", "2024-09-15")
    assert len(df_sep_late) == 1
    assert df_sep_late.iloc[0]["version_sequence"] == 2
    assert df_sep_late.iloc[0]["revenue"] == 39500.0
    assert df_sep_late.iloc[0]["filing_type"] == "RESTATED"


def test_08_scope_isolation_consolidated_vs_standalone(temp_db):
    """Verify that CONSOLIDATED and STANDALONE scopes are strictly isolated."""
    repo = StagingFinancialVintageRepository(temp_db)
    
    # Insert Consolidated
    repo.insert_vintage({
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_CONSOL",
        "publication_timestamp": "2024-07-18 15:45:00",
        "effective_trading_date": "2024-07-19",
        "revenue": 39315.0,
        "operating_expenses": 30000.0,
        "operating_profit": 9315.0,
        "net_profit": 6368.0,
        "eps": 15.35,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.075,
        "roce": 0.11,
        "debt_equity": 0.0,
        "operating_margin": 0.237,
        "net_margin": 0.162,
        "source_document_url": "https://nsearchives.nseindia.com/consol.pdf",
        "source_document_hash": "c" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Consol"
    })

    # Insert Standalone
    repo.insert_vintage({
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "STANDALONE",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_STAND",
        "publication_timestamp": "2024-07-18 15:45:00",
        "effective_trading_date": "2024-07-19",
        "revenue": 34000.0,  # Standalone revenue is lower
        "operating_expenses": 26000.0,
        "operating_profit": 8000.0,
        "net_profit": 5500.0,
        "eps": 13.25,
        "total_assets": 95000.0,
        "total_equity": 75000.0,
        "total_debt": 0.0,
        "current_liabilities": 20000.0,
        "roe": 0.073,
        "roce": 0.106,
        "debt_equity": 0.0,
        "operating_margin": 0.235,
        "net_margin": 0.161,
        "source_document_url": "https://nsearchives.nseindia.com/stand.pdf",
        "source_document_hash": "s" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Standalone"
    })

    df_consol = repo.get_point_in_time_vintages("INFY", "2024-08-01", filing_scope="CONSOLIDATED")
    assert len(df_consol) == 1
    assert df_consol.iloc[0]["revenue"] == 39315.0
    assert df_consol.iloc[0]["filing_scope"] == "CONSOLIDATED"

    df_stand = repo.get_point_in_time_vintages("INFY", "2024-08-01", filing_scope="STANDALONE")
    assert len(df_stand) == 1
    assert df_stand.iloc[0]["revenue"] == 34000.0
    assert df_stand.iloc[0]["filing_scope"] == "STANDALONE"


def test_09_unverified_records_exclusion(temp_db):
    """Verify that records with status PROVISIONAL or REJECTED are excluded by get_point_in_time_vintages."""
    repo = StagingFinancialVintageRepository(temp_db)
    repo.insert_vintage({
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_PROV",
        "publication_timestamp": "2024-07-18 15:45:00",
        "effective_trading_date": "2024-07-19",
        "revenue": 39315.0,
        "operating_expenses": 30000.0,
        "operating_profit": 9315.0,
        "net_profit": 6368.0,
        "eps": 15.35,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.075,
        "roce": 0.11,
        "debt_equity": 0.0,
        "operating_margin": 0.237,
        "net_margin": 0.162,
        "source_document_url": "https://nsearchives.nseindia.com/prov.pdf",
        "source_document_hash": "p" * 64,
        "verification_status": "PROVISIONAL",
        "verification_notes": "Unverified draft"
    })

    df = repo.get_point_in_time_vintages("INFY", "2024-08-01")
    assert df.empty


def test_10_deterministic_multi_quarter_ordering(temp_db):
    """Verify that multiple quarters are returned ordered chronologically by period_end_date."""
    repo = StagingFinancialVintageRepository(temp_db)
    
    # Q1
    repo.insert_vintage({
        "company_id": 1,
        "quarter": "2024-Q1",
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_Q1",
        "publication_timestamp": "2024-07-18 15:45:00",
        "effective_trading_date": "2024-07-19",
        "revenue": 39315.0,
        "operating_expenses": 30000.0,
        "operating_profit": 9315.0,
        "net_profit": 6368.0,
        "eps": 15.35,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.075,
        "roce": 0.11,
        "debt_equity": 0.0,
        "operating_margin": 0.237,
        "net_margin": 0.162,
        "source_document_url": "https://nsearchives.nseindia.com/q1.pdf",
        "source_document_hash": "1" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Q1"
    })

    # Q2
    repo.insert_vintage({
        "company_id": 1,
        "quarter": "2024-Q2",
        "period_start_date": "2024-07-01",
        "period_end_date": "2024-09-30",
        "accounting_standard": "IND_AS",
        "filing_scope": "CONSOLIDATED",
        "filing_type": "ORIGINAL",
        "version_sequence": 1,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": "NSE_Q2",
        "publication_timestamp": "2024-10-17 15:45:00",
        "effective_trading_date": "2024-10-18",
        "revenue": 40986.0,
        "operating_expenses": 31000.0,
        "operating_profit": 9986.0,
        "net_profit": 6506.0,
        "eps": 15.68,
        "total_assets": 118000.0,
        "total_equity": 87000.0,
        "total_debt": 0.0,
        "current_liabilities": 31000.0,
        "roe": 0.075,
        "roce": 0.114,
        "debt_equity": 0.0,
        "operating_margin": 0.244,
        "net_margin": 0.159,
        "source_document_url": "https://nsearchives.nseindia.com/q2.pdf",
        "source_document_hash": "2" * 64,
        "verification_status": "VERIFIED",
        "verification_notes": "Q2"
    })

    df = repo.get_point_in_time_vintages("INFY", "2024-11-01")
    assert len(df) == 2
    assert df.iloc[0]["quarter"] == "2024-Q1"
    assert df.iloc[1]["quarter"] == "2024-Q2"
    assert df.iloc[0]["revenue"] == 39315.0
    assert df.iloc[1]["revenue"] == 40986.0

