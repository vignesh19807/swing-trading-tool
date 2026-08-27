"""
Profit Margin Analysis v1
=========================

Logic Engineering layer component for analyzing Profit Margins (Operating Margin & Net Margin).

Purpose:
    Analyze Profit Margin data provided by the Financial Data Service:
    - Latest available Operating Margin and Net Margin
    - Historical Margin trends
    - Margin consistency (sample standard deviation)
    - Data quality / completeness status

Architecture:
    Financial Data Service -> Profit Margin Analyzer -> Future Financial Analyzers -> Financial Score

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


def analyze_profit_margin(symbol: str) -> Dict[str, Any]:
    """
    Perform Profit Margin analysis (Operating & Net Margin) for a given stock symbol.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "INFY", "TCS").

    Returns
    -------
    dict
        Structured Profit Margin analysis result containing:
        - symbol (str)
        - status (str): "VALID", "PARTIAL", or "INSUFFICIENT"
        - records (int): Total financial records returned
        - valid_profit_margin_observations (int): Count of valid Operating Margin observations
        - missing_profit_margin (int): Count of missing/NaN Operating Margin observations
        - latest_profit_margin (float or None): Most recent non-NaN Operating Margin observation
        - profit_margin_trend (str): "Improving", "Declining", "Stable", or "Insufficient Data"
        - profit_margin_consistency (str): "High", "Moderate", "Low", or "Insufficient Data"
        - latest_operating_margin (float or None)
        - operating_margin_trend (str)
        - operating_margin_consistency (str)
        - latest_net_margin (float or None)
        - net_margin_trend (str)
        - net_margin_consistency (str)
    """

    # 1. Normalize symbol
    symbol = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "valid_profit_margin_observations": 0,
        "missing_profit_margin": 0,
        "latest_profit_margin": None,
        "profit_margin_trend": "Insufficient Data",
        "profit_margin_consistency": "Insufficient Data",
        "valid_operating_margin_observations": 0,
        "missing_operating_margin": 0,
        "latest_operating_margin": None,
        "operating_margin_trend": "Insufficient Data",
        "operating_margin_consistency": "Insufficient Data",
        "valid_net_margin_observations": 0,
        "missing_net_margin": 0,
        "latest_net_margin": None,
        "net_margin_trend": "Insufficient Data",
        "net_margin_consistency": "Insufficient Data",
    }

    # 2. Get financial data through Financial Data Service
    data = get_financial_data(symbol)

    if data is None or data.empty:
        return default_result

    # Avoid mutating incoming DataFrame
    df = data.copy()
    total_records = len(df)

    if "operating_margin" not in df.columns and "net_margin" not in df.columns:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_profit_margin_observations": 0,
            "missing_profit_margin": total_records,
            "latest_profit_margin": None,
            "profit_margin_trend": "Insufficient Data",
            "profit_margin_consistency": "Insufficient Data",
            "valid_operating_margin_observations": 0,
            "missing_operating_margin": total_records,
            "latest_operating_margin": None,
            "operating_margin_trend": "Insufficient Data",
            "operating_margin_consistency": "Insufficient Data",
            "valid_net_margin_observations": 0,
            "missing_net_margin": total_records,
            "latest_net_margin": None,
            "net_margin_trend": "Insufficient Data",
            "net_margin_consistency": "Insufficient Data",
        }

    # 3. Ensure chronological sorting by quarter
    if "quarter" in df.columns:
        df["quarter_dt"] = pd.to_datetime(df["quarter"], errors="coerce")
        if not df["quarter_dt"].isna().all():
            df = df.sort_values(by="quarter_dt", ascending=True)
        else:
            df = df.sort_values(by="quarter", ascending=True)

    # 4. Convert operating_margin and net_margin safely to numeric; NaN represents missing observation
    if "operating_margin" in df.columns:
        df["op_margin_numeric"] = pd.to_numeric(df["operating_margin"], errors="coerce")
    else:
        df["op_margin_numeric"] = pd.Series([np.nan] * total_records, index=df.index)

    if "net_margin" in df.columns:
        df["net_margin_numeric"] = pd.to_numeric(df["net_margin"], errors="coerce")
    else:
        df["net_margin_numeric"] = pd.Series([np.nan] * total_records, index=df.index)

    # 5. Determine Operating Margin analysis (Primary Profit Margin metric)
    op_valid_mask = df["op_margin_numeric"].notna()
    op_valid_count = int(op_valid_mask.sum())
    op_missing_count = int(total_records - op_valid_count)

    if op_valid_count == 0:
        status = "INSUFFICIENT"
    elif op_valid_count == total_records:
        status = "VALID"
    else:
        status = "PARTIAL"

    # If no valid observations exist for primary operating margin
    if status == "INSUFFICIENT":
        latest_op_margin = None
        op_trend = "Insufficient Data"
        op_consistency = "Insufficient Data"
    else:
        op_valid_series = df.loc[op_valid_mask, "op_margin_numeric"]
        latest_op_margin = float(op_valid_series.iloc[-1])

        # Trend calculation: Higher is better
        if op_valid_count < 2:
            op_trend = "Insufficient Data"
        else:
            earliest_op_margin = float(op_valid_series.iloc[0])
            op_change = latest_op_margin - earliest_op_margin

            if op_change > TREND_TOLERANCE:
                op_trend = "Improving"
            elif op_change < -TREND_TOLERANCE:
                op_trend = "Declining"
            else:
                op_trend = "Stable"

        # Consistency calculation: Sample standard deviation (ddof=1)
        if op_valid_count < 2:
            op_consistency = "Insufficient Data"
        else:
            op_std_dev = float(op_valid_series.std(ddof=1))

            if op_std_dev <= CONSISTENCY_HIGH_MAX_STD:
                op_consistency = "High"
            elif op_std_dev <= CONSISTENCY_MODERATE_MAX_STD:
                op_consistency = "Moderate"
            else:
                op_consistency = "Low"

    # 6. Determine Net Margin analysis
    net_valid_mask = df["net_margin_numeric"].notna()
    net_valid_count = int(net_valid_mask.sum())
    net_missing_count = int(total_records - net_valid_count)

    if net_valid_count == 0:
        latest_net_margin = None
        net_trend = "Insufficient Data"
        net_consistency = "Insufficient Data"
    else:
        net_valid_series = df.loc[net_valid_mask, "net_margin_numeric"]
        latest_net_margin = float(net_valid_series.iloc[-1])

        if net_valid_count < 2:
            net_trend = "Insufficient Data"
        else:
            earliest_net_margin = float(net_valid_series.iloc[0])
            net_change = latest_net_margin - earliest_net_margin

            if net_change > TREND_TOLERANCE:
                net_trend = "Improving"
            elif net_change < -TREND_TOLERANCE:
                net_trend = "Declining"
            else:
                net_trend = "Stable"

        if net_valid_count < 2:
            net_consistency = "Insufficient Data"
        else:
            net_std_dev = float(net_valid_series.std(ddof=1))

            if net_std_dev <= CONSISTENCY_HIGH_MAX_STD:
                net_consistency = "High"
            elif net_std_dev <= CONSISTENCY_MODERATE_MAX_STD:
                net_consistency = "Moderate"
            else:
                net_consistency = "Low"

    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "valid_profit_margin_observations": op_valid_count,
        "missing_profit_margin": op_missing_count,
        "latest_profit_margin": latest_op_margin,
        "profit_margin_trend": op_trend,
        "profit_margin_consistency": op_consistency,
        "valid_operating_margin_observations": op_valid_count,
        "missing_operating_margin": op_missing_count,
        "latest_operating_margin": latest_op_margin,
        "operating_margin_trend": op_trend,
        "operating_margin_consistency": op_consistency,
        "valid_net_margin_observations": net_valid_count,
        "missing_net_margin": net_missing_count,
        "latest_net_margin": latest_net_margin,
        "net_margin_trend": net_trend,
        "net_margin_consistency": net_consistency,
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
    print("PROFIT MARGIN ANALYSIS V1")
    print("==========================================")

    for symbol in test_stocks:
        res = analyze_profit_margin(symbol)

        print(f"\n------------------------------------------")
        print(f"{res['symbol']}")
        print(f"------------------------------------------")
        print(f"Status                        : {res['status']}")
        print(f"Records                       : {res['records']}")
        print(f"Valid Margin observations     : {res['valid_profit_margin_observations']}")
        print(f"Missing Margin                : {res['missing_profit_margin']}")
        op_str = f"{res['latest_operating_margin']:.4f}%" if res['latest_operating_margin'] is not None else "None"
        net_str = f"{res['latest_net_margin']:.4f}%" if res['latest_net_margin'] is not None else "None"
        print(f"Latest Operating Margin       : {op_str}")
        print(f"Operating Margin Trend        : {res['operating_margin_trend']}")
        print(f"Operating Margin Consistency  : {res['operating_margin_consistency']}")
        print(f"Latest Net Margin             : {net_str}")
        print(f"Net Margin Trend              : {res['net_margin_trend']}")
        print(f"Net Margin Consistency        : {res['net_margin_consistency']}")

    print("\n==========================================")
    print("PROFIT MARGIN ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
