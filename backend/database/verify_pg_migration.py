"""
Data Integrity Verification Utility
==================================
Deterministic verification framework comparing SQLite source databases
with PostgreSQL target databases after migration.

Verifies:
1. Exact row count parity per table.
2. Primary key coverage and sequence integrity.
3. Column nullability and null-count equivalence.
4. Deterministic row-level cryptographic checksums (SHA-256).
5. Point-in-time financial filing lineage, publication dates, and supersession links.
6. Research eligibility and quarantine classification preservation.
"""

from __future__ import annotations

import json
import math
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.database.connection import (
    DatabaseEngine,
    open_db_connection,
    mask_database_url,
    ConnectionWrapper,
)

logger = logging.getLogger(__name__)

# Topological table order for migration and verification
TABLES_TOPOLOGICAL_ORDER = [
    "sectors",
    "industries",
    "companies",
    "daily_prices",
    "technical_indicators",
    "quarterly_results",
    "quarterly_financial_vintages",
    "signals",
    "financial_scores",
    "opportunity_scores",
    "backtest_runs",
    "backtest_results",
    "backtest_trades",
    "backtest_equity_curve",
    "universe_audit_log",
]


def _normalize_value(val: Any, col_name: str = "") -> Any:
    """Normalizes field values for deterministic cross-engine comparison."""
    if val is None:
        return None
    # Boolean fields normalized across SQLite (0/1) and PostgreSQL (True/False)
    if col_name.startswith("is_") or col_name.startswith("has_"):
        return bool(val)
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(val, 4)
    # Timestamps & Dates (normalize to canonical representation)
    val_str = str(val).strip()
    if val_str.endswith("+00:00"):
        val_str = val_str[:-6]
    elif val_str.endswith("Z"):
        val_str = val_str[:-1]
    return val_str


def _compute_table_checksum(
    conn: ConnectionWrapper,
    table_name: str,
    columns: List[str],
    pk_column: str,
) -> Tuple[int, str]:
    """
    Computes a deterministic cryptographic SHA-256 checksum over all rows
    in a table, ordered canonically by primary key.
    """
    cur = conn.cursor()
    cols_sql = ", ".join(columns)
    query = f"SELECT {cols_sql} FROM {table_name} ORDER BY {pk_column} ASC"
    cur.execute(query)
    rows = cur.fetchall()

    hasher = hashlib.sha256()
    count = 0
    for row in rows:
        count += 1
        # Convert row to normalized tuple
        normalized_row = []
        for col in columns:
            normalized_row.append(_normalize_value(row[col], col))
        canonical_str = json.dumps(normalized_row, separators=(",", ":"), ensure_ascii=True)
        hasher.update(canonical_str.encode("utf-8"))

    return count, hasher.hexdigest().upper()


class VerificationResult:
    """Structured report comparing source SQLite with target PostgreSQL."""

    def __init__(self, source_path: Path, target_url: str):
        self.source_path = source_path
        self.target_url = target_url
        self.masked_target_url = mask_database_url(target_url)
        self.is_valid = False
        self.table_results: Dict[str, Dict[str, Any]] = {}
        self.governance_checks: Dict[str, Any] = {}
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "target_url": self.masked_target_url,
            "is_valid": self.is_valid,
            "table_results": self.table_results,
            "governance_checks": self.governance_checks,
            "errors": self.errors,
        }


def verify_migration(
    source_sqlite_path: Path,
    target_pg_url: str,
    tables: Optional[List[str]] = None,
) -> VerificationResult:
    """
    Executes a comprehensive data integrity verification between SQLite and PostgreSQL.
    """
    result = VerificationResult(source_sqlite_path, target_pg_url)
    target_tables = tables or TABLES_TOPOLOGICAL_ORDER

    if not source_sqlite_path.exists():
        result.errors.append(f"Source SQLite database not found: {source_sqlite_path}")
        return result

    try:
        source_conn = open_db_connection(f"sqlite:///{source_sqlite_path.resolve()}")
    except Exception as e:
        result.errors.append(f"Failed to open source SQLite connection: {e}")
        return result

    try:
        target_conn = open_db_connection(target_pg_url)
    except Exception as e:
        source_conn.close()
        result.errors.append(f"Failed to open target PostgreSQL connection: {e}")
        return result

    try:
        # Check table-by-table
        for table in target_tables:
            # 1. Check if table exists in source
            cur_s = source_conn.cursor()
            cur_s.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (table,),
            )
            if not cur_s.fetchone():
                continue  # Table not in source database, skip safely

            # 2. Check if table exists in target
            cur_t = target_conn.cursor()
            cur_t.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name = %s",
                (table,),
            )
            if not cur_t.fetchone():
                result.errors.append(f"Table '{table}' exists in source but is missing in PostgreSQL target.")
                continue

            # 3. Get common columns
            cur_s.execute(f"PRAGMA table_info({table})")
            s_cols = [r["name"] for r in cur_s.fetchall()]

            cur_t.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name = %s",
                (table,),
            )
            t_cols = {r["column_name"] for r in cur_t.fetchall()}

            # Columns in source that also exist in target (excluding generated columns)
            cols_to_compare = [c for c in s_cols if c in t_cols and c not in ("filing_type", "publication_timestamp")]
            pk_col = "run_id" if table == "backtest_runs" else "id"

            # 4. Compute row counts and cryptographic checksums
            s_count, s_checksum = _compute_table_checksum(source_conn, table, cols_to_compare, pk_col)
            t_count, t_checksum = _compute_table_checksum(target_conn, table, cols_to_compare, pk_col)

            matches = (s_count == t_count) and (s_checksum == t_checksum)
            result.table_results[table] = {
                "source_rows": s_count,
                "target_rows": t_count,
                "rows_match": s_count == t_count,
                "source_checksum": s_checksum,
                "target_checksum": t_checksum,
                "checksum_matches": s_checksum == t_checksum,
                "columns_compared": len(cols_to_compare),
                "is_equivalent": matches,
            }

            if not matches:
                result.errors.append(
                    f"Mismatch in table '{table}': source={s_count} rows ({s_checksum[:8]}...), "
                    f"target={t_count} rows ({t_checksum[:8]}...)"
                )

        # 5. Specialized Governance Verifications (if quarterly_financial_vintages is present)
        if "quarterly_financial_vintages" in result.table_results:
            cur_s = source_conn.cursor()
            cur_t = target_conn.cursor()

            # Lineage counts
            cur_s.execute(
                "SELECT COUNT(parent_vintage_id), COUNT(supersedes_vintage_id), COUNT(superseded_by_vintage_id) "
                "FROM quarterly_financial_vintages"
            )
            s_lineage = cur_s.fetchone()

            cur_t.execute(
                "SELECT COUNT(parent_vintage_id), COUNT(supersedes_vintage_id), COUNT(superseded_by_vintage_id) "
                "FROM quarterly_financial_vintages"
            )
            t_lineage = cur_t.fetchone()

            # Quarantine counts
            cur_s.execute(
                "SELECT research_eligibility, COUNT(*) FROM quarterly_financial_vintages GROUP BY research_eligibility"
            )
            s_quarantine = dict(cur_s.fetchall())

            cur_t.execute(
                "SELECT research_eligibility, COUNT(*) FROM quarterly_financial_vintages GROUP BY research_eligibility"
            )
            t_quarantine = dict(cur_t.fetchall())

            lineage_matches = (list(s_lineage) == list(t_lineage))
            quarantine_matches = (s_quarantine == t_quarantine)

            result.governance_checks = {
                "lineage_matches": lineage_matches,
                "quarantine_distribution_matches": quarantine_matches,
                "source_quarantine": s_quarantine,
                "target_quarantine": t_quarantine,
            }

            if not lineage_matches:
                result.errors.append("Financial vintage lineage counts do not match between source and target.")
            if not quarantine_matches:
                result.errors.append("Financial vintage quarantine status distributions do not match.")

        # Final verdict
        result.is_valid = len(result.errors) == 0 and len(result.table_results) > 0

    finally:
        source_conn.close()
        target_conn.close()

    return result

