"""
ROE Analysis v1
================

Logic Engineering layer component for analyzing Return on Equity (ROE).

Purpose:
    Analyze ROE data provided by the Financial Data Service:
    - Latest available ROE
    - Historical ROE trend
    - ROE consistency (standard deviation)
    - Data quality / completeness status

Architecture:
    Financial Data Service -> ROE Analyzer -> Future Financial Analyzers -> Financial Score

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

TREND_TOLERANCE_PERCENT = 2.0

CONSISTENCY_HIGH_MAX_STD = 2.0
CONSISTENCY_MODERATE_MAX_STD = 5.0


def analyze_roe(symbol: str) -> Dict[str, Any]:
    """
    Perform Return on Equity (ROE) analysis for a given stock symbol.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "INFY", "TCS").

    Returns
    -------
    dict
        Structured ROE analysis result containing:
        - symbol (str)
        - status (str): "VALID", "PARTIAL", or "INSUFFICIENT"
        - records (int): Total financial records returned
        - data_points (int): Count of valid ROE observations
        - valid_roe_observations (int): Count of valid ROE observations
        - missing_roe_observations (int): Count of missing/NaN ROE observations
        - latest_roe (float or None): Most recent non-NaN ROE observation
        - roe_trend (str): "Improving", "Declining", "Stable", or "Insufficient Data"
        - roe_consistency (str): "High", "Moderate", "Low", or "Insufficient Data"
    """

    # 1. Normalize symbol
    symbol = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "data_points": 0,
        "valid_roe_observations": 0,
        "missing_roe_observations": 0,
        "latest_roe": None,
        "roe_trend": "Insufficient Data",
        "roe_consistency": "Insufficient Data",
    }

    # 2. Get financial data through Financial Data Service
    data = get_financial_data(symbol)

    if data is None or data.empty:
        return default_result

    # Avoid mutating incoming DataFrame
    df = data.copy()
    total_records = len(df)

    # 3. Ensure chronological sorting by quarter
    if "quarter" in df.columns:
        df["quarter_dt"] = pd.to_datetime(df["quarter"], errors="coerce")
        if not df["quarter_dt"].isna().all():
            df = df.sort_values(by="quarter_dt", ascending=True)
        else:
            df = df.sort_values(by="quarter", ascending=True)

    # 4. Convert ROE safely to numeric; NaN represents missing observation
    df["roe_numeric"] = pd.to_numeric(df["roe"], errors="coerce")

    valid_mask = df["roe_numeric"].notna()
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
            "data_points": 0,
            "valid_roe_observations": 0,
            "missing_roe_observations": missing_count,
            "latest_roe": None,
            "roe_trend": "Insufficient Data",
            "roe_consistency": "Insufficient Data",
        }

    # Chronologically ordered valid ROE series
    valid_series = df.loc[valid_mask, "roe_numeric"]

    # 6. Latest available ROE (most recent non-NaN observation)
    latest_roe = float(valid_series.iloc[-1])

    # 7. ROE Trend calculation (provisional logic rule)
    if valid_count < 2:
        roe_trend = "Insufficient Data"
    else:
        earliest_roe = float(valid_series.iloc[0])
        change = latest_roe - earliest_roe

        if change > TREND_TOLERANCE_PERCENT:
            roe_trend = "Improving"
        elif change < -TREND_TOLERANCE_PERCENT:
            roe_trend = "Declining"
        else:
            roe_trend = "Stable"

    # 8. ROE Consistency calculation (provisional sample std dev rule)
    if valid_count < 2:
        roe_consistency = "Insufficient Data"
    else:
        # Sample standard deviation (ddof=1)
        std_dev = float(valid_series.std(ddof=1))

        if std_dev <= CONSISTENCY_HIGH_MAX_STD:
            roe_consistency = "High"
        elif std_dev <= CONSISTENCY_MODERATE_MAX_STD:
            roe_consistency = "Moderate"
        else:
            roe_consistency = "Low"

    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "data_points": valid_count,
        "valid_roe_observations": valid_count,
        "missing_roe_observations": missing_count,
        "latest_roe": latest_roe,
        "roe_trend": roe_trend,
        "roe_consistency": roe_consistency,
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
    print("ROE ANALYSIS V1")
    print("==========================================")

    for symbol in test_stocks:
        res = analyze_roe(symbol)

        print(f"\n------------------------------------------")
        print(f"{res['symbol']}")
        print(f"------------------------------------------")
        print(f"Status                 : {res['status']}")
        print(f"Records                : {res['records']}")
        print(f"Valid ROE observations : {res['valid_roe_observations']}")
        print(f"Missing ROE            : {res['missing_roe_observations']}")
        latest_str = f"{res['latest_roe']:.4f}" if res['latest_roe'] is not None else "None"
        print(f"Latest ROE             : {latest_str}")
        print(f"ROE Trend              : {res['roe_trend']}")
        print(f"ROE Consistency        : {res['roe_consistency']}")

    print("\n==========================================")
    print("ROE ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
