"""
Annual Financial Analysis v1
============================

Logic Engineering layer component for analyzing annual financial records.

Purpose:
    Analyze annual financial statements provided by the Data Engineer:
    - Latest Annual Revenue, Net Profit, EPS, ROE, ROCE
    - Trend analysis (Improving, Declining, Stable) across consecutive annual periods
    - CAGR (Compound Annual Growth Rate) calculation for Revenue and Net Profit
    - Safe handling of missing/NaN values
    - Strict chronology enforcement

Architecture:
    Data Engineering Layer -> Annual Financial Analyzer -> Financial Engine

This component is READ-ONLY and PURE LOGIC. It does NOT:
    - access SQLite directly
    - fetch data from yfinance or external APIs
    - modify database records
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


# Provisional thresholds for Annual Trends (v1 heuristics)
GROWTH_TREND_THRESHOLD_PERCENT = 5.0
TREND_TOLERANCE_PERCENT = 2.0


def calculate_cagr(start_value: float, end_value: float, years: float) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate (CAGR).
    Returns result as a percentage.
    Safely handles invalid, zero, or negative starting values by returning None.
    """
    if pd.isna(start_value) or pd.isna(end_value) or pd.isna(years):
        return None
    if start_value is None or end_value is None or years is None:
        return None
    if start_value <= 0 or years <= 0:
        return None

    try:
        cagr_decimal = ((float(end_value) / float(start_value)) ** (1.0 / float(years))) - 1.0
        return float(cagr_decimal * 100.0)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def _calculate_percentage_growth(current: float, prior: float, is_profit: bool = False) -> Optional[float]:
    """Calculate percentage growth safely."""
    if pd.isna(current) or pd.isna(prior):
        return None
    if prior == 0:
        return None

    if is_profit:
        return float(((current - prior) / abs(prior)) * 100.0)
    else:
        return float(((current - prior) / prior) * 100.0)


def _classify_growth_trend(growth_rate: Optional[float], threshold: float = GROWTH_TREND_THRESHOLD_PERCENT) -> str:
    """Classify growth rate into Improving, Declining, Stable, or Insufficient Data."""
    if growth_rate is None or pd.isna(growth_rate):
        return "Insufficient Data"
    if growth_rate > threshold:
        return "Improving"
    elif growth_rate < -threshold:
        return "Declining"
    else:
        return "Stable"


def _extract_metric(df: pd.DataFrame, column: str) -> Tuple[Optional[float], Optional[float], str]:
    """
    Extract latest value, YoY growth, and trend for a given metric.
    Returns (latest_value, yoy_growth, trend)
    """
    if column not in df.columns:
        return None, None, "Insufficient Data"

    df[f"{column}_numeric"] = pd.to_numeric(df[column], errors="coerce")
    valid_series = df.loc[df[f"{column}_numeric"].notna(), f"{column}_numeric"]

    if valid_series.empty:
        return None, None, "Insufficient Data"

    latest_val = float(valid_series.iloc[-1])

    if len(valid_series) < 2:
        return latest_val, None, "Insufficient Data"

    prior_val = float(valid_series.iloc[-2])
    is_profit = column in ["net_profit", "eps"]
    growth = _calculate_percentage_growth(latest_val, prior_val, is_profit=is_profit)

    threshold = TREND_TOLERANCE_PERCENT if column in ["roe", "roce"] else GROWTH_TREND_THRESHOLD_PERCENT
    trend = _classify_growth_trend(growth, threshold)

    return latest_val, growth, trend


def _extract_cagr(df: pd.DataFrame, column: str) -> Optional[float]:
    """Extract actual elapsed years and calculate CAGR for a given metric."""
    if column not in df.columns or "period_dt" not in df.columns:
        return None

    df[f"{column}_numeric"] = pd.to_numeric(df[column], errors="coerce")
    valid_df = df.loc[df[f"{column}_numeric"].notna() & df["period_dt"].notna()].sort_values("period_dt")

    if len(valid_df) < 2:
        return None

    earliest_record = valid_df.iloc[0]
    latest_record = valid_df.iloc[-1]

    start_val = float(earliest_record[f"{column}_numeric"])
    end_val = float(latest_record[f"{column}_numeric"])

    start_date = earliest_record["period_dt"]
    end_date = latest_record["period_dt"]

    days_diff = (end_date - start_date).days
    years = days_diff / 365.25

    return calculate_cagr(start_val, end_val, years)


def analyze_annual_financials(annual_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform pure logic analysis on standardized annual financial records.

    Parameters
    ----------
    annual_records : list of dict
        List of dictionaries conforming to the annual input contract:
        - symbol (str)
        - period (str, ISO YYYY-MM-DD)
        - revenue (float | None)
        - net_profit (float | None)
        - eps (float | None)
        - roe (float | None)
        - roce (float | None)

    Returns
    -------
    dict
        Structured annual analysis result.
    """
    symbol = "UNKNOWN"
    if annual_records and isinstance(annual_records, list) and len(annual_records) > 0:
        if isinstance(annual_records[0], dict) and "symbol" in annual_records[0]:
            symbol = str(annual_records[0]["symbol"]).strip().upper()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "latest_period": None,
        "latest_revenue": None,
        "revenue_yoy_growth": None,
        "revenue_trend": "Insufficient Data",
        "revenue_cagr": None,
        "latest_net_profit": None,
        "net_profit_yoy_growth": None,
        "net_profit_trend": "Insufficient Data",
        "net_profit_cagr": None,
        "latest_eps": None,
        "eps_yoy_growth": None,
        "eps_trend": "Insufficient Data",
        "latest_roe": None,
        "roe_yoy_change": None,
        "roe_trend": "Insufficient Data",
        "latest_roce": None,
        "roce_yoy_change": None,
        "roce_trend": "Insufficient Data",
    }

    if not annual_records or not isinstance(annual_records, list):
        return default_result

    df = pd.DataFrame(annual_records)

    if df.empty or "period" not in df.columns:
        return default_result

    # Ensure chronological sorting
    df["period_dt"] = pd.to_datetime(df["period"], errors="coerce")

    # If all dates are invalid, we can't reliably sort/analyze
    if df["period_dt"].isna().all():
        return default_result

    df = df.dropna(subset=["period_dt"]).sort_values(by="period_dt", ascending=True).reset_index(drop=True)
    total_records = len(df)

    if total_records == 0:
        return default_result

    latest_period = df["period_dt"].dt.strftime("%Y-%m-%d").iloc[-1]

    # Revenue
    latest_rev, rev_growth, rev_trend = _extract_metric(df, "revenue")
    rev_cagr = _extract_cagr(df, "revenue")

    # Net Profit
    latest_np, np_growth, np_trend = _extract_metric(df, "net_profit")
    np_cagr = _extract_cagr(df, "net_profit")

    # EPS
    latest_eps, eps_growth, eps_trend = _extract_metric(df, "eps")

    # ROE
    latest_roe, roe_growth, roe_trend = _extract_metric(df, "roe")

    # ROCE
    latest_roce, roce_growth, roce_trend = _extract_metric(df, "roce")

    # Determine status
    if total_records >= 2 and latest_rev is not None and latest_np is not None:
        status = "VALID"
    elif total_records > 0:
        status = "PARTIAL"
    else:
        status = "INSUFFICIENT"

    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "latest_period": latest_period,
        "latest_revenue": latest_rev,
        "revenue_yoy_growth": rev_growth,
        "revenue_trend": rev_trend,
        "revenue_cagr": rev_cagr,
        "latest_net_profit": latest_np,
        "net_profit_yoy_growth": np_growth,
        "net_profit_trend": np_trend,
        "net_profit_cagr": np_cagr,
        "latest_eps": latest_eps,
        "eps_yoy_growth": eps_growth,
        "eps_trend": eps_trend,
        "latest_roe": latest_roe,
        "roe_yoy_change": roe_growth,
        "roe_trend": roe_trend,
        "latest_roce": latest_roce,
        "roce_yoy_change": roce_growth,
        "roce_trend": roce_trend,
    }
