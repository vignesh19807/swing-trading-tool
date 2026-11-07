"""
Universe Coverage Service
=========================
Provides decoupled, transparent tracking of market data and financial fundamental
coverage across the dynamic stock universe.

Decoupled Dimensions:
1. Market Data Status:
   - MARKET_DATA_READY: >= 200 daily bars, technical indicators calculated.
   - COLLECTING: 1 - 199 daily bars (insufficient for full technical indicators).
   - STALE: Market data exists, but latest bar is > 7 calendar days old.
   - NO_DATA: 0 daily price bars.

2. Financial Fundamental Status:
   - ELIGIBLE: >= 4 verified quarterly vintages available with PIT lag enforcement.
   - COLD_START_INCOMPLETE: 1 - 3 quarterly vintages available.
   - UNVERIFIED_PENDING: 0 quarterly vintages available (cold start).
   - QUARANTINED: Data integrity or audit anomaly flagged.

3. Composite Signal Readiness:
   - FULLY_COVERED: Technical + Financial data ready.
   - TECHNICAL_ONLY: Technical signals active; financial engine operates under cold-start fallback.
   - ONBOARDING: Technical history still being accumulated.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.config import DATABASE_PATH
from backend.data_pipeline.stock_universe_service import get_universe_stock, get_active_universe

MINIMUM_MARKET_BARS = 200
MINIMUM_FINANCIAL_QUARTERS = 4
STALE_DAYS_THRESHOLD = 7


def _get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = Path(db_path or DATABASE_PATH)
    if not target_path.exists():
        raise FileNotFoundError(f"Database not found at: {target_path}")
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_stock_coverage(symbol: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Returns granular data coverage metrics for a single stock.
    """
    stock = get_universe_stock(symbol, db_path)
    if not stock:
        return None

    company_id = stock["id"]
    conn = _get_connection(db_path)
    try:
        cur = conn.cursor()

        # 1. Inspect daily_prices
        cur.execute(
            """
            SELECT COUNT(*) as bar_count, MIN(date) as earliest_date, MAX(date) as latest_date
            FROM daily_prices
            WHERE company_id = ?
            """,
            (company_id,),
        )
        p_row = cur.fetchone()
        bar_count = p_row["bar_count"] if p_row else 0
        earliest_price_date = p_row["earliest_date"] if p_row else None
        latest_price_date = p_row["latest_date"] if p_row else None

        # Check staleness
        is_stale = False
        if latest_price_date:
            try:
                latest_dt = datetime.datetime.fromisoformat(latest_price_date).date()
                today = datetime.datetime.now(datetime.timezone.utc).date()
                if (today - latest_dt).days > STALE_DAYS_THRESHOLD:
                    is_stale = True
            except Exception:
                pass

        if bar_count >= MINIMUM_MARKET_BARS:
            market_data_status = "STALE" if is_stale else "MARKET_DATA_READY"
        elif bar_count > 0:
            market_data_status = "COLLECTING"
        else:
            market_data_status = "NO_DATA"

        # 2. Inspect technical_indicators
        cur.execute(
            """
            SELECT COUNT(*) as ind_count, MAX(date) as latest_ind_date
            FROM technical_indicators
            WHERE company_id = ?
            """,
            (company_id,),
        )
        t_row = cur.fetchone()
        tech_count = t_row["ind_count"] if t_row else 0
        latest_tech_date = t_row["latest_ind_date"] if t_row else None

        # 3. Inspect financials (check quarterly_financial_vintages if exists, else quarterly_results)
        cur.execute("PRAGMA table_info(quarterly_financial_vintages)")
        vintages_info = cur.fetchall()
        has_vintages = bool(vintages_info)

        quarter_count = 0
        latest_quarter = None
        is_quarantined = False

        if has_vintages:
            v_cols = {r["name"] for r in vintages_info}
            id_col = "company_id" if "company_id" in v_cols else ("symbol" if "symbol" in v_cols else None)
            id_val = company_id if id_col == "company_id" else stock["symbol"]

            # Check for explicit quarantine
            if "research_eligibility" in v_cols:
                cur.execute(
                    f"SELECT COUNT(*) FROM quarterly_financial_vintages WHERE {id_col} = ? AND research_eligibility = 'QUARANTINED'",
                    (id_val,),
                )
                if cur.fetchone()[0] > 0:
                    is_quarantined = True
            elif "is_quarantined" in v_cols:
                cur.execute(
                    f"SELECT COUNT(*) FROM quarterly_financial_vintages WHERE {id_col} = ? AND is_quarantined = 1",
                    (id_val,),
                )
                if cur.fetchone()[0] > 0:
                    is_quarantined = True

            # Query verified eligible vintages with valid publication dates
            where_clauses = [f"{id_col} = ?"]
            params = [id_val]

            if "research_eligibility" in v_cols:
                where_clauses.append("research_eligibility = 'VERIFIED_ELIGIBLE'")
            elif "verification_status" in v_cols:
                where_clauses.append("verification_status = 'VERIFIED'")
            elif "is_verified" in v_cols:
                where_clauses.append("is_verified = 1")

            # Must have non-null publication date
            if "published_at" in v_cols:
                where_clauses.append("published_at IS NOT NULL AND published_at != ''")
            elif "publication_date" in v_cols:
                where_clauses.append("publication_date IS NOT NULL AND publication_date != ''")

            q_col = "quarter" if "quarter" in v_cols else ("fiscal_quarter" if "fiscal_quarter" in v_cols else "quarter")
            query = f"SELECT COUNT(*) as q_count, MAX({q_col}) as latest_q FROM quarterly_financial_vintages WHERE {' AND '.join(where_clauses)}"
            cur.execute(query, params)
            v_row = cur.fetchone()
            if v_row and v_row["q_count"] > 0:
                quarter_count = v_row["q_count"]
                latest_quarter = v_row["latest_q"]

        if quarter_count == 0 and not is_quarantined:
            cur.execute("PRAGMA table_info(quarterly_results)")
            if cur.fetchall():
                cur.execute(
                    """
                    SELECT COUNT(*) as q_count, MAX(quarter) as latest_q
                    FROM quarterly_results
                    WHERE company_id = ?
                    """,
                    (company_id,),
                )
                q_row = cur.fetchone()
                if q_row:
                    quarter_count = q_row["q_count"]
                    latest_quarter = q_row["latest_q"]

        if is_quarantined:
            financial_status = "QUARANTINED"
        elif quarter_count >= MINIMUM_FINANCIAL_QUARTERS:
            financial_status = "ELIGIBLE"
        elif quarter_count > 0:
            financial_status = "COLD_START_INCOMPLETE"
        else:
            financial_status = "UNVERIFIED_PENDING"

        # 4. Composite Readiness
        technical_ready = bar_count >= MINIMUM_MARKET_BARS and tech_count > 0
        financial_ready = financial_status == "ELIGIBLE"

        if technical_ready and financial_ready:
            composite_status = "FULLY_COVERED"
        elif technical_ready:
            composite_status = "TECHNICAL_ONLY"
        else:
            composite_status = "ONBOARDING"

        return {
            "symbol": stock["symbol"],
            "company_name": stock["company_name"],
            "sector": stock["sector"],
            "lifecycle_status": stock.get("status", "ACTIVE"),
            "is_active": bool(stock.get("is_active", 1)),
            "market_data": {
                "status": market_data_status,
                "bar_count": bar_count,
                "required_bars": MINIMUM_MARKET_BARS,
                "earliest_date": earliest_price_date,
                "latest_date": latest_price_date,
                "is_stale": is_stale,
            },
            "technical_indicators": {
                "record_count": tech_count,
                "latest_date": latest_tech_date,
                "has_coverage": tech_count > 0,
            },
            "financial_data": {
                "status": financial_status,
                "quarter_count": quarter_count,
                "required_quarters": MINIMUM_FINANCIAL_QUARTERS,
                "latest_quarter": latest_quarter,
            },
            "readiness": {
                "technical_ready": technical_ready,
                "financial_ready": financial_ready,
                "composite_status": composite_status,
                "signal_eligible": technical_ready,
            },
        }

    finally:
        conn.close()


def get_universe_coverage_summary(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returns aggregate coverage statistics across the active stock universe.
    """
    active_stocks = get_active_universe(db_path)
    total_active = len(active_stocks)

    market_status_counts = {"MARKET_DATA_READY": 0, "COLLECTING": 0, "STALE": 0, "NO_DATA": 0}
    financial_status_counts = {
        "ELIGIBLE": 0,
        "COLD_START_INCOMPLETE": 0,
        "UNVERIFIED_PENDING": 0,
        "QUARANTINED": 0,
    }
    composite_counts = {"FULLY_COVERED": 0, "TECHNICAL_ONLY": 0, "ONBOARDING": 0}

    for s in active_stocks:
        cov = get_stock_coverage(s["symbol"], db_path)
        if not cov:
            continue
        m_status = cov["market_data"]["status"]
        market_status_counts[m_status] = market_status_counts.get(m_status, 0) + 1

        f_status = cov["financial_data"]["status"]
        financial_status_counts[f_status] = financial_status_counts.get(f_status, 0) + 1

        c_status = cov["readiness"]["composite_status"]
        composite_counts[c_status] = composite_counts.get(c_status, 0) + 1

    return {
        "total_active_stocks": total_active,
        "market_data_breakdown": market_status_counts,
        "financial_data_breakdown": financial_status_counts,
        "composite_readiness_breakdown": composite_counts,
        "signal_eligible_count": composite_counts["FULLY_COVERED"] + composite_counts["TECHNICAL_ONLY"],
    }

