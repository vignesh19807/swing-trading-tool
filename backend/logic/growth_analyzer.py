"""
Growth Analysis v1
==================

Logic Engineering layer component for analyzing Revenue Growth and Net Profit Growth.

Purpose:
    Analyze Revenue and Net Profit Growth provided by the Financial Data Service:
    - Primary Metric: Exact Date-Matched YoY Growth (current quarter vs 12 months prior)
    - Secondary Metric: Exact Calendar-Quarter QoQ Growth (current quarter vs prior calendar quarter)
    - Historical YoY Growth Consistency (sample standard deviation of date-matched YoY growth rates)
    - Data quality / completeness status

Architecture:
    Financial Data Service -> Growth Analyzer -> Future Financial Analyzers -> Financial Score

This component is READ-ONLY with respect to data and does NOT:
    - access SQLite directly
    - fetch data from yfinance or external APIs
    - modify database records
    - compute final Financial Score or trading decisions
"""

from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from backend.data_pipeline.financial_service import get_financial_data


# ============================================================
# PROVISIONAL LOGIC THRESHOLDS (v1)
# ============================================================
# Note: These thresholds are initial analysis heuristics for v1.
# They are PROVISIONAL and NOT empirically validated trading rules.

GROWTH_TREND_THRESHOLD_PERCENT = 5.0

CONSISTENCY_HIGH_MAX_STD = 5.0
CONSISTENCY_MODERATE_MAX_STD = 15.0


def _get_yoy_date(date_str: str) -> Optional[str]:
    """Return date string for exact same quarter 12 months prior."""
    try:
        dt = pd.to_datetime(date_str)
        prior_dt = dt.replace(year=dt.year - 1)
        return prior_dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def _get_qoq_date(date_str: str) -> Optional[str]:
    """
    Return date string for exact previous calendar quarter end date:
    - 06-30 -> 03-31
    - 09-30 -> 06-30
    - 12-31 -> 09-30
    - 03-31 -> (year-1)-12-31
    """
    try:
        dt = pd.to_datetime(date_str)
        year = dt.year
        month = dt.month

        if month == 6:
            return f"{year}-03-31"
        elif month == 9:
            return f"{year}-06-30"
        elif month == 12:
            return f"{year}-09-30"
        elif month == 3:
            return f"{year - 1}-12-31"
        else:
            prior_dt = dt - pd.DateOffset(months=3)
            return prior_dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def _calculate_percentage_growth(current: float, prior: float, is_profit: bool = False) -> Optional[float]:
    """
    Calculate growth percentage:
    For Revenue: (current - prior) / prior * 100
    For Profit (handling negative profit transitions): (current - prior) / abs(prior) * 100
    Returns None if prior is 0 or NaN.
    """
    if pd.isna(current) or pd.isna(prior):
        return None
    if prior == 0:
        return None

    if is_profit:
        return float(((current - prior) / abs(prior)) * 100.0)
    else:
        return float(((current - prior) / prior) * 100.0)


def _classify_growth_trend(growth_rate: Optional[float]) -> str:
    """Classify growth rate into Improving, Declining, Stable, or Insufficient Data."""
    if growth_rate is None or pd.isna(growth_rate):
        return "Insufficient Data"
    if growth_rate > GROWTH_TREND_THRESHOLD_PERCENT:
        return "Improving"
    elif growth_rate < -GROWTH_TREND_THRESHOLD_PERCENT:
        return "Declining"
    else:
        return "Stable"


def _classify_growth_consistency(growth_series: List[float]) -> str:
    """Classify sample standard deviation of date-matched YoY growth rates."""
    if len(growth_series) < 2:
        return "Insufficient Data"

    std_dev = float(pd.Series(growth_series).std(ddof=1))
    if std_dev <= CONSISTENCY_HIGH_MAX_STD:
        return "High"
    elif std_dev <= CONSISTENCY_MODERATE_MAX_STD:
        return "Moderate"
    else:
        return "Low"


def _detect_missing_calendar_quarters(df: pd.DataFrame) -> bool:


    """
    Detect whether any expected calendar quarters between the earliest quarter
    and latest quarter in the DataFrame are missing as database rows.
    """
    if df.empty or "quarter_str" not in df.columns:
        return False

    valid_dates = df["quarter_str"].dropna().tolist()
    if len(valid_dates) < 2:
        return False

    sorted_dates = sorted(valid_dates)
    start_dt = pd.to_datetime(sorted_dates[0])
    end_dt = pd.to_datetime(sorted_dates[-1])

    actual_date_set = set(sorted_dates)
    expected_date_set = set()

    curr_dt = start_dt
    while curr_dt <= end_dt:
        expected_date_set.add(curr_dt.strftime("%Y-%m-%d"))
        month = curr_dt.month
        year = curr_dt.year
        if month == 3:
            curr_dt = pd.to_datetime(f"{year}-06-30")
        elif month == 6:
            curr_dt = pd.to_datetime(f"{year}-09-30")
        elif month == 9:
            curr_dt = pd.to_datetime(f"{year}-12-31")
        elif month == 12:
            curr_dt = pd.to_datetime(f"{year + 1}-03-31")
        else:
            curr_dt = curr_dt + pd.DateOffset(months=3)

    return not expected_date_set.issubset(actual_date_set)


def analyze_growth(symbol: str) -> Dict[str, Any]:

    """
    Perform Growth analysis (Revenue Growth & Net Profit Growth) for a stock symbol.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "INFY", "TCS").

    Returns
    -------
    dict
        Structured Growth analysis result.
    """
    # 1. Normalize symbol
    symbol = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "valid_revenue_observations": 0,
        "missing_revenue": 0,
        "latest_revenue": None,
        "revenue_yoy_growth": None,
        "revenue_yoy_trend": "Insufficient Data",
        "revenue_yoy_consistency": "Insufficient Data",
        "revenue_qoq_growth": None,
        "revenue_qoq_trend": "Insufficient Data",
        "valid_net_profit_observations": 0,
        "missing_net_profit": 0,
        "latest_net_profit": None,
        "net_profit_yoy_growth": None,
        "net_profit_yoy_trend": "Insufficient Data",
        "net_profit_yoy_consistency": "Insufficient Data",
        "net_profit_qoq_growth": None,
        "net_profit_qoq_trend": "Insufficient Data",
    }

    # 2. Fetch financial data through Financial Data Service
    data = get_financial_data(symbol)

    if data is None or data.empty:
        return default_result

    df = data.copy()
    total_records = len(df)

    if "quarter" not in df.columns:
        return default_result

    # 3. Sort chronologically by quarter
    df["quarter_dt"] = pd.to_datetime(df["quarter"], errors="coerce")
    if not df["quarter_dt"].isna().all():
        df = df.sort_values(by="quarter_dt", ascending=True)
    else:
        df = df.sort_values(by="quarter", ascending=True)

    df["quarter_str"] = df["quarter_dt"].dt.strftime("%Y-%m-%d")

    # 4. Safe numeric conversions
    if "revenue" in df.columns:
        df["revenue_numeric"] = pd.to_numeric(df["revenue"], errors="coerce")
    else:
        df["revenue_numeric"] = pd.Series([np.nan] * total_records, index=df.index)

    if "net_profit" in df.columns:
        df["net_profit_numeric"] = pd.to_numeric(df["net_profit"], errors="coerce")
    else:
        df["net_profit_numeric"] = pd.Series([np.nan] * total_records, index=df.index)

    rev_valid_mask = df["revenue_numeric"].notna()
    rev_valid_count = int(rev_valid_mask.sum())
    rev_missing_count = int(total_records - rev_valid_count)

    np_valid_mask = df["net_profit_numeric"].notna()
    np_valid_count = int(np_valid_mask.sum())
    np_missing_count = int(total_records - np_valid_count)

    if rev_valid_count == 0 and np_valid_count == 0:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_revenue_observations": 0,
            "missing_revenue": total_records,
            "latest_revenue": None,
            "revenue_yoy_growth": None,
            "revenue_yoy_trend": "Insufficient Data",
            "revenue_yoy_consistency": "Insufficient Data",
            "revenue_qoq_growth": None,
            "revenue_qoq_trend": "Insufficient Data",
            "valid_net_profit_observations": 0,
            "missing_net_profit": total_records,
            "latest_net_profit": None,
            "net_profit_yoy_growth": None,
            "net_profit_yoy_trend": "Insufficient Data",
            "net_profit_yoy_consistency": "Insufficient Data",
            "net_profit_qoq_growth": None,
            "net_profit_qoq_trend": "Insufficient Data",
        }


    date_to_row = {}
    for idx, row in df.iterrows():
        if pd.notna(row["quarter_str"]):
            date_to_row[row["quarter_str"]] = row

    # 5. Identify latest valid record
    latest_rev_row = df[rev_valid_mask].iloc[-1] if rev_valid_count > 0 else None
    latest_np_row = df[np_valid_mask].iloc[-1] if np_valid_count > 0 else None

    latest_row = df[rev_valid_mask | np_valid_mask].iloc[-1]
    latest_quarter_date = latest_row["quarter_str"]

    latest_rev_val = float(latest_rev_row["revenue_numeric"]) if latest_rev_row is not None else None
    latest_np_val = float(latest_np_row["net_profit_numeric"]) if latest_np_row is not None else None

    # 6. Primary Metric: Exact Date-Matched YoY Growth
    target_yoy_date = _get_yoy_date(latest_quarter_date)
    yoy_row = date_to_row.get(target_yoy_date) if target_yoy_date else None

    rev_yoy_growth = None
    net_profit_yoy_growth = None

    if yoy_row is not None:
        prior_rev = yoy_row.get("revenue_numeric")
        prior_np = yoy_row.get("net_profit_numeric")

        if latest_rev_val is not None and pd.notna(prior_rev):
            rev_yoy_growth = _calculate_percentage_growth(latest_rev_val, float(prior_rev), is_profit=False)

        if latest_np_val is not None and pd.notna(prior_np):
            net_profit_yoy_growth = _calculate_percentage_growth(latest_np_val, float(prior_np), is_profit=True)

    rev_yoy_trend = _classify_growth_trend(rev_yoy_growth)
    net_profit_yoy_trend = _classify_growth_trend(net_profit_yoy_growth)

    # 7. Secondary Metric: Exact Calendar-Quarter QoQ Growth
    target_qoq_date = _get_qoq_date(latest_quarter_date)
    qoq_row = date_to_row.get(target_qoq_date) if target_qoq_date else None

    rev_qoq_growth = None
    net_profit_qoq_growth = None

    if qoq_row is not None:
        prior_qoq_rev = qoq_row.get("revenue_numeric")
        prior_qoq_np = qoq_row.get("net_profit_numeric")

        if latest_rev_val is not None and pd.notna(prior_qoq_rev):
            rev_qoq_growth = _calculate_percentage_growth(latest_rev_val, float(prior_qoq_rev), is_profit=False)

        if latest_np_val is not None and pd.notna(prior_qoq_np):
            net_profit_qoq_growth = _calculate_percentage_growth(latest_np_val, float(prior_qoq_np), is_profit=True)

    rev_qoq_trend = _classify_growth_trend(rev_qoq_growth)
    net_profit_qoq_trend = _classify_growth_trend(net_profit_qoq_growth)

    # 8. Historical YoY Growth Series & Consistency
    rev_yoy_series: List[float] = []
    np_yoy_series: List[float] = []

    for idx, row in df.iterrows():
        q_date = row["quarter_str"]
        if not q_date:
            continue
        p_yoy_date = _get_yoy_date(q_date)
        p_row = date_to_row.get(p_yoy_date) if p_yoy_date else None

        if p_row is not None:
            c_rev = row.get("revenue_numeric")
            p_rev = p_row.get("revenue_numeric")
            if pd.notna(c_rev) and pd.notna(p_rev):
                g = _calculate_percentage_growth(float(c_rev), float(p_rev), is_profit=False)
                if g is not None:
                    rev_yoy_series.append(g)

            c_np = row.get("net_profit_numeric")
            p_np = p_row.get("net_profit_numeric")
            if pd.notna(c_np) and pd.notna(p_np):
                g = _calculate_percentage_growth(float(c_np), float(p_np), is_profit=True)
                if g is not None:
                    np_yoy_series.append(g)

    rev_yoy_consistency = _classify_growth_consistency(rev_yoy_series)
    net_profit_yoy_consistency = _classify_growth_consistency(np_yoy_series)

    # 9. Determine Status
    has_missing_calendar_quarters = _detect_missing_calendar_quarters(df)

    if rev_yoy_growth is None and net_profit_yoy_growth is None:
        status = "INSUFFICIENT"
    elif rev_missing_count > 0 or np_missing_count > 0 or has_missing_calendar_quarters:
        status = "PARTIAL"
    elif rev_valid_count == total_records and np_valid_count == total_records:
        status = "VALID"
    else:
        status = "PARTIAL"


    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "valid_revenue_observations": rev_valid_count,
        "missing_revenue": rev_missing_count,
        "latest_revenue": latest_rev_val,
        "revenue_yoy_growth": rev_yoy_growth,
        "revenue_yoy_trend": rev_yoy_trend,
        "revenue_yoy_consistency": rev_yoy_consistency,
        "revenue_qoq_growth": rev_qoq_growth,
        "revenue_qoq_trend": rev_qoq_trend,
        "valid_net_profit_observations": np_valid_count,
        "missing_net_profit": np_missing_count,
        "latest_net_profit": latest_np_val,
        "net_profit_yoy_growth": net_profit_yoy_growth,
        "net_profit_yoy_trend": net_profit_yoy_trend,
        "net_profit_yoy_consistency": net_profit_yoy_consistency,
        "net_profit_qoq_growth": net_profit_qoq_growth,
        "net_profit_qoq_trend": net_profit_qoq_trend,
    }


def main():
    """Run CLI analysis for verified stocks."""
    test_stocks = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("GROWTH ANALYSIS V1")
    print("==========================================")

    for symbol in test_stocks:
        res = analyze_growth(symbol)

        print(f"\n------------------------------------------")
        print(f"{res['symbol']}")
        print(f"------------------------------------------")
        print(f"Status                       : {res['status']}")
        print(f"Records                      : {res['records']}")
        print(f"Valid Revenue observations   : {res['valid_revenue_observations']}")
        print(f"Missing Revenue              : {res['missing_revenue']}")
        rev_str = f"{res['latest_revenue']:,.2f}" if res['latest_revenue'] is not None else "None"
        rev_yoy_str = f"{res['revenue_yoy_growth']:.2f}%" if res['revenue_yoy_growth'] is not None else "None"
        rev_qoq_str = f"{res['revenue_qoq_growth']:.2f}%" if res['revenue_qoq_growth'] is not None else "None"
        print(f"Latest Revenue               : {rev_str}")
        print(f"Revenue YoY Growth           : {rev_yoy_str}")
        print(f"Revenue YoY Trend            : {res['revenue_yoy_trend']}")
        print(f"Revenue YoY Consistency      : {res['revenue_yoy_consistency']}")
        print(f"Revenue QoQ Growth           : {rev_qoq_str}")
        print(f"Revenue QoQ Trend            : {res['revenue_qoq_trend']}")
        print(f"Valid Net Profit obs         : {res['valid_net_profit_observations']}")
        print(f"Missing Net Profit           : {res['missing_net_profit']}")
        np_str = f"{res['latest_net_profit']:,.2f}" if res['latest_net_profit'] is not None else "None"
        np_yoy_str = f"{res['net_profit_yoy_growth']:.2f}%" if res['net_profit_yoy_growth'] is not None else "None"
        np_qoq_str = f"{res['net_profit_qoq_growth']:.2f}%" if res['net_profit_qoq_growth'] is not None else "None"
        print(f"Latest Net Profit            : {np_str}")
        print(f"Net Profit YoY Growth        : {np_yoy_str}")
        print(f"Net Profit YoY Trend         : {res['net_profit_yoy_trend']}")
        print(f"Net Profit YoY Consistency   : {res['net_profit_yoy_consistency']}")
        print(f"Net Profit QoQ Growth        : {np_qoq_str}")
        print(f"Net Profit QoQ Trend         : {res['net_profit_qoq_trend']}")

    print("\n==========================================")
    print("GROWTH ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
