"""
Stock Universe Service
======================
Central database-driven service for querying stock universe membership, lifecycle
status, and metadata. Serves as the single authoritative source of truth for all
data pipelines, scoring services, and API endpoints.

Backward-Compatibility Guarantee:
If executed against an older schema lacking `is_active` or `status` columns,
it falls back gracefully to treating all rows in `companies` as active.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.config import DATABASE_PATH

logger = logging.getLogger(__name__)


def _get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = Path(db_path or DATABASE_PATH)
    if not target_path.exists():
        raise FileNotFoundError(f"Database not found at: {target_path}")
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def _has_universe_columns(conn: sqlite3.Connection) -> bool:
    """Checks whether the companies table has the Phase 4 lifecycle columns."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(companies)")
    cols = {row["name"] for row in cur.fetchall()}
    return "is_active" in cols and "status" in cols


def get_active_universe(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all active stocks currently authorized for pipeline processing,
    scoring, and trading intelligence.

    Returns
    -------
    List[Dict[str, Any]]
        List of stock dictionaries sorted alphabetically by symbol.
    """
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        has_cols = _has_universe_columns(conn)

        if has_cols:
            query = """
                SELECT c.id, c.symbol, c.company_name, c.sector, c.industry,
                       c.exchange, c.sector_id, c.industry_id, c.is_active,
                       c.status, c.listing_date, c.source, c.created_at, c.updated_at
                FROM companies c
                WHERE c.is_active = 1 AND c.status = 'ACTIVE'
                ORDER BY c.symbol ASC
            """
        else:
            query = """
                SELECT c.id, c.symbol, c.company_name, c.sector, c.industry,
                       c.exchange, c.sector_id, c.industry_id
                FROM companies c
                ORDER BY c.symbol ASC
            """

        cur.execute(query)
        rows = cur.fetchall()

        stocks = []
        for r in rows:
            d = dict(r)
            if not has_cols:
                d["is_active"] = 1
                d["status"] = "ACTIVE"
                d["listing_date"] = None
                d["source"] = "LEGACY_SCHEMA"
            stocks.append(d)

        return stocks
    finally:
        conn.close()


def get_active_symbols(db_path: Optional[Path] = None) -> List[str]:
    """Returns a sorted list of uppercase ticker symbols for all active stocks."""
    stocks = get_active_universe(db_path)
    return [s["symbol"] for s in stocks]


def get_universe_stock(symbol: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves metadata and lifecycle status for a single stock by symbol.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. 'RELIANCE', 'TCS'). Normalized to uppercase.
    db_path : Path, optional
        Target database path.

    Returns
    -------
    Optional[Dict[str, Any]]
        Stock dictionary or None if not found in universe.
    """
    sym = symbol.strip().upper()
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        has_cols = _has_universe_columns(conn)

        if has_cols:
            query = """
                SELECT c.id, c.symbol, c.company_name, c.sector, c.industry,
                       c.exchange, c.sector_id, c.industry_id, c.is_active,
                       c.status, c.listing_date, c.source, c.created_at, c.updated_at
                FROM companies c
                WHERE c.symbol = ?
            """
        else:
            query = """
                SELECT c.id, c.symbol, c.company_name, c.sector, c.industry,
                       c.exchange, c.sector_id, c.industry_id
                FROM companies c
                WHERE c.symbol = ?
            """

        cur.execute(query, (sym,))
        row = cur.fetchone()
        if not row:
            return None

        d = dict(row)
        if not has_cols:
            d["is_active"] = 1
            d["status"] = "ACTIVE"
            d["listing_date"] = None
            d["source"] = "LEGACY_SCHEMA"
        return d
    finally:
        conn.close()


def get_universe_count(db_path: Optional[Path] = None) -> Dict[str, int]:
    """
    Returns breakdown of universe membership counts by status.

    Returns
    -------
    Dict[str, int]
        Counts for active, inactive, cold_start, and total stocks.
    """
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        has_cols = _has_universe_columns(conn)

        if not has_cols:
            cur.execute("SELECT COUNT(*) AS total FROM companies")
            total = cur.fetchone()["total"]
            return {
                "active": total,
                "inactive": 0,
                "cold_start": 0,
                "pending_review": 0,
                "delisted": 0,
                "total": total,
            }

        cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM companies
            GROUP BY status
        """)
        counts_by_status = {row["status"]: row["cnt"] for row in cur.fetchall()}

        cur.execute("SELECT COUNT(*) as total FROM companies")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as active_cnt FROM companies WHERE is_active = 1")
        active = cur.fetchone()["active_cnt"]

        return {
            "active": active,
            "inactive": counts_by_status.get("INACTIVE", 0),
            "cold_start": counts_by_status.get("COLD_START", 0),
            "pending_review": counts_by_status.get("PENDING_REVIEW", 0),
            "delisted": counts_by_status.get("DELISTED", 0),
            "total": total,
        }
    finally:
        conn.close()


def get_all_universe_stocks(
    db_path: Optional[Path] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
    sector: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves universe stocks with filtering and optional pagination.
    """
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        has_cols = _has_universe_columns(conn)

        select_cols = (
            "c.id, c.symbol, c.company_name, c.sector, c.industry, c.exchange, "
            "c.sector_id, c.industry_id, c.is_active, c.status, c.listing_date, "
            "c.source, c.created_at, c.updated_at"
            if has_cols
            else "c.id, c.symbol, c.company_name, c.sector, c.industry, c.exchange, "
                 "c.sector_id, c.industry_id"
        )

        conditions = []
        params = []

        if has_cols:
            if status is not None:
                conditions.append("c.status = ?")
                params.append(status.upper())
            if is_active is not None:
                conditions.append("c.is_active = ?")
                params.append(1 if is_active else 0)

        if sector is not None:
            conditions.append("c.sector = ?")
            params.append(sector)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT {select_cols} FROM companies c {where_clause} ORDER BY c.symbol ASC"

        if limit is not None:
            query += f" LIMIT {int(limit)}"
            if offset is not None:
                query += f" OFFSET {int(offset)}"

        cur.execute(query, params)
        rows = cur.fetchall()

        stocks = []
        for r in rows:
            d = dict(r)
            if not has_cols:
                d["is_active"] = 1
                d["status"] = "ACTIVE"
                d["listing_date"] = None
                d["source"] = "LEGACY_SCHEMA"
            stocks.append(d)

        return stocks
    finally:
        conn.close()

