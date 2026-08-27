"""
Opportunity Score Persistence Service
=====================================

Provides database persistence operations for Decision Engine V1 (Engine 7)
Opportunity Scores.

Architecture:
-------------
Decision Engine (pure calculation) -> Opportunity Service (DB persistence) -> opportunity_scores (table)

Author: Logic Engineer
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.engines.decision_engine import calculate_opportunity_score

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "database" / "swing_trading.db"


# ============================================================
# SAVE OPPORTUNITY SCORE
# ============================================================

def save_opportunity_score(symbol: str, date: Optional[str] = None) -> bool:
    """
    Calculates and persists the composite Opportunity Score for a stock symbol
    into the opportunity_scores database table.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "TCS", "INFY").
    date : Optional[str]
        Snapshot calculation date string (YYYY-MM-DD). Defaults to current UTC date if None.

    Returns
    -------
    bool
        True if persisted successfully, False if skipped (e.g. INSUFFICIENT score
        where opportunity_score is None, or unknown symbol).
    """
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        return False

    symbol_clean = symbol.strip().upper()

    # 1. Obtain score calculation from pure Decision Engine
    score_dict = calculate_opportunity_score(symbol_clean)

    # 2. Check if opportunity_score is None or status is INSUFFICIENT
    opportunity_score = score_dict.get("opportunity_score")
    if opportunity_score is None or score_dict.get("status") == "INSUFFICIENT":
        return False

    # 3. Resolve Date Semantics
    if not date or not isinstance(date, str) or not date.strip():
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        date_str = date.strip()

    # 4. Resolve company_id & execute transaction-safe idempotent write
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        cursor.execute(
            """
            SELECT id
            FROM companies
            WHERE symbol = ?
            """,
            (symbol_clean,),
        )
        row = cursor.fetchone()
        if not row:
            return False

        company_id = row[0]

        technical_score = score_dict.get("technical_score")
        financial_score = score_dict.get("financial_score")
        momentum_score = score_dict.get("momentum_score")

        # 5. Idempotent Persistence: DELETE followed by INSERT
        cursor.execute(
            """
            DELETE FROM opportunity_scores
            WHERE company_id = ? AND date = ?
            """,
            (company_id, date_str),
        )

        cursor.execute(
            """
            INSERT INTO opportunity_scores (
                company_id,
                date,
                technical_score,
                financial_score,
                momentum_score,
                opportunity_score
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                date_str,
                technical_score,
                financial_score,
                momentum_score,
                opportunity_score,
            ),
        )

        connection.commit()
        return True
    except Exception:
        connection.rollback()
        return False
    finally:
        connection.close()
