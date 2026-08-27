"""
Debt/Equity Analysis v1
=======================

Logic Engineering layer component for analyzing Debt to Equity ratio (Debt/Equity).

Purpose:
    Analyze Debt/Equity data provided by the Financial Data Service:
    - Latest available Debt/Equity
    - Historical Debt/Equity trend
    - Debt/Equity consistency (sample standard deviation)
    - Data quality / completeness status

Architecture:
    Financial Data Service -> Debt/Equity Analyzer -> Future Financial Analyzers -> Financial Score

This component is READ-ONLY with respect to data and does NOT:
    - access SQLite directly
    - fetch data from yfinance or external APIs
    - modify database records
    - compute final Financial Score or trading decisions
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from backend.data_pipeline.financial_service import get_financial_data


# ============================================================
# PROVISIONAL LOGIC THRESHOLDS (v1)
# ============================================================
# Note: These thresholds are initial analysis heuristics for v1.
# They are PROVISIONAL and NOT empirically validated trading rules.

TREND_TOLERANCE = 2.0

CONSISTENCY_HIGH_MAX_STD = 2.0
CONSISTENCY_MODERATE_MAX_STD = 5.0


def analyze_debt_equity(symbol: str) -> Dict[str, Any]:
    """
    Perform Debt/Equity ratio analysis for a given stock symbol.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "INFY", "TCS").

    Returns
    -------
    dict
        Structured Debt/Equity analysis result containing:
        - symbol (str)
        - status (str): "VALID", "PARTIAL", or "INSUFFICIENT"
        - records (int): Total financial records returned
        - valid_debt_equity_observations (int): Count of valid Debt/Equity observations
        - missing_debt_equity (int): Count of missing/NaN Debt/Equity observations
        - latest_debt_equity (float or None): Most recent non-NaN Debt/Equity observation
        - debt_equity_trend (str): "Improving", "Declining", "Stable", or "Insufficient Data"
        - debt_equity_consistency (str): "High", "Moderate", "Low", or "Insufficient Data"
    """

    # 1. Normalize symbol
    symbol = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "valid_debt_equity_observations": 0,
        "missing_debt_equity": 0,
        "latest_debt_equity": None,
        "debt_equity_trend": "Insufficient Data",
        "debt_equity_consistency": "Insufficient Data",
    }

    # 2. Get financial data through Financial Data Service
    data = get_financial_data(symbol)

    if data is None or data.empty:
        return default_result

    # Avoid mutating incoming DataFrame
    df = data.copy()
    total_records = len(df)

    if "debt_equity" not in df.columns:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_debt_equity_observations": 0,
            "missing_debt_equity": total_records,
            "latest_debt_equity": None,
            "debt_equity_trend": "Insufficient Data",
            "debt_equity_consistency": "Insufficient Data",
        }

    # 3. Ensure chronological sorting by quarter
    if "quarter" in df.columns:
        df["quarter_dt"] = pd.to_datetime(df["quarter"], errors="coerce")
        if not df["quarter_dt"].isna().all():
            df = df.sort_values(by="quarter_dt", ascending=True)
        else:
            df = df.sort_values(by="quarter", ascending=True)

    # 4. Convert debt_equity safely to numeric; NaN represents missing observation
    df["de_numeric"] = pd.to_numeric(df["debt_equity"], errors="coerce")

    valid_mask = df["de_numeric"].notna()
    valid_count = int(valid_mask.sum())
    missing_count = int(total_records - valid_count)

    # 5. Determine status
    if valid_count == 0:
        status = "INSUFFICIENT"
    elif valid_count == total_records:
        status = "VALID"
    else:
        status = "PARTIAL"

    # If insufficient valid observations exist
    if status == "INSUFFICIENT":
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_debt_equity_observations": 0,
            "missing_debt_equity": missing_count,
            "latest_debt_equity": None,
            "debt_equity_trend": "Insufficient Data",
            "debt_equity_consistency": "Insufficient Data",
        }

    # Chronologically ordered valid Debt/Equity series
    valid_series = df.loc[valid_mask, "de_numeric"]

    # 6. Latest available Debt/Equity (most recent non-NaN observation)
    latest_de = float(valid_series.iloc[-1])

    # 7. Debt/Equity Trend calculation
    # change = latest_valid_debt_equity - earliest_valid_debt_equity
    # Lower leverage is generally preferred.
    # change < -2.0 -> "Improving"
    # change > +2.0 -> "Declining"
    # -2.0 <= change <= +2.0 -> "Stable"
    if valid_count < 2:
        debt_equity_trend = "Insufficient Data"
    else:
        earliest_de = float(valid_series.iloc[0])
        change = latest_de - earliest_de

        if change < -TREND_TOLERANCE:
            debt_equity_trend = "Improving"
        elif change > TREND_TOLERANCE:
            debt_equity_trend = "Declining"
        else:
            debt_equity_trend = "Stable"

    # 8. Debt/Equity Consistency calculation (sample standard deviation rule)
    if valid_count < 2:
        debt_equity_consistency = "Insufficient Data"
    else:
        # Sample standard deviation (ddof=1)
        std_dev = float(valid_series.std(ddof=1))

        if std_dev <= CONSISTENCY_HIGH_MAX_STD:
            debt_equity_consistency = "High"
        elif std_dev <= CONSISTENCY_MODERATE_MAX_STD:
            debt_equity_consistency = "Moderate"
        else:
            debt_equity_consistency = "Low"

    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "valid_debt_equity_observations": valid_count,
        "missing_debt_equity": missing_count,
        "latest_debt_equity": latest_de,
        "debt_equity_trend": debt_equity_trend,
        "debt_equity_consistency": debt_equity_consistency,
    }


def main():
    """
    Run CLI analysis for verified stocks.
    """
    test_stocks = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("DEBT/EQUITY ANALYSIS V1")
    print("==========================================")

    for symbol in test_stocks:
        res = analyze_debt_equity(symbol)

        print(f"\n------------------------------------------")
        print(f"{res['symbol']}")
        print(f"------------------------------------------")
        print(f"Status                 : {res['status']}")
        print(f"Records                : {res['records']}")
        print(f"Valid D/E observations : {res['valid_debt_equity_observations']}")
        print(f"Missing D/E            : {res['missing_debt_equity']}")
        latest_str = f"{res['latest_debt_equity']:.4f}" if res['latest_debt_equity'] is not None else "None"
        print(f"Latest D/E             : {latest_str}")
        print(f"D/E Trend              : {res['debt_equity_trend']}")
        print(f"D/E Consistency        : {res['debt_equity_consistency']}")

    print("\n==========================================")
    print("DEBT/EQUITY ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
