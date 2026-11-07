"""
Stock Onboarding Service
========================
Manages dynamic universe onboarding, symbol validation, lifecycle transitions,
and audit logging.

Lifecycle States:
- COLD_START: Newly registered; market data/technicals backfill in progress.
- ACTIVE: Fully eligible for screening, ranking, and technical indicators.
- INACTIVE: Soft-disabled from daily fetching and signal generation.
- PENDING_REVIEW: Ingestion anomaly or corporate action requiring attention.
- DELISTED: Permanently delisted from exchange.

Safety Invariants:
- Deactivation NEVER deletes price history, technicals, or financial records.
- All lifecycle mutations generate an immutable audit log record.
- Strict symbol formatting prevents ticker corruption.
"""

import json
import re
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from backend.config import DATABASE_PATH
from backend.database.connection import open_db_connection, ConnectionWrapper, CursorWrapper, DatabaseEngine

logger = logging.getLogger(__name__)

# Valid NSE ticker symbols: 1-20 alphanumeric characters, plus '&' or '-'
# Must not contain '.NS' suffix (exchange is separate).
NSE_SYMBOL_REGEX = re.compile(r"^[A-Z0-9&-]{1,20}$")

VALID_STATUSES = {
    "COLD_START",
    "ACTIVE",
    "INACTIVE",
    "PENDING_REVIEW",
    "DELISTED",
}


def validate_symbol(symbol: str) -> str:
    """
    Validates and normalizes an Indian equity ticker symbol for the database.

    Raises
    ------
    ValueError
        If symbol contains invalid characters or suffixes.
    """
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Symbol must be a non-empty string.")

    cleaned = symbol.strip().upper()

    if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
        raise ValueError(
            f"Symbol '{symbol}' must not include exchange suffix (.NS/.BO). "
            f"Use '{cleaned.split('.')[0]}' with exchange='NSE'."
        )

    if not NSE_SYMBOL_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid ticker format: '{symbol}'. "
            "Must be 1-20 uppercase alphanumeric characters, '&', or '-'."
        )

    return cleaned


def _get_connection(db_path: Optional[Union[Path, str]] = None) -> ConnectionWrapper:
    if db_path is not None and not str(db_path).startswith(("sqlite://", "postgresql://", "postgres://")) and str(db_path) != ":memory:":
        target_path = Path(db_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Database not found at: {target_path}")
    return open_db_connection(db_path)


def _get_table_columns(cur: CursorWrapper, table_name: str) -> set:
    """Retrieves column names for a table across SQLite and PostgreSQL."""
    if cur.engine == DatabaseEngine.POSTGRESQL:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (table_name,),
        )
        return {r["column_name"] for r in cur.fetchall()}
    else:
        cur.execute(f"PRAGMA table_info({table_name})")
        return {r["name"] for r in cur.fetchall()}


def _ensure_audit_table(cur: CursorWrapper):
    if cur.engine == DatabaseEngine.POSTGRESQL:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS universe_audit_log (
                id BIGSERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                old_values_json TEXT,
                new_values_json TEXT,
                initiated_by TEXT NOT NULL DEFAULT 'SYSTEM',
                notes TEXT,
                timestamp TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS universe_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                old_values_json TEXT,
                new_values_json TEXT,
                initiated_by TEXT NOT NULL DEFAULT 'SYSTEM',
                notes TEXT,
                timestamp TEXT NOT NULL
            )
        """)


def _log_audit_entry(
    cur: CursorWrapper,
    symbol: str,
    action: str,
    old_values: Optional[Dict],
    new_values: Optional[Dict],
    initiated_by: str,
    notes: Optional[str],
):
    _ensure_audit_table(cur)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute(
        """
        INSERT INTO universe_audit_log (
            symbol, action, old_values_json, new_values_json, initiated_by, notes, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            action,
            json.dumps(old_values, default=str) if old_values else None,
            json.dumps(new_values, default=str) if new_values else None,
            initiated_by,
            notes,
            now_iso,
        ),
    )


def _resolve_sector_and_industry_ids(
    cur: CursorWrapper, sector: Optional[str], industry: Optional[str]
) -> tuple[Optional[int], Optional[int]]:
    """Resolves or auto-populates sector_id and industry_id if relational tables exist."""
    has_sectors = bool(_get_table_columns(cur, "sectors"))
    has_industries = bool(_get_table_columns(cur, "industries"))

    sector_id = None
    industry_id = None

    if has_sectors and sector:
        cur.execute("SELECT id FROM sectors WHERE LOWER(name) = LOWER(?)", (sector.strip(),))
        row = cur.fetchone()
        if row:
            sector_id = row[0]
        else:
            if cur.engine == DatabaseEngine.POSTGRESQL:
                cur.execute("INSERT INTO sectors (name) VALUES (?) RETURNING id", (sector.strip(),))
                ret_row = cur.fetchone()
                sector_id = ret_row[0] if ret_row else None
            else:
                cur.execute("INSERT INTO sectors (name) VALUES (?)", (sector.strip(),))
                sector_id = cur.lastrowid

    if has_industries and industry:
        cur.execute("SELECT id FROM industries WHERE LOWER(name) = LOWER(?)", (industry.strip(),))
        row = cur.fetchone()
        if row:
            industry_id = row[0]
        else:
            ind_cols = _get_table_columns(cur, "industries")
            has_sec_col = "sector_id" in ind_cols and sector_id is not None
            if cur.engine == DatabaseEngine.POSTGRESQL:
                if has_sec_col:
                    cur.execute(
                        "INSERT INTO industries (name, sector_id) VALUES (?, ?) RETURNING id",
                        (industry.strip(), sector_id),
                    )
                else:
                    cur.execute("INSERT INTO industries (name) VALUES (?) RETURNING id", (industry.strip(),))
                ret_row = cur.fetchone()
                industry_id = ret_row[0] if ret_row else None
            else:
                if has_sec_col:
                    cur.execute(
                        "INSERT INTO industries (name, sector_id) VALUES (?, ?)",
                        (industry.strip(), sector_id),
                    )
                else:
                    cur.execute("INSERT INTO industries (name) VALUES (?)", (industry.strip(),))
                industry_id = cur.lastrowid

    return sector_id, industry_id


def add_stock(
    symbol: str,
    company_name: str,
    sector: str,
    industry: Optional[str] = None,
    exchange: str = "NSE",
    listing_date: Optional[str] = None,
    source: str = "MANUAL_ONBOARDING",
    status: str = "COLD_START",
    initiated_by: str = "SYSTEM",
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Onboards a new stock into the database-backed universe.

    Parameters
    ----------
    symbol : str
        Ticker symbol. Validated and normalized to uppercase.
    company_name : str
        Legal or registered corporate name.
    sector : str
        Economic sector classification.
    industry : str, optional
        Industry classification.
    exchange : str, default 'NSE'
        Exchange venue.
    listing_date : str, optional
        ISO date (YYYY-MM-DD).
    source : str, default 'MANUAL_ONBOARDING'
        Source of the universe addition.
    status : str, default 'COLD_START'
        Initial lifecycle state.
    initiated_by : str, default 'SYSTEM'
        User, process, or script initiating the onboarding.
    notes : str, optional
        Justification or context.
    db_path : Path, optional
        Target database.

    Returns
    -------
    Dict[str, Any]
        Newly created company record.
    """
    clean_symbol = validate_symbol(symbol)
    if not company_name or not company_name.strip():
        raise ValueError("company_name must be a non-empty string.")
    if not sector or not sector.strip():
        raise ValueError("sector must be a non-empty string.")

    target_status = status.upper().strip()
    if target_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {sorted(VALID_STATUSES)}")

    is_active = 1 if target_status == "ACTIVE" else 0
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()

        # Check for duplicate
        cur.execute("SELECT id, symbol, status FROM companies WHERE symbol = ?", (clean_symbol,))
        existing = cur.fetchone()
        if existing:
            raise ValueError(
                f"Stock with symbol '{clean_symbol}' already exists in universe (ID: {existing['id']}, Status: {existing['status']})."
            )

        # Check table columns
        cols = _get_table_columns(cur, "companies")
        has_extended = "is_active" in cols and "status" in cols

        sector_id, industry_id = _resolve_sector_and_industry_ids(cur, sector, industry)

        if cur.engine == DatabaseEngine.POSTGRESQL:
            is_active_val = (target_status == "ACTIVE")
        else:
            is_active_val = 1 if target_status == "ACTIVE" else 0

        if has_extended:
            insert_query = """
                INSERT INTO companies (
                    symbol, company_name, sector, industry, exchange,
                    sector_id, industry_id, is_active, status, listing_date,
                    created_at, updated_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                clean_symbol,
                company_name.strip(),
                sector.strip(),
                industry.strip() if industry else None,
                exchange.strip().upper(),
                sector_id,
                industry_id,
                is_active_val,
                target_status,
                listing_date,
                now_iso,
                now_iso,
                source,
            )
        else:
            insert_query = """
                INSERT INTO companies (
                    symbol, company_name, sector, industry, exchange,
                    sector_id, industry_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                clean_symbol,
                company_name.strip(),
                sector.strip(),
                industry.strip() if industry else None,
                exchange.strip().upper(),
                sector_id,
                industry_id,
            )

        if cur.engine == DatabaseEngine.POSTGRESQL:
            cur.execute(insert_query + " RETURNING id", params)
            ret_row = cur.fetchone()
            new_id = ret_row[0] if ret_row else None
        else:
            cur.execute(insert_query, params)
            new_id = cur.lastrowid

        new_record = {
            "id": new_id,
            "symbol": clean_symbol,
            "company_name": company_name.strip(),
            "sector": sector.strip(),
            "industry": industry.strip() if industry else None,
            "exchange": exchange.strip().upper(),
            "sector_id": sector_id,
            "industry_id": industry_id,
            "is_active": is_active,
            "status": target_status,
            "listing_date": listing_date,
            "created_at": now_iso,
            "updated_at": now_iso,
            "source": source,
        }

        _log_audit_entry(
            cur,
            clean_symbol,
            "ADD",
            old_values=None,
            new_values=new_record,
            initiated_by=initiated_by,
            notes=notes or f"Onboarded into universe via {source}",
        )

        conn.commit()
        logger.info(f"Successfully onboarded stock {clean_symbol} into universe (ID: {new_id})")
        return new_record

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def activate_stock(
    symbol: str,
    initiated_by: str = "SYSTEM",
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Activates a stock for daily pipeline ingestion, ranking, and trading intelligence.
    """
    clean_symbol = validate_symbol(symbol)
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE symbol = ?", (clean_symbol,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Stock '{clean_symbol}' not found in companies table.")

        old_values = dict(row)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cols = _get_table_columns(cur, "companies")

        if "is_active" in cols and "status" in cols:
            cur.execute(
                """
                UPDATE companies
                SET is_active = TRUE, status = 'ACTIVE', updated_at = ?
                WHERE symbol = ?
                """,
                (now_iso, clean_symbol),
            )
        else:
            # Legacy table, already considered active
            pass

        new_values = dict(old_values)
        new_values["is_active"] = 1
        new_values["status"] = "ACTIVE"
        new_values["updated_at"] = now_iso

        _log_audit_entry(
            cur,
            clean_symbol,
            "ACTIVATE",
            old_values=old_values,
            new_values=new_values,
            initiated_by=initiated_by,
            notes=notes or "Stock activated in dynamic universe.",
        )

        conn.commit()
        logger.info(f"Activated stock {clean_symbol} in universe.")
        return new_values

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def deactivate_stock(
    symbol: str,
    initiated_by: str = "SYSTEM",
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Soft-deactivates a stock from the active universe.

    CRITICAL SAFETY GUARANTEE:
    This operation NEVER deletes price history, technical indicators,
    quarterly results, or financial vintages.
    """
    clean_symbol = validate_symbol(symbol)
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE symbol = ?", (clean_symbol,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Stock '{clean_symbol}' not found in companies table.")

        old_values = dict(row)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cols = _get_table_columns(cur, "companies")

        if "is_active" in cols and "status" in cols:
            cur.execute(
                """
                UPDATE companies
                SET is_active = FALSE, status = 'INACTIVE', updated_at = ?
                WHERE symbol = ?
                """,
                (now_iso, clean_symbol),
            )
        else:
            raise RuntimeError(
                "Cannot deactivate stock on legacy schema lacking is_active column. "
                "Run migrate_universe_schema first."
            )

        new_values = dict(old_values)
        new_values["is_active"] = 0
        new_values["status"] = "INACTIVE"
        new_values["updated_at"] = now_iso

        _log_audit_entry(
            cur,
            clean_symbol,
            "DEACTIVATE",
            old_values=old_values,
            new_values=new_values,
            initiated_by=initiated_by,
            notes=notes or "Stock deactivated in dynamic universe.",
        )

        conn.commit()
        logger.info(f"Deactivated stock {clean_symbol} in universe (data preserved).")
        return new_values

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_stock_status(
    symbol: str,
    new_status: str,
    initiated_by: str = "SYSTEM",
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Transitions a stock's lifecycle status (COLD_START, ACTIVE, INACTIVE, PENDING_REVIEW, DELISTED).
    """
    clean_symbol = validate_symbol(symbol)
    target_status = new_status.upper().strip()
    if target_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {sorted(VALID_STATUSES)}")

    conn = _get_connection(db_path)
    is_active = (target_status == "ACTIVE") if conn.engine == DatabaseEngine.POSTGRESQL else (1 if target_status == "ACTIVE" else 0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM companies WHERE symbol = ?", (clean_symbol,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Stock '{clean_symbol}' not found in companies table.")

        old_values = dict(row)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cols = _get_table_columns(cur, "companies")

        if "is_active" in cols and "status" in cols:
            cur.execute(
                """
                UPDATE companies
                SET is_active = ?, status = ?, updated_at = ?
                WHERE symbol = ?
                """,
                (is_active, target_status, now_iso, clean_symbol),
            )
        else:
            raise RuntimeError("Database schema does not support status updates.")

        new_values = dict(old_values)
        new_values["is_active"] = is_active
        new_values["status"] = target_status
        new_values["updated_at"] = now_iso

        _log_audit_entry(
            cur,
            clean_symbol,
            "STATUS_CHANGE",
            old_values=old_values,
            new_values=new_values,
            initiated_by=initiated_by,
            notes=notes or f"Status changed to {target_status}",
        )

        conn.commit()
        return new_values

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_audit_history(
    symbol: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves universe audit log history.
    """
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()
        _ensure_audit_table(cur)

        if symbol:
            clean_sym = validate_symbol(symbol)
            cur.execute(
                """
                SELECT id, symbol, action, old_values_json, new_values_json,
                       initiated_by, notes, timestamp
                FROM universe_audit_log
                WHERE symbol = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (clean_sym, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, symbol, action, old_values_json, new_values_json,
                       initiated_by, notes, timestamp
                FROM universe_audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

