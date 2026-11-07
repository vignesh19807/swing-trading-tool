"""
Staging Database Migration: Financial Vintage Classification & Lineage Schema (Phase P2.6)
==========================================================================================

Implements the approved four-dimensional classification schema and canonical lineage model
exclusively in `database/staging_financial_expansion.db`.

Safety Guarantees:
- Hardcoded rejection of production database paths (`database/swing_trading.db`).
- Zero modifications to production database or legacy `quarterly_results` rows.
- Complete preservation of all existing 17 staging vintages (zero rows deleted).
- Enforces four independent dimensions:
    1. company_filing_type:       ['ORIGINAL', 'REVISED_DISCLOSURE', 'CORPORATE_RESTATEMENT', 'ANNUAL_AUDITED_FINAL']
    2. internal_revision_type:    ['INITIAL_INGESTION', 'EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION']
    3. verification_status:       ['VERIFIED', 'PROVISIONAL', 'REJECTED']
    4. research_eligibility:      ['VERIFIED_ELIGIBLE', 'PROVISIONAL_DEMO', 'QUARANTINED', 'SUPERSEDED']
- Canonical 5-timestamp tracking model (`published_at`, `ingested_at`, `internally_corrected_at`, `effective_trading_date`, `company_revision_published_at`).
- Complete bidirectional lineage tracking (`parent_vintage_id`, `supersedes_vintage_id`, `superseded_by_vintage_id`).
- SQLite triggers enforcing append-only immutability, circular lineage rejection, and semantic conflation prevention.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

STAGING_DATABASE_PATH = (PROJECT_ROOT / "database" / "staging_financial_expansion.db").resolve()
PRODUCTION_DATABASE_PATH = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()


VINTAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS quarterly_financial_vintages (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id                      INTEGER NOT NULL,
    quarter                         TEXT NOT NULL,               -- e.g. '2024-Q1', '2024-Q2'
    period_start_date               TEXT NOT NULL,               -- 'YYYY-MM-DD'
    period_end_date                 TEXT NOT NULL,               -- 'YYYY-MM-DD'
    accounting_standard             TEXT NOT NULL DEFAULT 'IND_AS' CHECK(accounting_standard IN ('IND_AS', 'IGAAP')),
    filing_scope                    TEXT NOT NULL DEFAULT 'CONSOLIDATED' CHECK(filing_scope IN ('CONSOLIDATED', 'STANDALONE')),
    
    -- 1. Four Independent Classification Dimensions (P2.6)
    company_filing_type             TEXT NOT NULL CHECK(company_filing_type IN (
                                        'ORIGINAL', 'REVISED_DISCLOSURE', 'CORPORATE_RESTATEMENT', 'ANNUAL_AUDITED_FINAL'
                                    )),
    filing_type                     TEXT GENERATED ALWAYS AS (company_filing_type) VIRTUAL,
    internal_revision_type          TEXT NOT NULL DEFAULT 'INITIAL_INGESTION' CHECK(internal_revision_type IN (
                                        'INITIAL_INGESTION', 'EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION'
                                    )),
    verification_status             TEXT NOT NULL DEFAULT 'PROVISIONAL' CHECK(verification_status IN (
                                        'VERIFIED', 'PROVISIONAL', 'REJECTED'
                                    )),
    research_eligibility            TEXT NOT NULL DEFAULT 'PROVISIONAL_DEMO' CHECK(research_eligibility IN (
                                        'VERIFIED_ELIGIBLE', 'PROVISIONAL_DEMO', 'QUARANTINED', 'SUPERSEDED'
                                    )),
                                    
    -- 2. Versioning & Lineage Model (P2.6)
    version_sequence                INTEGER NOT NULL DEFAULT 1 CHECK(version_sequence >= 1),
    parent_vintage_id               INTEGER,
    supersedes_vintage_id           INTEGER,
    superseded_by_vintage_id        INTEGER,
    revision_reason                 TEXT,
    revision_source                 TEXT,
    lineage_created_at              TEXT DEFAULT CURRENT_TIMESTAMP,

    -- 3. Canonical Timestamps (P2.6)
    exchange                        TEXT NOT NULL CHECK(exchange IN ('NSE', 'BSE')),
    exchange_broadcast_id           TEXT NOT NULL,
    original_broadcast_id           TEXT,
    internal_correction_event_id    TEXT,
    published_at                    TEXT NOT NULL,               -- Official exchange announcement timestamp (ISO 8601)
    publication_timestamp           TEXT GENERATED ALWAYS AS (published_at) VIRTUAL,
    effective_trading_date          TEXT NOT NULL,               -- First executable market trading session ('YYYY-MM-DD')
    ingested_at                     TEXT DEFAULT CURRENT_TIMESTAMP,
    internally_corrected_at         TEXT,
    company_revision_published_at   TEXT,

    -- 4. Disaggregated Operating Financials (in INR Crores)
    revenue                         REAL NOT NULL,               -- Standardized Revenue from Operations
    revenue_from_operations         REAL,                        -- Disclosed Revenue from Core Operations
    gross_revenue                   REAL,                        -- Disclosed Gross Turnover before duties/GST
    total_income                    REAL,                        -- Turnover + Other Income
    operating_expenses              REAL,
    operating_profit                REAL,
    net_profit                      REAL NOT NULL,               -- Profit After Tax (PAT)
    eps                             REAL NOT NULL,

    -- 5. Sector-Aware Banking / Financial Institutions Metrics
    is_banking_institution          INTEGER NOT NULL DEFAULT 0 CHECK(is_banking_institution IN (0, 1)),
    net_interest_income             REAL,
    customer_deposits               REAL,
    capital_adequacy_ratio          REAL,
    gross_npa_pct                   REAL,
    net_npa_pct                     REAL,

    -- 6. Standard Balance Sheet Line Items
    total_assets                    REAL,
    total_equity                    REAL,
    total_debt                      REAL,                        -- Corporate borrowings (excluding bank customer deposits)
    current_liabilities             REAL,

    -- 7. Materialized Financial Ratios
    roe                             REAL,
    roce                            REAL,
    debt_equity                     REAL,                        -- NULL for banking institutions
    operating_margin                REAL,
    net_margin                      REAL,

    -- 8. Provenance & Audit Metadata
    source_document_url             TEXT NOT NULL,
    source_document_hash            TEXT NOT NULL,               -- SHA-256 fingerprint
    verification_notes              TEXT,
    remediation_type                TEXT,                        -- Legacy compatibility column
    remediation_notes               TEXT,
    created_at                      TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (parent_vintage_id) REFERENCES quarterly_financial_vintages(id),
    FOREIGN KEY (supersedes_vintage_id) REFERENCES quarterly_financial_vintages(id),
    FOREIGN KEY (superseded_by_vintage_id) REFERENCES quarterly_financial_vintages(id),

    -- Integrity Constraints
    CHECK(superseded_by_vintage_id IS NULL OR superseded_by_vintage_id != id),
    CHECK(supersedes_vintage_id IS NULL OR supersedes_vintage_id != id),
    CHECK(parent_vintage_id IS NULL OR parent_vintage_id != id),
    CHECK(is_banking_institution = 0 OR debt_equity IS NULL),

    UNIQUE(exchange, exchange_broadcast_id),
    UNIQUE(company_id, quarter, filing_scope, version_sequence)
);
"""

INDEXES_SQL = [
    """
    CREATE INDEX IF NOT EXISTS idx_vintages_pit_lookup 
    ON quarterly_financial_vintages(company_id, filing_scope, effective_trading_date, quarter);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_vintages_research_eligibility
    ON quarterly_financial_vintages(research_eligibility, company_id, filing_scope);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_vintages_lineage
    ON quarterly_financial_vintages(parent_vintage_id, supersedes_vintage_id, superseded_by_vintage_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_vintages_doc_hash 
    ON quarterly_financial_vintages(source_document_hash);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_vintages_broadcast 
    ON quarterly_financial_vintages(exchange, exchange_broadcast_id);
    """
]

APPEND_ONLY_TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS prevent_vintage_deletion
BEFORE DELETE ON quarterly_financial_vintages
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Illegal deletion: Historical financial vintages are immutable and cannot be deleted.');
END;
"""

DELETE_PROTECTION_TRIGGER_SQL = APPEND_ONLY_TRIGGER_SQL

FINANCIAL_MUTATION_GUARD_SQL = """
CREATE TRIGGER IF NOT EXISTS prevent_vintage_financial_mutation
BEFORE UPDATE ON quarterly_financial_vintages
FOR EACH ROW
BEGIN
    SELECT CASE
        -- Prohibit mutating reported financial figures, timestamps, or core identity
        WHEN (NEW.company_id != OLD.company_id)
          OR (NEW.quarter != OLD.quarter)
          OR (NEW.version_sequence != OLD.version_sequence)
          OR (NEW.filing_scope != OLD.filing_scope)
          OR (NEW.published_at != OLD.published_at)
          OR (NEW.effective_trading_date != OLD.effective_trading_date)
          OR (NEW.revenue != OLD.revenue)
          OR (NEW.net_profit != OLD.net_profit)
          OR (NEW.eps != OLD.eps)
        THEN RAISE(ABORT, 'Illegal mutation: Financial figures and publication timestamps are immutable. Insert a new vintage instead.')
        
        -- Prohibit self-supersession
        WHEN (NEW.superseded_by_vintage_id IS NOT NULL AND NEW.superseded_by_vintage_id = OLD.id)
          OR (NEW.supersedes_vintage_id IS NOT NULL AND NEW.supersedes_vintage_id = OLD.id)
          OR (NEW.parent_vintage_id IS NOT NULL AND NEW.parent_vintage_id = OLD.id)
        THEN RAISE(ABORT, 'Illegal lineage: A vintage cannot reference or supersede itself.')

        -- Prohibit circular lineage
        WHEN (NEW.superseded_by_vintage_id IS NOT NULL AND NEW.superseded_by_vintage_id = OLD.supersedes_vintage_id)
        THEN RAISE(ABORT, 'Illegal circular lineage: A vintage cannot be superseded by the vintage it supersedes.')

        -- Prohibit promoting to VERIFIED_ELIGIBLE without verification_status = VERIFIED
        WHEN (NEW.research_eligibility = 'VERIFIED_ELIGIBLE' AND NEW.verification_status != 'VERIFIED')
        THEN RAISE(ABORT, 'Illegal promotion: Record cannot be VERIFIED_ELIGIBLE without verification_status = VERIFIED.')

        ELSE NULL
    END;
END;
"""

INSERT_CONFLATION_GUARD_SQL = """
CREATE TRIGGER IF NOT EXISTS prevent_extraction_restatement_conflation
BEFORE INSERT ON quarterly_financial_vintages
FOR EACH ROW
BEGIN
    SELECT CASE
        -- Prohibit semantic conflation of internal fixes with corporate restatements
        WHEN NEW.internal_revision_type IN ('EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION')
         AND NEW.company_filing_type = 'CORPORATE_RESTATEMENT'
        THEN RAISE(ABORT, 'Semantic Conflation Error: Internal pipeline revisions cannot populate company_filing_type as CORPORATE_RESTATEMENT.')
        
        -- Prohibit inserting as VERIFIED_ELIGIBLE without verification_status = VERIFIED
        WHEN NEW.research_eligibility = 'VERIFIED_ELIGIBLE' AND NEW.verification_status != 'VERIFIED'
        THEN RAISE(ABORT, 'Integrity Error: Cannot insert VERIFIED_ELIGIBLE vintage without verification_status = VERIFIED.')
        
        -- Prohibit self-supersession
        WHEN NEW.superseded_by_vintage_id IS NOT NULL AND NEW.superseded_by_vintage_id = NEW.id
        THEN RAISE(ABORT, 'Lineage Error: A vintage cannot supersede itself.')
        
        ELSE NULL
    END;
END;
"""


def verify_target_database(target_path: Path) -> Path:
    """Ensure the target database is strictly staging, never production."""
    resolved = target_path.resolve()
    if resolved == PRODUCTION_DATABASE_PATH:
        raise ValueError(f"CRITICAL SAFETY VIOLATION: Attempted to run staging migration on PRODUCTION: {resolved}")
    if resolved.name != "staging_financial_expansion.db":
        raise ValueError(f"CRITICAL SAFETY VIOLATION: Target database must be staging_financial_expansion.db, got: {resolved.name}")
    if not resolved.exists():
        raise FileNotFoundError(f"Target staging database does not exist: {resolved}")
    return resolved


def run_migration(db_path: Path = STAGING_DATABASE_PATH) -> bool:
    """
    Run Phase P2.6 schema migration on target staging database.
    Preserves all existing records, establishes the 4D classification schema,
    5-timestamp tracking model, and bidirectional lineage links.
    Idempotent across fresh, unmigrated, or already migrated databases.
    """
    target = verify_target_database(db_path)
    print(f"Applying Phase P2.6 financial vintage classification & lineage migration to: {target}")

    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Step 1: Check if table exists
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='quarterly_financial_vintages';")
        table_exists = cursor.fetchone()[0] > 0

        if not table_exists:
            cursor.execute(VINTAGES_TABLE_SQL)
            for idx_sql in INDEXES_SQL:
                cursor.execute(idx_sql)
            cursor.execute(APPEND_ONLY_TRIGGER_SQL)
            cursor.execute(FINANCIAL_MUTATION_GUARD_SQL)
            cursor.execute(INSERT_CONFLATION_GUARD_SQL)
            conn.commit()
            print("[OK] Fresh schema initialized.")
            return True

        # Step 2: Check if already migrated
        cursor.execute("PRAGMA table_info(quarterly_financial_vintages);")
        columns = [r["name"] for r in cursor.fetchall()]

        if "company_filing_type" in columns:
            # Table already has new schema; ensure indexes and triggers exist
            for idx_sql in INDEXES_SQL:
                cursor.execute(idx_sql)
            cursor.execute(APPEND_ONLY_TRIGGER_SQL)
            cursor.execute(FINANCIAL_MUTATION_GUARD_SQL)
            cursor.execute(INSERT_CONFLATION_GUARD_SQL)
            conn.commit()
            print("[OK] Schema already migrated (idempotent pass).")
            return True

        # Step 3: Read existing rows from old table
        cursor.execute("SELECT * FROM quarterly_financial_vintages ORDER BY id ASC")
        existing_rows = [dict(r) for r in cursor.fetchall()]
        print(f"Found {len(existing_rows)} existing financial vintages to migrate.")

        # Step 4: Disable foreign keys temporarily during table recreation
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Step 5: Create v2 table with new schema
        temp_table_sql = VINTAGES_TABLE_SQL.replace(
            "CREATE TABLE IF NOT EXISTS quarterly_financial_vintages",
            "CREATE TABLE quarterly_financial_vintages_v2"
        )
        cursor.execute(temp_table_sql)
        
        # Step 6: Map and insert existing rows
        insert_sql = """
        INSERT INTO quarterly_financial_vintages_v2 (
            id, company_id, quarter, period_start_date, period_end_date,
            accounting_standard, filing_scope, company_filing_type, internal_revision_type,
            verification_status, research_eligibility, version_sequence, parent_vintage_id,
            supersedes_vintage_id, superseded_by_vintage_id, revision_reason, revision_source,
            lineage_created_at, exchange, exchange_broadcast_id, original_broadcast_id,
            published_at, effective_trading_date, ingested_at, internally_corrected_at,
            company_revision_published_at, revenue, revenue_from_operations, gross_revenue,
            total_income, operating_expenses, operating_profit, net_profit, eps,
            is_banking_institution, net_interest_income, customer_deposits, capital_adequacy_ratio,
            gross_npa_pct, net_npa_pct, total_assets, total_equity, total_debt,
            current_liabilities, roe, roce, debt_equity, operating_margin, net_margin,
            source_document_url, source_document_hash, verification_notes,
            remediation_type, remediation_notes, created_at
        ) VALUES (
            :id, :company_id, :quarter, :period_start_date, :period_end_date,
            :accounting_standard, :filing_scope, :company_filing_type, :internal_revision_type,
            :verification_status, :research_eligibility, :version_sequence, :parent_vintage_id,
            :supersedes_vintage_id, :superseded_by_vintage_id, :revision_reason, :revision_source,
            :lineage_created_at, :exchange, :exchange_broadcast_id, :original_broadcast_id,
            :published_at, :effective_trading_date, :ingested_at, :internally_corrected_at,
            :company_revision_published_at, :revenue, :revenue_from_operations, :gross_revenue,
            :total_income, :operating_expenses, :operating_profit, :net_profit, :eps,
            :is_banking_institution, :net_interest_income, :customer_deposits, :capital_adequacy_ratio,
            :gross_npa_pct, :net_npa_pct, :total_assets, :total_equity, :total_debt,
            :current_liabilities, :roe, :roce, :debt_equity, :operating_margin, :net_margin,
            :source_document_url, :source_document_hash, :verification_notes,
            :remediation_type, :remediation_notes, :created_at
        )
        """
        
        for r in existing_rows:
            row_id = r["id"]
            comp_filing_type = "ORIGINAL"
            
            if row_id in (1, 2, 3, 4):  # TCS & INFY
                int_rev_type = "INITIAL_INGESTION"
                ver_status = "PROVISIONAL"
                res_elig = "PROVISIONAL_DEMO"
                parent_id = None
                supersedes_id = None
                superseded_by = None
                corr_at = None
                rev_reason = "Phase P2.5 initial pilot ingestion (mock document fixture)"
                rev_source = "P2.5 Pilot Pipeline"
                is_bank = 0
                rem_type = "ORIGINAL_PILOT"
            elif row_id in (5, 6, 9, 10):  # RELIANCE & ADANIENT Pilot
                int_rev_type = "INITIAL_INGESTION"
                ver_status = "REJECTED"
                res_elig = "SUPERSEDED"
                parent_id = None
                supersedes_id = None
                superseded_by = r.get("superseded_by_vintage_id")
                corr_at = None
                rev_reason = "Pilot extraction flawed; superseded by extraction remediation"
                rev_source = "P2.5 Pilot Pipeline"
                is_bank = 0
                rem_type = "ORIGINAL_PILOT"
            elif row_id in (7, 8):  # HDFCBANK Pilot
                int_rev_type = "INITIAL_INGESTION"
                ver_status = "REJECTED"
                res_elig = "SUPERSEDED"
                parent_id = None
                supersedes_id = None
                superseded_by = r.get("superseded_by_vintage_id")
                corr_at = None
                rev_reason = "Pilot extraction flawed; corporate D/E applied to commercial bank"
                rev_source = "P2.5 Pilot Pipeline"
                is_bank = 1
                rem_type = "ORIGINAL_PILOT"
            elif row_id in (11, 12):  # RELIANCE Remediation
                int_rev_type = "EXTRACTION_CORRECTION"
                ver_status = "PROVISIONAL"
                res_elig = "PROVISIONAL_DEMO"
                parent_id = 5 if row_id == 11 else 6
                supersedes_id = 5 if row_id == 11 else 6
                superseded_by = None
                corr_at = "2026-11-04 16:20:00"
                rev_reason = "Normalized Revenue from Operations vs Gross Turnover"
                rev_source = "P2.5.2 Remediation Pipeline"
                is_bank = 0
                rem_type = "INTERNAL_EXTRACTION_CORRECTION"
            elif row_id in (13, 14):  # ADANIENT Remediation
                int_rev_type = "EXTRACTION_CORRECTION"
                ver_status = "PROVISIONAL"
                res_elig = "PROVISIONAL_DEMO"
                parent_id = 9 if row_id == 13 else 10
                supersedes_id = 9 if row_id == 13 else 10
                superseded_by = None
                corr_at = "2026-11-04 16:20:00"
                rev_reason = "Normalized Revenue from Operations vs Total Income (other income separated)"
                rev_source = "P2.5.2 Remediation Pipeline"
                is_bank = 0
                rem_type = "INTERNAL_EXTRACTION_CORRECTION"
            elif row_id in (15, 16):  # HDFCBANK Consolidated Remediation
                int_rev_type = "SCOPE_REALIGNMENT"
                ver_status = "REJECTED"
                res_elig = "QUARANTINED"
                parent_id = 7 if row_id == 15 else 8
                supersedes_id = 7 if row_id == 15 else 8
                superseded_by = None
                corr_at = "2026-11-04 16:20:00"
                rev_reason = "Quarantined: Q1 retains standalone top-line; Q2 copies standalone NII/NPA"
                rev_source = "P2.5.3 Audit Defect Finding"
                is_bank = 1
                rem_type = "SECTOR_BANKING_METRICS_REMEDIATION" if row_id == 15 else "SCOPE_ALIGNMENT_CORRECTION"
            elif row_id == 17:  # HDFCBANK Standalone Q2
                int_rev_type = "INITIAL_INGESTION"
                ver_status = "PROVISIONAL"
                res_elig = "PROVISIONAL_DEMO"
                parent_id = None
                supersedes_id = None
                superseded_by = None
                corr_at = None
                rev_reason = "Standalone banking disclosure isolated"
                rev_source = "P2.5.2 Remediation Pipeline"
                is_bank = 1
                rem_type = "ORIGINAL_PILOT"
            else:
                int_rev_type = "INITIAL_INGESTION"
                ver_status = r.get("verification_status", "PROVISIONAL")
                res_elig = "PROVISIONAL_DEMO"
                parent_id = None
                supersedes_id = None
                superseded_by = r.get("superseded_by_vintage_id")
                corr_at = None
                rev_reason = "Migrated vintage"
                rev_source = "Migration"
                is_bank = 0
                rem_type = "ORIGINAL_PILOT"

            payload = {
                "id": row_id,
                "company_id": r["company_id"],
                "quarter": r["quarter"],
                "period_start_date": r["period_start_date"],
                "period_end_date": r["period_end_date"],
                "accounting_standard": r["accounting_standard"],
                "filing_scope": r["filing_scope"],
                "company_filing_type": comp_filing_type,
                "internal_revision_type": int_rev_type,
                "verification_status": ver_status,
                "research_eligibility": res_elig,
                "version_sequence": r["version_sequence"],
                "parent_vintage_id": parent_id,
                "supersedes_vintage_id": supersedes_id,
                "superseded_by_vintage_id": superseded_by,
                "revision_reason": rev_reason,
                "revision_source": rev_source,
                "lineage_created_at": r["created_at"],
                "exchange": r["exchange"],
                "exchange_broadcast_id": r["exchange_broadcast_id"],
                "original_broadcast_id": r.get("original_broadcast_id"),
                "published_at": r.get("published_at") or r.get("publication_timestamp"),
                "effective_trading_date": r["effective_trading_date"],
                "ingested_at": r.get("ingested_at") or r.get("created_at"),
                "internally_corrected_at": corr_at,
                "company_revision_published_at": None,
                "revenue": r["revenue"],
                "revenue_from_operations": r.get("revenue_from_operations"),
                "gross_revenue": r.get("gross_revenue"),
                "total_income": r.get("total_income"),
                "operating_expenses": r["operating_expenses"],
                "operating_profit": r["operating_profit"],
                "net_profit": r["net_profit"],
                "eps": r["eps"],
                "is_banking_institution": is_bank,
                "net_interest_income": r.get("net_interest_income"),
                "customer_deposits": r.get("customer_deposits"),
                "capital_adequacy_ratio": r.get("capital_adequacy_ratio"),
                "gross_npa_pct": r.get("gross_npa_pct"),
                "net_npa_pct": r.get("net_npa_pct"),
                "total_assets": r["total_assets"],
                "total_equity": r["total_equity"],
                "total_debt": None if is_bank else r["total_debt"],
                "current_liabilities": r["current_liabilities"],
                "roe": r["roe"],
                "roce": None if is_bank else r["roce"],
                "debt_equity": None if is_bank else r["debt_equity"],
                "operating_margin": r["operating_margin"],
                "net_margin": r["net_margin"],
                "source_document_url": r["source_document_url"],
                "source_document_hash": r["source_document_hash"],
                "verification_notes": r["verification_notes"],
                "remediation_type": r.get("remediation_type") or rem_type,
                "remediation_notes": r.get("remediation_notes"),
                "created_at": r["created_at"]
            }
            cursor.execute(insert_sql, payload)

        # Step 7: Replace table
        cursor.execute("DROP TRIGGER IF EXISTS prevent_vintage_mutation;")
        cursor.execute("DROP TRIGGER IF EXISTS prevent_vintage_deletion;")
        cursor.execute("DROP TABLE quarterly_financial_vintages;")
        cursor.execute("ALTER TABLE quarterly_financial_vintages_v2 RENAME TO quarterly_financial_vintages;")

        # Step 8: Create indexes
        for idx_sql in INDEXES_SQL:
            cursor.execute(idx_sql)

        # Step 9: Create triggers
        cursor.execute(APPEND_ONLY_TRIGGER_SQL)
        cursor.execute(FINANCIAL_MUTATION_GUARD_SQL)
        cursor.execute(INSERT_CONFLATION_GUARD_SQL)

        # Step 10: Re-enable foreign keys & verify row count
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("SELECT COUNT(*) FROM quarterly_financial_vintages;")
        migrated_count = cursor.fetchone()[0]
        if migrated_count != len(existing_rows):
            raise ValueError(f"Migration count mismatch: expected {len(existing_rows)}, got {migrated_count}")

        conn.commit()
        print(f"[OK] Phase P2.6 migration successfully applied. All {migrated_count} vintages migrated and verified.")
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
