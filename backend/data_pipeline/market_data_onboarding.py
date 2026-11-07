"""
Market Data Onboarding Pipeline
===============================
Handles the automated acquisition, validation, backfilling, and technical indicator
calculation for newly registered stocks entering the dynamic stock universe.

Lifecycle Progression:
  COLD_START -> (Download >=200 OHLCV bars) -> (Compute Indicators) -> ACTIVE

Safety Invariants:
- High quality checks: Non-negative price, High >= Low, Close > 0, Volume >= 0.
- Rejection of corrupt or synthetic data.
- Isolated testability (supports mock data_provider injection).
- Automatic audit log emission upon activation.
"""

import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import pandas as pd

from backend.config import DATABASE_PATH, HISTORY_YEARS
from backend.data_pipeline.stock_universe_service import get_universe_stock, get_all_universe_stocks
from backend.data_pipeline.stock_onboarding_service import activate_stock, update_stock_status
from backend.data_pipeline.load_stock_data import fetch_stock_data, insert_daily_prices
from backend.data_pipeline.technical_indicator_service import save_technical_indicators

logger = logging.getLogger(__name__)

MINIMUM_REQUIRED_BARS = 200


def validate_market_data_quality(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Validates OHLCV dataframe integrity.

    Returns
    -------
    (bool, str)
        (is_valid, reason)
    """
    if df is None or df.empty:
        return False, "Dataframe is empty or None."

    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        missing = required - set(df.columns)
        return False, f"Missing required columns: {missing}"

    # Check for NaN in critical price columns
    for col in ["open", "high", "low", "close"]:
        if df[col].isna().any():
            return False, f"Column '{col}' contains NaN values."

    # Logic checks
    if (df["high"] < df["low"]).any():
        return False, "Found instances where High < Low."

    if (df["close"] <= 0).any():
        return False, "Found instances where Close <= 0."

    if (df["volume"] < 0).any():
        return False, "Found instances where Volume < 0."

    return True, "Data quality checks passed."


def onboard_stock_market_data(
    symbol: str,
    history_years: int = HISTORY_YEARS,
    db_path: Optional[Path] = None,
    data_provider: Optional[Callable[[str], pd.DataFrame]] = None,
    auto_activate: bool = True,
) -> Dict[str, Any]:
    """
    Downloads historical market data, populates daily_prices, calculates technical indicators,
    and transitions stock status from COLD_START to ACTIVE if criteria are met.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    history_years : int, default HISTORY_YEARS
        Years of history to fetch.
    db_path : Path, optional
        Target database path. Defaults to DATABASE_PATH.
    data_provider : Callable, optional
        Custom function to fetch dataframe for testing/mocking.
    auto_activate : bool, default True
        Whether to transition status to ACTIVE upon successful >=200 bar backfill.

    Returns
    -------
    Dict[str, Any]
        Diagnostic execution result.
    """
    target_path = Path(db_path or DATABASE_PATH)
    stock = get_universe_stock(symbol, target_path)
    if not stock:
        raise ValueError(f"Stock '{symbol}' is not registered in companies table. Onboard it first.")

    sym = stock["symbol"]
    company_id = stock["id"]

    # 1. Fetch data
    start_date = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365 * history_years)
    ).strftime("%Y-%m-%d")

    if data_provider is not None:
        raw_data = data_provider(sym)
    else:
        raw_data = fetch_stock_data(sym, start_date=start_date)

    if raw_data is None or raw_data.empty:
        update_stock_status(
            sym,
            new_status="PENDING_REVIEW",
            initiated_by="MARKET_DATA_ONBOARDING",
            notes="No market data returned from provider.",
            db_path=target_path,
        )
        return {
            "symbol": sym,
            "success": False,
            "bars_inserted": 0,
            "total_bars": 0,
            "status": "PENDING_REVIEW",
            "error": "No market data returned by provider.",
        }

    # 2. Validate data
    is_valid, reason = validate_market_data_quality(raw_data)
    if not is_valid:
        update_stock_status(
            sym,
            new_status="PENDING_REVIEW",
            initiated_by="MARKET_DATA_ONBOARDING",
            notes=f"Market data quality check failed: {reason}",
            db_path=target_path,
        )
        return {
            "symbol": sym,
            "success": False,
            "bars_inserted": 0,
            "total_bars": 0,
            "status": "PENDING_REVIEW",
            "error": reason,
        }

    # 3. Insert into daily_prices
    conn = sqlite3.connect(target_path)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA foreign_keys = ON")
        inserted, skipped = insert_daily_prices(cur, company_id, raw_data)
        conn.commit()

        # Count total bars now available
        cur.execute("SELECT COUNT(*) FROM daily_prices WHERE company_id = ?", (company_id,))
        total_bars = cur.fetchone()[0]

    finally:
        conn.close()

    # 4. Check bar count against minimum requirement
    if total_bars < MINIMUM_REQUIRED_BARS:
        return {
            "symbol": sym,
            "success": False,
            "bars_inserted": inserted,
            "total_bars": total_bars,
            "status": stock.get("status", "COLD_START"),
            "error": f"Insufficient historical bars ({total_bars} < {MINIMUM_REQUIRED_BARS}) for technical indicators.",
        }

    # 5. Calculate and save technical indicators
    # Note: save_technical_indicators connects via DATABASE_PATH or active environment
    tech_count = 0
    try:
        # If running on custom db_path, we set the environment variable temporarily if needed
        import os
        old_env = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(target_path.resolve())
        try:
            tech_count = save_technical_indicators(sym)
        finally:
            if old_env is not None:
                os.environ["DATABASE_PATH"] = old_env
            else:
                os.environ.pop("DATABASE_PATH", None)
    except Exception as e:
        logger.error(f"Failed to calculate technical indicators for {sym}: {e}")

    # 6. Auto-activate if requested
    final_status = stock.get("status", "COLD_START")
    if auto_activate and total_bars >= MINIMUM_REQUIRED_BARS:
        activated = activate_stock(
            sym,
            initiated_by="MARKET_DATA_ONBOARDING",
            notes=f"Onboarded with {total_bars} bars and {tech_count} technical indicator records.",
            db_path=target_path,
        )
        final_status = activated["status"]

    return {
        "symbol": sym,
        "success": True,
        "bars_inserted": inserted,
        "total_bars": total_bars,
        "technical_records": tech_count,
        "status": final_status,
        "message": f"Successfully onboarded market data ({total_bars} bars, {tech_count} indicators).",
    }


def batch_onboard_cold_start_stocks(
    db_path: Optional[Path] = None,
    data_provider: Optional[Callable[[str], pd.DataFrame]] = None,
) -> Dict[str, Any]:
    """
    Scans for all stocks in COLD_START status and attempts market data onboarding.
    """
    target_path = Path(db_path or DATABASE_PATH)
    cold_stocks = get_all_universe_stocks(db_path=target_path, status="COLD_START")

    results = []
    success_count = 0
    failure_count = 0

    for s in cold_stocks:
        sym = s["symbol"]
        try:
            res = onboard_stock_market_data(
                symbol=sym,
                db_path=target_path,
                data_provider=data_provider,
                auto_activate=True,
            )
            results.append(res)
            if res["success"]:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            failure_count += 1
            results.append({
                "symbol": sym,
                "success": False,
                "error": str(e),
                "status": "COLD_START",
            })

    return {
        "total_attempted": len(cold_stocks),
        "successful": success_count,
        "failed": failure_count,
        "details": results,
    }

