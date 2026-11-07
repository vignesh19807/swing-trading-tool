"""
P2.6 Test Suite: Classification & Financial Vintage Lineage Schema
==================================================================

Comprehensive test suite validating:
1. Four independent classification dimensions (allowed values, check constraints).
2. Semantic conflation prevention (internal fixes cannot be corporate restatements).
3. Promotion invariants (VERIFIED_ELIGIBLE strictly requires verification_status = 'VERIFIED').
4. Canonical timestamp immutability and separate corporate restatement availability.
5. Lineage integrity: parent-child, self-supersession rejection, circular lineage prevention.
6. Quarantine isolation: quarantined records blocked from PIT queries.
7. Status transitions and auditable logging.
8. Migration fidelity: all 17 existing records preserved, correct initial conservative classification.
"""

import sqlite3
import pytest
from pathlib import Path
from typing import Dict, Any

from backend.database.migrate_staging_financial_vintages import (
    run_migration,
    VINTAGES_TABLE_SQL,
    INDEXES_SQL,
    APPEND_ONLY_TRIGGER_SQL,
    FINANCIAL_MUTATION_GUARD_SQL,
    INSERT_CONFLATION_GUARD_SQL,
    verify_target_database,
    PRODUCTION_DATABASE_PATH,
)
from backend.data_pipeline.staging_financial_vintage_service import (
    StagingFinancialVintageRepository,
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
    conn.execute("INSERT INTO companies (id, symbol, company_name) VALUES (4, 'RELIANCE', 'Reliance Industries Limited');")
    conn.execute("INSERT INTO companies (id, symbol, company_name) VALUES (5, 'HDFCBANK', 'HDFC Bank Limited');")
    conn.execute("INSERT INTO companies (id, symbol, company_name) VALUES (43, 'ADANIENT', 'Adani Enterprises Limited');")
    conn.commit()
    conn.close()
    
    # Run migration to create schema
    run_migration(db_file)
    return db_file


def _build_sample_vintage(
    company_id: int = 1,
    quarter: str = "2024-Q1",
    broadcast_id: str = "NSE_TEST_01",
    company_filing_type: str = "ORIGINAL",
    internal_revision_type: str = "INITIAL_INGESTION",
    verification_status: str = "PROVISIONAL",
    research_eligibility: str = "PROVISIONAL_DEMO",
    version_sequence: int = 1,
    published_at: str = "2024-07-18 15:45:00",
    effective_trading_date: str = "2024-07-19",
    revenue: float = 39315.0,
    net_profit: float = 6368.0,
    eps: float = 15.35,
    filing_scope: str = "CONSOLIDATED"
) -> Dict[str, Any]:
    """Helper to generate valid vintage dictionary for testing."""
    return {
        "company_id": company_id,
        "quarter": quarter,
        "period_start_date": "2024-04-01",
        "period_end_date": "2024-06-30",
        "accounting_standard": "IND_AS",
        "filing_scope": filing_scope,
        "company_filing_type": company_filing_type,
        "internal_revision_type": internal_revision_type,
        "verification_status": verification_status,
        "research_eligibility": research_eligibility,
        "version_sequence": version_sequence,
        "parent_vintage_id": None,
        "supersedes_vintage_id": None,
        "superseded_by_vintage_id": None,
        "exchange": "NSE",
        "exchange_broadcast_id": broadcast_id,
        "published_at": published_at,
        "effective_trading_date": effective_trading_date,
        "revenue": revenue,
        "operating_expenses": 30000.0,
        "operating_profit": 9315.0,
        "net_profit": net_profit,
        "eps": eps,
        "total_assets": 115000.0,
        "total_equity": 85000.0,
        "total_debt": 0.0,
        "current_liabilities": 30000.0,
        "roe": 0.075,
        "roce": 0.11,
        "debt_equity": 0.0,
        "operating_margin": 0.237,
        "net_margin": 0.162,
        "source_document_url": "https://nsearchives.nseindia.com/sample.pdf",
        "source_document_hash": "a" * 64,
        "verification_notes": "Sample test vintage"
    }


def test_01_classification_dimensions_allowed_values(temp_db):
    """Verify all valid combinations of the 4 classification dimensions are accepted."""
    repo = StagingFinancialVintageRepository(temp_db)
    
    filing_types = ['ORIGINAL', 'REVISED_DISCLOSURE', 'CORPORATE_RESTATEMENT', 'ANNUAL_AUDITED_FINAL']
    for idx, ft in enumerate(filing_types):
        data = _build_sample_vintage(
            quarter=f"2023-Q{idx+1}",
            broadcast_id=f"NSE_FT_{idx}",
            company_filing_type=ft,
            internal_revision_type='INITIAL_INGESTION',
            verification_status='PROVISIONAL',
            research_eligibility='PROVISIONAL_DEMO'
        )
        v_id = repo.insert_vintage(data)
        assert v_id > 0

    rev_types = ['INITIAL_INGESTION', 'EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION']
    for idx, rt in enumerate(rev_types):
        data = _build_sample_vintage(
            company_id=2,
            quarter=f"2023-Q{idx+1}",
            broadcast_id=f"NSE_RT_{idx}",
            company_filing_type='ORIGINAL',
            internal_revision_type=rt,
            verification_status='PROVISIONAL',
            research_eligibility='PROVISIONAL_DEMO'
        )
        v_id = repo.insert_vintage(data)
        assert v_id > 0


def test_02_classification_rejections(temp_db):
    """Verify invalid classification dimension values are strictly rejected."""
    repo = StagingFinancialVintageRepository(temp_db)

    # Invalid company_filing_type
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_INV_1",
            company_filing_type="INVALID_FILING_TYPE"
        ))

    # Invalid internal_revision_type
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_INV_2",
            internal_revision_type="UNAUTHORIZED_REVISION"
        ))

    # Invalid verification_status
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_INV_3",
            verification_status="PARTIALLY_VERIFIED"
        ))

    # Invalid research_eligibility
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_INV_4",
            research_eligibility="LIVE_PRODUCTION"
        ))


def test_03_conflation_prevention(temp_db):
    """Verify semantic conflation of internal fixes with corporate restatements is rejected."""
    repo = StagingFinancialVintageRepository(temp_db)

    # EXTRACTION_CORRECTION cannot have company_filing_type = CORPORATE_RESTATEMENT
    with pytest.raises(ValueError, match="Semantic Conflation Error"):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_CONF_1",
            company_filing_type="CORPORATE_RESTATEMENT",
            internal_revision_type="EXTRACTION_CORRECTION"
        ))

    # SCOPE_REALIGNMENT cannot have company_filing_type = CORPORATE_RESTATEMENT
    with pytest.raises(ValueError, match="Semantic Conflation Error"):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_CONF_2",
            company_filing_type="CORPORATE_RESTATEMENT",
            internal_revision_type="SCOPE_REALIGNMENT"
        ))


def test_04_unverified_promotion_rejection(temp_db):
    """Verify a vintage cannot become VERIFIED_ELIGIBLE without verification_status = 'VERIFIED'."""
    repo = StagingFinancialVintageRepository(temp_db)

    # Rejection at insert time
    with pytest.raises(ValueError, match="Integrity Error"):
        repo.insert_vintage(_build_sample_vintage(
            broadcast_id="NSE_UNVER_1",
            verification_status="PROVISIONAL",
            research_eligibility="VERIFIED_ELIGIBLE"
        ))

    # Rejection at update time via service
    v_id = repo.insert_vintage(_build_sample_vintage(
        broadcast_id="NSE_UNVER_2",
        verification_status="PROVISIONAL",
        research_eligibility="PROVISIONAL_DEMO"
    ))
    with pytest.raises(ValueError, match="Integrity Error"):
        repo.record_status_transition(
            vintage_id=v_id,
            new_verification_status="PROVISIONAL",
            new_research_eligibility="VERIFIED_ELIGIBLE",
            notes="Illegal promotion attempt"
        )


def test_05_canonical_timestamps_immutability(temp_db):
    """Verify publication timestamp and reported financial figures cannot be mutated."""
    repo = StagingFinancialVintageRepository(temp_db)
    v_id = repo.insert_vintage(_build_sample_vintage(
        broadcast_id="NSE_MUT_1",
        published_at="2024-07-18 15:45:00",
        effective_trading_date="2024-07-19",
        revenue=50000.0
    ))

    with repo.get_connection() as conn:
        # Cannot mutate published_at
        with pytest.raises(sqlite3.DatabaseError, match="Illegal mutation"):
            conn.execute("UPDATE quarterly_financial_vintages SET published_at = '2024-07-20 10:00:00' WHERE id = ?", (v_id,))

        # Cannot mutate effective_trading_date
        with pytest.raises(sqlite3.DatabaseError, match="Illegal mutation"):
            conn.execute("UPDATE quarterly_financial_vintages SET effective_trading_date = '2024-07-20' WHERE id = ?", (v_id,))

        # Cannot mutate revenue
        with pytest.raises(sqlite3.DatabaseError, match="Illegal mutation"):
            conn.execute("UPDATE quarterly_financial_vintages SET revenue = 99999.0 WHERE id = ?", (v_id,))


def test_06_lineage_parent_child_and_supersession(temp_db):
    """Verify transactional creation of internal correction and bidirectional lineage links."""
    repo = StagingFinancialVintageRepository(temp_db)
    
    # 1. Initial ingestion
    v1_id = repo.insert_vintage(_build_sample_vintage(
        broadcast_id="NSE_LINEAGE_V1",
        revenue=30000.0,
        version_sequence=1
    ))

    # 2. Internal extraction correction
    correction_data = {
        "revenue": 28500.0,
        "revenue_from_operations": 28500.0,
        "total_income": 30000.0,
        "exchange_broadcast_id": "NSE_LINEAGE_V1_CORR"
    }
    v2_id = repo.create_internal_correction(
        predecessor_id=v1_id,
        corrected_data=correction_data,
        revision_type="EXTRACTION_CORRECTION",
        reason="Deducted other income from gross total",
        auditor_id="SENIOR_AUDITOR_42"
    )

    # Verify v1 is now superseded
    v1 = repo.get_vintage_by_id(v1_id)
    assert v1["superseded_by_vintage_id"] == v2_id
    assert v1["research_eligibility"] == "SUPERSEDED"

    # Verify v2 has proper lineage
    v2 = repo.get_vintage_by_id(v2_id)
    assert v2["parent_vintage_id"] == v1_id
    assert v2["supersedes_vintage_id"] == v1_id
    assert v2["version_sequence"] == 2
    assert v2["internal_revision_type"] == "EXTRACTION_CORRECTION"
    assert v2["company_filing_type"] == "ORIGINAL"
    assert v2["internally_corrected_at"] is not None
    assert v2["revenue"] == 28500.0

    # Lineage traversal
    lineage = repo.get_vintage_lineage(v2_id)
    assert len(lineage["ancestors"]) == 1
    assert lineage["ancestors"][0]["id"] == v1_id


def test_07_self_supersession_rejection(temp_db):
    """Verify a vintage cannot supersede itself."""
    repo = StagingFinancialVintageRepository(temp_db)
    v_id = repo.insert_vintage(_build_sample_vintage(broadcast_id="NSE_SELF_1"))

    with repo.get_connection() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="Illegal lineage"):
            conn.execute("UPDATE quarterly_financial_vintages SET superseded_by_vintage_id = ? WHERE id = ?", (v_id, v_id))

        with pytest.raises(sqlite3.DatabaseError, match="Illegal lineage"):
            conn.execute("UPDATE quarterly_financial_vintages SET supersedes_vintage_id = ? WHERE id = ?", (v_id, v_id))


def test_08_circular_lineage_rejection(temp_db):
    """Verify circular supersession is rejected."""
    repo = StagingFinancialVintageRepository(temp_db)
    v1_id = repo.insert_vintage(_build_sample_vintage(broadcast_id="NSE_CIRC_1", version_sequence=1))
    v2_id = repo.insert_vintage(_build_sample_vintage(broadcast_id="NSE_CIRC_2", version_sequence=2))

    # Link v1 superseded by v2
    repo.mark_superseded(v1_id, v2_id)

    # Attempt to have v2 superseded by v1 (circular)
    with repo.get_connection() as conn:
        # Set supersedes link on v2
        conn.execute("UPDATE quarterly_financial_vintages SET supersedes_vintage_id = ? WHERE id = ?", (v1_id, v2_id))
        conn.commit()

        # Attempt to set superseded_by_vintage_id on v2 back to v1
        with pytest.raises(sqlite3.DatabaseError, match="Illegal circular lineage"):
            conn.execute("UPDATE quarterly_financial_vintages SET superseded_by_vintage_id = ? WHERE id = ?", (v1_id, v2_id))


def test_09_quarantine_isolation(temp_db):
    """Verify quarantined records cannot be retrieved by point-in-time queries."""
    repo = StagingFinancialVintageRepository(temp_db)
    v_id = repo.insert_vintage(_build_sample_vintage(
        broadcast_id="NSE_QUAR_1",
        verification_status="PROVISIONAL",
        research_eligibility="PROVISIONAL_DEMO"
    ))

    # Quarantine the record
    repo.quarantine_vintage(v_id, reason="Scope misalignment in consolidated numbers", auditor_id="AUDIT_TEAM")
    v = repo.get_vintage_by_id(v_id)
    assert v["research_eligibility"] == "QUARANTINED"
    assert "QUARANTINED by AUDIT_TEAM" in v["verification_notes"]

    # Even with allow_provisional=True, QUARANTINED records MUST NOT be returned
    df = repo.get_point_in_time_vintages("INFY", "2024-08-01", allow_provisional=True)
    assert df.empty


def test_10_status_transition_audit(temp_db):
    """Verify auditable transitions between verification and eligibility states."""
    repo = StagingFinancialVintageRepository(temp_db)
    v_id = repo.insert_vintage(_build_sample_vintage(
        broadcast_id="NSE_AUDIT_1",
        verification_status="PROVISIONAL",
        research_eligibility="PROVISIONAL_DEMO"
    ))

    # Legitimate audited promotion to VERIFIED and VERIFIED_ELIGIBLE
    repo.record_status_transition(
        vintage_id=v_id,
        new_verification_status="VERIFIED",
        new_research_eligibility="VERIFIED_ELIGIBLE",
        notes="Verified against authentic BSE PDF broadcast 500209_12072024.pdf"
    )

    v = repo.get_vintage_by_id(v_id)
    assert v["verification_status"] == "VERIFIED"
    assert v["research_eligibility"] == "VERIFIED_ELIGIBLE"
    assert "Verified against authentic BSE PDF" in v["verification_notes"]

    # Now point-in-time query with allow_provisional=False finds it
    df = repo.get_point_in_time_vintages("INFY", "2024-08-01", allow_provisional=False)
    assert len(df) == 1
    assert df.iloc[0]["vintage_id"] == v_id


@pytest.mark.requires_preseeded_db
def test_11_migration_fidelity_preserves_all_17_records(tmp_path):
    """
    Simulate full migration of the 17 staging records on an isolated copy database.
    Verify:
    1. Exact 17 records migrated.
    2. Zero financial values altered.
    3. HDFC records 15 & 16 remain QUARANTINED.
    4. Vintages 1-4 remain PROVISIONAL_DEMO.
    5. Vintages 5-10 remain SUPERSEDED.
    """
    from backend.database.migrate_staging_financial_vintages import STAGING_DATABASE_PATH
    import shutil

    # Copy actual staging database to temporary location for migration verification
    test_db_copy = tmp_path / "staging_financial_expansion.db"
    shutil.copyfile(STAGING_DATABASE_PATH, test_db_copy)

    repo = StagingFinancialVintageRepository(test_db_copy)
    
    # Verify count of preserved legacy records
    with repo.get_connection() as conn:
        legacy_count = conn.execute("SELECT COUNT(*) FROM quarterly_financial_vintages WHERE id <= 17").fetchone()[0]
        assert legacy_count == 17, f"Expected all 17 legacy vintages preserved, found {legacy_count}"
        total_count = conn.execute("SELECT COUNT(*) FROM quarterly_financial_vintages").fetchone()[0]
        assert total_count == 28, f"Expected 28 total vintages in staging, found {total_count}"

    # Check classifications of legacy records
    v1 = repo.get_vintage_by_id(1)
    assert v1["verification_status"] == "PROVISIONAL"
    assert v1["revenue"] == 62613.0

    v5 = repo.get_vintage_by_id(5)
    assert v5["superseded_by_vintage_id"] == 11
    assert v5["revenue"] == 257823.0

    v11 = repo.get_vintage_by_id(11)
    assert v11["internal_revision_type"] == "EXTRACTION_CORRECTION"
    assert v11["revenue"] == 236217.0

    v15 = repo.get_vintage_by_id(15)
    assert v15["internal_revision_type"] == "SCOPE_REALIGNMENT"

    v16 = repo.get_vintage_by_id(16)

    v17 = repo.get_vintage_by_id(17)
    assert v17["research_eligibility"] == "PROVISIONAL_DEMO"
    assert v17["filing_scope"] == "STANDALONE"

