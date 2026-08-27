"""
ROCE Analysis v1
================

Logic Engineering layer component for analyzing Return on Capital Employed (ROCE).

Purpose:
    Analyze ROCE data provided by the Financial Data Service:
    - Latest available ROCE
    - Historical ROCE trend
    - ROCE consistency (sample standard deviation)
    - Data quality / completeness status

Architecture:
    Financial Data Service -> ROCE Analyzer -> Future Financial Analyzers -> Financial Score

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


def analyze_roce(symbol: str) -> Dict[str, Any]:
    """
    Perform Return on Capital Employed (ROCE) analysis for a given stock symbol.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "INFY", "TCS").

    Returns
    -------
    dict
        Structured ROCE analysis result containing:
        - symbol (str)
        - status (str): "VALID", "PARTIAL", or "INSUFFICIENT"
        - records (int): Total financial records returned
        - data_points (int): Count of valid ROCE observations
        - valid_roce_observations (int): Count of valid ROCE observations
        - missing_roce (int): Count of missing/NaN ROCE observations
        - missing_roce_observations (int): Alias count of missing/NaN ROCE observations
        - latest_roce (float or None): Most recent non-NaN ROCE observation
        - roce_trend (str): "Improving", "Declining", "Stable", or "Insufficient Data"
        - roce_consistency (str): "High", "Moderate", "Low", or "Insufficient Data"
    """

    # 1. Normalize symbol
    symbol = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "data_points": 0,
        "valid_roce_observations": 0,
        "missing_roce": 0,
        "missing_roce_observations": 0,
        "latest_roce": None,
        "roce_trend": "Insufficient Data",
        "roce_consistency": "Insufficient Data",
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

    # 4. Convert ROCE safely to numeric; NaN represents missing observation
    df["roce_numeric"] = pd.to_numeric(df["roce"], errors="coerce")

    valid_mask = df["roce_numeric"].notna()
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
            "valid_roce_observations": 0,
            "missing_roce": missing_count,
            "missing_roce_observations": missing_count,
            "latest_roce": None,
            "roce_trend": "Insufficient Data",
            "roce_consistency": "Insufficient Data",
        }

    # Chronologically ordered valid ROCE series
    valid_series = df.loc[valid_mask, "roce_numeric"]

    # 6. Latest available ROCE (most recent non-NaN observation)
    latest_roce = float(valid_series.iloc[-1])

    # 7. ROCE Trend calculation (provisional logic rule)
    if valid_count < 2:
        roce_trend = "Insufficient Data"
    else:
        earliest_roce = float(valid_series.iloc[0])
        change = latest_roce - earliest_roce

        if change > TREND_TOLERANCE_PERCENT:
            roce_trend = "Improving"
        elif change < -TREND_TOLERANCE_PERCENT:
            roce_trend = "Declining"
        else:
            roce_trend = "Stable"

    # 8. ROCE Consistency calculation (provisional sample std dev rule)
    if valid_count < 2:
        roce_consistency = "Insufficient Data"
    else:
        # Sample standard deviation (ddof=1)
        std_dev = float(valid_series.std(ddof=1))

        if std_dev <= CONSISTENCY_HIGH_MAX_STD:
            roce_consistency = "High"
        elif std_dev <= CONSISTENCY_MODERATE_MAX_STD:
            roce_consistency = "Moderate"
        else:
            roce_consistency = "Low"

    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "data_points": valid_count,
        "valid_roce_observations": valid_count,
        "missing_roce": missing_count,
        "missing_roce_observations": missing_count,
        "latest_roce": latest_roce,
        "roce_trend": roce_trend,
        "roce_consistency": roce_consistency,
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
    print("ROCE ANALYSIS V1")
    print("==========================================")

    for symbol in test_stocks:
        res = analyze_roce(symbol)

        print(f"\n------------------------------------------")
        print(f"{res['symbol']}")
        print(f"------------------------------------------")
        print(f"Status                  : {res['status']}")
        print(f"Records                 : {res['records']}")
        print(f"Valid ROCE observations : {res['valid_roce_observations']}")
        print(f"Missing ROCE            : {res['missing_roce']}")
        latest_str = f"{res['latest_roce']:.4f}" if res['latest_roce'] is not None else "None"
        print(f"Latest ROCE             : {latest_str}")
        print(f"ROCE Trend              : {res['roce_trend']}")
        print(f"ROCE Consistency        : {res['roce_consistency']}")

    print("\n==========================================")
    print("ROCE ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
