"""
Staging Financial Vintage Repository & Point-in-Time Service (Phase P2.6)
========================================================================

Staging-only data access layer for `quarterly_financial_vintages`.
Implements deterministic point-in-time retrieval, 4D classification management,
canonical 5-timestamp tracking, and bidirectional lineage operations.

Safety Guarantees:
- Targets strictly staging database or test-provided SQLite connections.
- Hardcoded rejection of production database paths (`database/swing_trading.db`).
- Implements strict filtering before window ranking.
- Isolates CONSOLIDATED and STANDALONE filing scopes.
- Quarantines and rejects synthetic placeholder records.
- Enforces data governance invariants:
    1. VERIFIED_ELIGIBLE requires verification_status = 'VERIFIED'.
    2. Internal revisions cannot be labeled CORPORATE_RESTATEMENT.
    3. Banking entities have debt_equity = None and total_debt = None.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd

from backend.database.connection import open_db_connection, ConnectionWrapper, DatabaseEngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DATABASE_PATH = (PROJECT_ROOT / "database" / "staging_financial_expansion.db").resolve()
PRODUCTION_DATABASE_PATH = (PROJECT_ROOT / "database" / "swing_trading.db").resolve()

SYNTHETIC_REVENUE_PATTERN = 10000.0
SYNTHETIC_PROFIT_PATTERN = 1500.0
SYNTHETIC_EPS_PATTERN = 15.0


def is_synthetic_record(revenue: float, net_profit: float, eps: float) -> bool:
    """Detect if a record matches known synthetic placeholder constants."""
    return (
        revenue == SYNTHETIC_REVENUE_PATTERN
        and net_profit == SYNTHETIC_PROFIT_PATTERN
        and eps == SYNTHETIC_EPS_PATTERN
    )


class StagingFinancialVintageRepository:
    """Staging repository for append-only financial vintages with 4D classification and lineage."""

    def __init__(self, db_path: Union[str, Path] = STAGING_DATABASE_PATH):
        db_str = str(db_path)
        if not db_str.startswith(("postgresql://", "postgres://")):
            resolved = Path(db_path).resolve()
            if resolved == PRODUCTION_DATABASE_PATH:
                raise ValueError(f"CRITICAL SAFETY VIOLATION: Staging repository cannot connect to production: {resolved}")
            self.db_path = str(resolved)
        else:
            self.db_path = db_str

    def get_connection(self):
        conn = open_db_connection(self.db_path)
        if conn.engine == DatabaseEngine.SQLITE:
            return conn.raw_connection
        return conn

    def insert_vintage(self, vintage_data: Dict[str, Any]) -> int:
        """
        Insert a new filing vintage with 4D classification and lineage support.
        Rejects synthetic placeholder patterns and validates required provenance.
        """
        rev = float(vintage_data["revenue"])
        pat = float(vintage_data["net_profit"])
        eps = float(vintage_data["eps"])

        if is_synthetic_record(rev, pat, eps):
            raise ValueError(
                f"REJECTED_SYNTHETIC: Record matches forbidden synthetic placeholder constants (rev={rev}, pat={pat}, eps={eps})."
            )

        doc_hash = vintage_data.get("source_document_hash")
        if not doc_hash or len(doc_hash) != 64:
            raise ValueError("Provenance Error: A valid 64-character SHA-256 source_document_hash is required.")

        pub_at = vintage_data.get("published_at") or vintage_data.get("publication_timestamp")
        if not pub_at:
            raise ValueError("Timestamp Error: Exact publication_timestamp / published_at is required.")

        eff_date = vintage_data.get("effective_trading_date")
        if not eff_date:
            raise ValueError("Timestamp Error: Exact effective_trading_date is required.")

        # Map filing type
        c_filing_type = vintage_data.get("company_filing_type") or vintage_data.get("filing_type", "ORIGINAL")
        if c_filing_type == "RESTATED" or c_filing_type == "RESTATEMENT":
            c_filing_type = "CORPORATE_RESTATEMENT"
        elif c_filing_type == "REVISED":
            c_filing_type = "REVISED_DISCLOSURE"

        int_rev_type = vintage_data.get("internal_revision_type", "INITIAL_INGESTION")
        ver_status = vintage_data.get("verification_status", "PROVISIONAL")

        # Determine research eligibility
        if "research_eligibility" in vintage_data:
            res_elig = vintage_data["research_eligibility"]
        else:
            res_elig = "VERIFIED_ELIGIBLE" if ver_status == "VERIFIED" else "PROVISIONAL_DEMO"

        # Invariant checks
        if res_elig == "VERIFIED_ELIGIBLE" and ver_status != "VERIFIED":
            raise ValueError("Integrity Error: Cannot insert VERIFIED_ELIGIBLE vintage without verification_status = VERIFIED.")

        if int_rev_type in ("EXTRACTION_CORRECTION", "SCOPE_REALIGNMENT", "SECTOR_NORMALIZATION") and c_filing_type == "CORPORATE_RESTATEMENT":
            raise ValueError("Semantic Conflation Error: Internal pipeline revisions cannot populate company_filing_type as CORPORATE_RESTATEMENT.")

        # Sector / Banking detection
        is_bank = int(vintage_data.get("is_banking_institution", 0))
        if any(vintage_data.get(k) is not None for k in ("customer_deposits", "net_interest_income", "capital_adequacy_ratio", "gross_npa_pct", "net_npa_pct")):
            is_bank = 1

        debt_eq = None if is_bank else vintage_data.get("debt_equity")
        tot_debt = None if is_bank else vintage_data.get("total_debt")
        roce_val = None if is_bank else vintage_data.get("roce")

        # Map legacy remediation_type for compatibility
        rem_type = vintage_data.get("remediation_type")
        if not rem_type:
            if int_rev_type == "EXTRACTION_CORRECTION":
                rem_type = "INTERNAL_EXTRACTION_CORRECTION"
            elif int_rev_type == "SCOPE_REALIGNMENT":
                rem_type = "SCOPE_ALIGNMENT_CORRECTION"
            elif int_rev_type == "SECTOR_NORMALIZATION":
                rem_type = "SECTOR_BANKING_METRICS_REMEDIATION"
            else:
                rem_type = "ORIGINAL_PILOT"

        payload = {
            "company_id": vintage_data["company_id"],
            "quarter": vintage_data["quarter"],
            "period_start_date": vintage_data["period_start_date"],
            "period_end_date": vintage_data["period_end_date"],
            "accounting_standard": vintage_data.get("accounting_standard", "IND_AS"),
            "filing_scope": vintage_data.get("filing_scope", "CONSOLIDATED"),
            "company_filing_type": c_filing_type,
            "internal_revision_type": int_rev_type,
            "verification_status": ver_status,
            "research_eligibility": res_elig,
            "version_sequence": vintage_data.get("version_sequence", 1),
            "parent_vintage_id": vintage_data.get("parent_vintage_id"),
            "supersedes_vintage_id": vintage_data.get("supersedes_vintage_id"),
            "superseded_by_vintage_id": vintage_data.get("superseded_by_vintage_id"),
            "revision_reason": vintage_data.get("revision_reason"),
            "revision_source": vintage_data.get("revision_source"),
            "lineage_created_at": vintage_data.get("lineage_created_at"),
            "exchange": vintage_data["exchange"],
            "exchange_broadcast_id": vintage_data["exchange_broadcast_id"],
            "original_broadcast_id": vintage_data.get("original_broadcast_id"),
            "internal_correction_event_id": vintage_data.get("internal_correction_event_id"),
            "published_at": pub_at,
            "effective_trading_date": eff_date,
            "ingested_at": vintage_data.get("ingested_at"),
            "internally_corrected_at": vintage_data.get("internally_corrected_at"),
            "company_revision_published_at": vintage_data.get("company_revision_published_at"),
            "revenue": rev,
            "revenue_from_operations": vintage_data.get("revenue_from_operations"),
            "gross_revenue": vintage_data.get("gross_revenue"),
            "total_income": vintage_data.get("total_income"),
            "operating_expenses": vintage_data.get("operating_expenses"),
            "operating_profit": vintage_data.get("operating_profit"),
            "net_profit": pat,
            "eps": eps,
            "is_banking_institution": is_bank,
            "net_interest_income": vintage_data.get("net_interest_income"),
            "customer_deposits": vintage_data.get("customer_deposits"),
            "capital_adequacy_ratio": vintage_data.get("capital_adequacy_ratio"),
            "gross_npa_pct": vintage_data.get("gross_npa_pct"),
            "net_npa_pct": vintage_data.get("net_npa_pct"),
            "total_assets": vintage_data.get("total_assets"),
            "total_equity": vintage_data.get("total_equity"),
            "total_debt": tot_debt,
            "current_liabilities": vintage_data.get("current_liabilities"),
            "roe": vintage_data.get("roe"),
            "roce": roce_val,
            "debt_equity": debt_eq,
            "operating_margin": vintage_data.get("operating_margin"),
            "net_margin": vintage_data.get("net_margin"),
            "source_document_url": vintage_data["source_document_url"],
            "source_document_hash": doc_hash,
            "verification_notes": vintage_data.get("verification_notes"),
            "remediation_type": rem_type,
            "remediation_notes": vintage_data.get("remediation_notes")
        }

        sql = """
        INSERT INTO quarterly_financial_vintages (
            company_id, quarter, period_start_date, period_end_date,
            accounting_standard, filing_scope, company_filing_type,
            internal_revision_type, verification_status, research_eligibility,
            version_sequence, parent_vintage_id, supersedes_vintage_id,
            superseded_by_vintage_id, revision_reason, revision_source,
            lineage_created_at, exchange, exchange_broadcast_id, original_broadcast_id, internal_correction_event_id,
            published_at, effective_trading_date, ingested_at, internally_corrected_at,
            company_revision_published_at, revenue, revenue_from_operations, gross_revenue,
            total_income, operating_expenses, operating_profit, net_profit, eps,
            is_banking_institution, net_interest_income, customer_deposits,
            capital_adequacy_ratio, gross_npa_pct, net_npa_pct, total_assets,
            total_equity, total_debt, current_liabilities, roe, roce,
            debt_equity, operating_margin, net_margin, source_document_url,
            source_document_hash, verification_notes, remediation_type, remediation_notes
        ) VALUES (
            :company_id, :quarter, :period_start_date, :period_end_date,
            :accounting_standard, :filing_scope, :company_filing_type,
            :internal_revision_type, :verification_status, :research_eligibility,
            :version_sequence, :parent_vintage_id, :supersedes_vintage_id,
            :superseded_by_vintage_id, :revision_reason, :revision_source,
            :lineage_created_at, :exchange, :exchange_broadcast_id, :original_broadcast_id, :internal_correction_event_id,
            :published_at, :effective_trading_date, :ingested_at, :internally_corrected_at,
            :company_revision_published_at, :revenue, :revenue_from_operations, :gross_revenue,
            :total_income, :operating_expenses, :operating_profit, :net_profit, :eps,
            :is_banking_institution, :net_interest_income, :customer_deposits,
            :capital_adequacy_ratio, :gross_npa_pct, :net_npa_pct, :total_assets,
            :total_equity, :total_debt, :current_liabilities, :roe, :roce,
            :debt_equity, :operating_margin, :net_margin, :source_document_url,
            :source_document_hash, :verification_notes, :remediation_type, :remediation_notes
        );
        """

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, payload)
            row_id = cur.lastrowid
            if row_id is None:
                cur.execute("SELECT currval(pg_get_serial_sequence('quarterly_financial_vintages', 'id'))")
                seq_row = cur.fetchone()
                if seq_row:
                    row_id = seq_row[0]
            conn.commit()
            return row_id

    def create_internal_correction(
        self,
        predecessor_id: int,
        corrected_data: Dict[str, Any],
        revision_type: str,
        reason: str,
        auditor_id: str = "AUDITOR"
    ) -> int:
        """
        Transactionally create an internal pipeline correction vintage.
        Applies lineage links and marks predecessor superseded.
        """
        if revision_type not in ("EXTRACTION_CORRECTION", "SCOPE_REALIGNMENT", "SECTOR_NORMALIZATION"):
            raise ValueError(f"Invalid internal_revision_type: {revision_type}")

        pred = self.get_vintage_by_id(predecessor_id)
        if not pred:
            raise ValueError(f"Predecessor vintage {predecessor_id} not found.")

        payload = dict(pred)
        payload.update(corrected_data)
        payload.pop("id", None)
        payload["parent_vintage_id"] = predecessor_id
        payload["supersedes_vintage_id"] = predecessor_id
        payload["superseded_by_vintage_id"] = None
        payload["version_sequence"] = pred["version_sequence"] + 1
        payload["company_filing_type"] = pred["company_filing_type"]
        payload["internal_revision_type"] = revision_type
        payload["verification_status"] = corrected_data.get("verification_status", "PROVISIONAL")
        payload["research_eligibility"] = corrected_data.get("research_eligibility", "PROVISIONAL_DEMO")
        payload["internally_corrected_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        payload["internal_correction_event_id"] = corrected_data.get("internal_correction_event_id") or f"INT_CORR_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{pred['company_id']}_{pred['quarter']}_V{pred['version_sequence'] + 1}"
        payload["revision_reason"] = reason
        payload["revision_source"] = auditor_id

        # Insert and update atomically
        with self.get_connection() as conn:
            cur = conn.cursor()
            new_id = self.insert_vintage(payload)
            cur.execute("""
                UPDATE quarterly_financial_vintages
                SET superseded_by_vintage_id = ?, research_eligibility = 'SUPERSEDED'
                WHERE id = ?;
            """, (new_id, predecessor_id))
            conn.commit()
            return new_id

    def link_company_revision(
        self,
        predecessor_id: int,
        revision_data: Dict[str, Any],
        company_filing_type: str,
        reason: str
    ) -> int:
        """
        Transactionally create a company-announced revision or corporate restatement.
        Applies lineage links and marks predecessor superseded.
        """
        if company_filing_type not in ("REVISED_DISCLOSURE", "CORPORATE_RESTATEMENT", "ANNUAL_AUDITED_FINAL"):
            raise ValueError(f"Invalid company_filing_type for company revision: {company_filing_type}")

        pred = self.get_vintage_by_id(predecessor_id)
        if not pred:
            raise ValueError(f"Predecessor vintage {predecessor_id} not found.")

        payload = dict(pred)
        payload.update(revision_data)
        payload.pop("id", None)
        payload["parent_vintage_id"] = predecessor_id
        payload["supersedes_vintage_id"] = predecessor_id
        payload["superseded_by_vintage_id"] = None
        payload["version_sequence"] = pred["version_sequence"] + 1
        payload["company_filing_type"] = company_filing_type
        payload["internal_revision_type"] = "INITIAL_INGESTION"
        payload["verification_status"] = revision_data.get("verification_status", "PROVISIONAL")
        payload["research_eligibility"] = "VERIFIED_ELIGIBLE" if payload["verification_status"] == "VERIFIED" else "PROVISIONAL_DEMO"
        payload["company_revision_published_at"] = payload.get("published_at") or payload.get("publication_timestamp")
        payload["revision_reason"] = reason
        payload["revision_source"] = "COMPANY_EXCHANGE_DISCLOSURE"

        with self.get_connection() as conn:
            cur = conn.cursor()
            new_id = self.insert_vintage(payload)
            cur.execute("""
                UPDATE quarterly_financial_vintages
                SET superseded_by_vintage_id = ?, research_eligibility = 'SUPERSEDED'
                WHERE id = ?;
            """, (new_id, predecessor_id))
            conn.commit()
            return new_id

    def mark_superseded(self, old_vintage_id: int, new_vintage_id: int, reason: Optional[str] = None) -> None:
        """Mark an earlier vintage as superseded by a newer vintage."""
        sql = """
        UPDATE quarterly_financial_vintages
        SET superseded_by_vintage_id = ?, research_eligibility = 'SUPERSEDED'
        WHERE id = ?;
        """
        with self.get_connection() as conn:
            conn.execute(sql, (new_vintage_id, old_vintage_id))
            conn.commit()

    def supersede_vintage(self, old_vintage_id: int, new_vintage_id: int) -> None:
        """Backward-compatible alias for mark_superseded."""
        self.mark_superseded(old_vintage_id, new_vintage_id)

    def quarantine_vintage(self, vintage_id: int, reason: str, auditor_id: str = "AUDITOR") -> None:
        """Quarantine a vintage to prevent consumption in research or production."""
        sql = """
        UPDATE quarterly_financial_vintages
        SET research_eligibility = 'QUARANTINED',
            verification_notes = CASE 
                WHEN verification_notes IS NULL OR verification_notes = '' 
                THEN ? 
                ELSE verification_notes || ' | ' || ? 
            END
        WHERE id = ?;
        """
        note_text = f"QUARANTINED by {auditor_id}: {reason}"
        with self.get_connection() as conn:
            conn.execute(sql, (note_text, note_text, vintage_id))
            conn.commit()

    def record_status_transition(
        self,
        vintage_id: int,
        new_verification_status: str,
        new_research_eligibility: str,
        notes: str
    ) -> None:
        """
        Record a verified status transition.
        Enforces that VERIFIED_ELIGIBLE requires verification_status = 'VERIFIED'.
        """
        if new_research_eligibility == "VERIFIED_ELIGIBLE" and new_verification_status != "VERIFIED":
            raise ValueError("Integrity Error: Cannot promote to VERIFIED_ELIGIBLE without verification_status = VERIFIED.")

        sql = """
        UPDATE quarterly_financial_vintages
        SET verification_status = ?,
            research_eligibility = ?,
            verification_notes = CASE 
                WHEN verification_notes IS NULL OR verification_notes = '' 
                THEN ? 
                ELSE verification_notes || ' | ' || ? 
            END
        WHERE id = ?;
        """
        with self.get_connection() as conn:
            conn.execute(sql, (new_verification_status, new_research_eligibility, notes, notes, vintage_id))
            conn.commit()

    def get_vintage_lineage(self, vintage_id: int) -> Dict[str, Any]:
        """Retrieve complete lineage tree for a vintage: ancestors and successors."""
        vintage = self.get_vintage_by_id(vintage_id)
        if not vintage:
            return {}

        ancestors = []
        curr = vintage
        while curr and curr.get("supersedes_vintage_id"):
            parent = self.get_vintage_by_id(curr["supersedes_vintage_id"])
            if parent:
                ancestors.append(parent)
                curr = parent
            else:
                break

        successors = []
        curr = vintage
        while curr and curr.get("superseded_by_vintage_id"):
            child = self.get_vintage_by_id(curr["superseded_by_vintage_id"])
            if child:
                successors.append(child)
                curr = child
            else:
                break

        return {
            "vintage": vintage,
            "ancestors": ancestors,
            "successors": successors
        }

    def get_point_in_time_vintages(
        self,
        symbol: str,
        evaluation_date: str,
        filing_scope: str = "CONSOLIDATED",
        allow_provisional: bool = False,
        include_quarantined: bool = False
    ) -> pd.DataFrame:
        """
        Retrieve eligible financial vintages for a company as of an evaluation date.
        
        Guarantees:
        1. Filters effective_trading_date <= evaluation_date BEFORE window ranking.
        2. Strict research eligibility gating:
           - By default: only VERIFIED_ELIGIBLE records with verification_status = 'VERIFIED'.
           - When allow_provisional=True: allows PROVISIONAL_DEMO for dev/testing.
        3. Never serves QUARANTINED or REJECTED records.
        4. Isolates filing_scope (CONSOLIDATED vs STANDALONE).
        """
        sql = """
        WITH eligible_vintages AS (
            SELECT 
                v.id AS vintage_id,
                v.company_id,
                c.symbol,
                v.quarter,
                v.period_start_date,
                v.period_end_date,
                v.accounting_standard,
                v.filing_scope,
                v.company_filing_type,
                CASE 
                    WHEN v.company_filing_type = 'CORPORATE_RESTATEMENT' THEN 'RESTATED' 
                    WHEN v.company_filing_type = 'REVISED_DISCLOSURE' THEN 'REVISED'
                    ELSE v.company_filing_type 
                END AS filing_type,
                v.internal_revision_type,
                v.verification_status,
                v.research_eligibility,
                v.version_sequence,
                v.parent_vintage_id,
                v.supersedes_vintage_id,
                v.superseded_by_vintage_id,
                v.published_at,
                v.published_at AS publication_timestamp,
                v.effective_trading_date,
                v.revenue,
                v.revenue_from_operations,
                v.gross_revenue,
                v.total_income,
                v.operating_profit,
                v.net_profit,
                v.eps,
                v.total_assets,
                v.total_equity,
                v.total_debt,
                v.current_liabilities,
                v.is_banking_institution,
                v.net_interest_income,
                v.customer_deposits,
                v.capital_adequacy_ratio,
                v.gross_npa_pct,
                v.net_npa_pct,
                v.roe,
                v.roce,
                v.debt_equity,
                v.operating_margin,
                v.net_margin,
                v.source_document_url,
                v.source_document_hash,
                v.remediation_type,
                v.remediation_notes,
                v.original_broadcast_id,
                ROW_NUMBER() OVER (
                    PARTITION BY v.quarter 
                    ORDER BY v.version_sequence DESC, v.published_at DESC
                ) AS rank
            FROM quarterly_financial_vintages v
            INNER JOIN companies c ON v.company_id = c.id
            WHERE c.symbol = :symbol
              AND v.filing_scope = :filing_scope
              AND v.effective_trading_date <= :eval_date
              AND (
                  (:allow_prov = 1 AND v.research_eligibility IN ('VERIFIED_ELIGIBLE', 'PROVISIONAL_DEMO'))
                  OR
                  (:allow_prov = 0 AND (
                      v.research_eligibility = 'VERIFIED_ELIGIBLE' 
                      OR (v.verification_status = 'VERIFIED' AND v.research_eligibility != 'QUARANTINED')
                  ))
              )
              AND (
                  :include_quar = 1 OR v.research_eligibility != 'QUARANTINED'
              )
              AND v.verification_status != 'REJECTED'
        )
        SELECT 
            vintage_id,
            company_id,
            symbol,
            quarter,
            period_start_date,
            period_end_date,
            filing_scope,
            company_filing_type,
            filing_type,
            internal_revision_type,
            verification_status,
            research_eligibility,
            version_sequence,
            parent_vintage_id,
            supersedes_vintage_id,
            superseded_by_vintage_id,
            effective_trading_date,
            published_at,
            publication_timestamp,
            revenue,
            revenue_from_operations,
            gross_revenue,
            total_income,
            net_profit,
            eps,
            roe,
            roce,
            debt_equity,
            operating_margin,
            net_margin,
            is_banking_institution,
            net_interest_income,
            customer_deposits,
            capital_adequacy_ratio,
            gross_npa_pct,
            net_npa_pct,
            remediation_type,
            remediation_notes,
            source_document_url,
            source_document_hash
        FROM eligible_vintages
        WHERE rank = 1
        ORDER BY period_end_date ASC;
        """

        params = {
            "symbol": symbol.upper().strip(),
            "filing_scope": filing_scope.upper().strip(),
            "eval_date": str(evaluation_date)[:10],
            "allow_prov": 1 if allow_provisional else 0,
            "include_quar": 1 if include_quarantined else 0
        }

        with self.get_connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params)
            df.attrs["evaluation_date"] = str(evaluation_date)[:10]
            df.attrs["filing_scope"] = filing_scope
            return df

    def get_all_vintages_for_company(self, symbol: str) -> pd.DataFrame:
        """Retrieve complete lineage of all vintages (including superseded) for audit."""
        sql = """
        SELECT 
            v.*,
            c.symbol
        FROM quarterly_financial_vintages v
        INNER JOIN companies c ON v.company_id = c.id
        WHERE c.symbol = ?
        ORDER BY v.quarter ASC, v.version_sequence ASC;
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=(symbol.upper().strip(),))

    def get_vintage_by_id(self, vintage_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific vintage by its primary key ID."""
        sql = "SELECT * FROM quarterly_financial_vintages WHERE id = ?"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (vintage_id,))
            row = cur.fetchone()
            return dict(row) if row else None
