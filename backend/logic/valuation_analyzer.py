"""
Valuation Analyzer v1
=====================

Logic Engineering layer component for analyzing Valuation metrics:
- latest_close : Most recent market close price
- ttm_eps      : Trailing Twelve Months Earnings Per Share (latest 4 valid quarterly EPS)
- pe_ratio     : Price to Earnings Ratio (latest_close / ttm_eps)
- earnings_yield : Earnings Yield % ((ttm_eps / latest_close) * 100.0)
- valuation_classification : Qualitative valuation assessment

Architecture:
    Financial & Market Data Services -> Valuation Analyzer -> Financial Score

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
from backend.data_pipeline.data_service import get_stock_data


# ============================================================
# PROVISIONAL LOGIC THRESHOLDS (v1)
# ============================================================
# Note: These thresholds are initial analysis heuristics for v1.
# They are PROVISIONAL and NOT empirically validated trading rules.

PE_UNDERVALUED_MAX = 15.0
PE_FAIRLY_VALUED_MAX = 25.0


def analyze_valuation(symbol: str) -> Dict[str, Any]:
    """
    Perform Valuation analysis (latest_close, ttm_eps, pe_ratio, earnings_yield,
    valuation_classification) for a stock symbol.

    Parameters
    ----------
    symbol : str
        Stock ticker symbol (e.g. "INFY", "TCS").

    Returns
    -------
    dict
        Structured Valuation analysis result containing:
        - symbol (str)
        - status (str): "VALID", "PARTIAL", or "INSUFFICIENT"
        - records (int): Total financial records returned
        - valid_eps_observations (int): Count of valid non-NaN EPS observations
        - missing_eps_observations (int): Count of missing/NaN EPS observations
        - latest_close (float or None): Most recent valid close price
        - ttm_eps (float or None): Sum of latest 4 valid quarterly EPS observations
        - pe_ratio (float or None): P/E ratio (latest_close / ttm_eps)
        - earnings_yield (float or None): Earnings yield % ((ttm_eps / latest_close) * 100.0)
        - valuation_classification (str): "Undervalued", "Fairly Valued", "Overvalued",
                                          "Unprofitable", or "Insufficient Data"
    """

    # 1. Normalize symbol
    symbol = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INSUFFICIENT",
        "records": 0,
        "valid_eps_observations": 0,
        "missing_eps_observations": 0,
        "latest_close": None,
        "ttm_eps": None,
        "pe_ratio": None,
        "earnings_yield": None,
        "valuation_classification": "Insufficient Data",
    }

    # 2. Get financial data through Financial Data Service
    fin_data = get_financial_data(symbol)

    if fin_data is None or fin_data.empty:
        return default_result

    # Avoid mutating incoming DataFrame
    df = fin_data.copy()
    total_records = len(df)

    if "eps" not in df.columns:
        return {
            **default_result,
            "records": total_records,
        }

    # 3. Numeric coercion & Chronological sorting
    if "quarter" in df.columns:
        df["quarter_dt"] = pd.to_datetime(df["quarter"], errors="coerce")
        if not df["quarter_dt"].isna().all():
            df = df.sort_values(by="quarter_dt", ascending=True)
        else:
            df = df.sort_values(by="quarter", ascending=True)

        # Drop duplicate quarters keeping last observation
        df = df.drop_duplicates(subset=["quarter"], keep="last")

    df["eps_numeric"] = pd.to_numeric(df["eps"], errors="coerce")

    # 4. Valid EPS series (non-NaN)
    valid_series = df.loc[df["eps_numeric"].notna(), "eps_numeric"]
    valid_count = int(len(valid_series))
    missing_count = int(total_records - valid_count)

    # If fewer than 4 valid EPS observations, valuation cannot be calculated safely
    if valid_count < 4:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_eps_observations": valid_count,
            "missing_eps_observations": missing_count,
            "latest_close": None,
            "ttm_eps": None,
            "pe_ratio": None,
            "earnings_yield": None,
            "valuation_classification": "Insufficient Data",
        }

    # 5. Calculate TTM EPS from the latest 4 valid quarterly observations
    latest_4_eps = valid_series.iloc[-4:]
    ttm_eps_val = float(latest_4_eps.sum())
    ttm_eps = round(ttm_eps_val, 4)

    # 6. Retrieve Market Data
    stock_data = get_stock_data(symbol)

    if stock_data is None or stock_data.empty:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_eps_observations": valid_count,
            "missing_eps_observations": missing_count,
            "latest_close": None,
            "ttm_eps": ttm_eps,
            "pe_ratio": None,
            "earnings_yield": None,
            "valuation_classification": "Insufficient Data",
        }

    stock_df = stock_data.copy()

    if "close" not in stock_df.columns or stock_df["close"].empty:
        latest_close = None
    else:
        stock_df["close_numeric"] = pd.to_numeric(stock_df["close"], errors="coerce")
        valid_closes = stock_df["close_numeric"].dropna()
        if valid_closes.empty or float(valid_closes.iloc[-1]) <= 0:
            latest_close = None
        else:
            latest_close = round(float(valid_closes.iloc[-1]), 4)

    if latest_close is None:
        return {
            "symbol": symbol,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_eps_observations": valid_count,
            "missing_eps_observations": missing_count,
            "latest_close": None,
            "ttm_eps": ttm_eps,
            "pe_ratio": None,
            "earnings_yield": None,
            "valuation_classification": "Insufficient Data",
        }

    # 7. INFY Unit Mismatch Detection
    # INFY stored EPS represents USD ADR-per-share while market close is in INR.
    is_infy_mismatch = (symbol == "INFY") or (ttm_eps < 1.0 and latest_close > 100.0 and symbol == "INFY")

    # 8. Valuation Metrics & Classification Calculation
    if is_infy_mismatch:
        pe_ratio = None
        earnings_yield = None
        valuation_classification = "Insufficient Data"
        status = "PARTIAL"
    elif ttm_eps < 0:
        pe_ratio = None
        earnings_yield = None
        valuation_classification = "Unprofitable"
        status = "PARTIAL"
    elif ttm_eps == 0:
        pe_ratio = None
        earnings_yield = None
        valuation_classification = "Insufficient Data"
        status = "PARTIAL"
    else:
        # ttm_eps > 0 and latest_close > 0
        pe_val = latest_close / ttm_eps
        pe_ratio = round(float(pe_val), 4)

        ey_val = (ttm_eps / latest_close) * 100.0
        earnings_yield = round(float(ey_val), 4)

        if pe_ratio < PE_UNDERVALUED_MAX:
            valuation_classification = "Undervalued"
        elif pe_ratio <= PE_FAIRLY_VALUED_MAX:
            valuation_classification = "Fairly Valued"
        else:
            valuation_classification = "Overvalued"

        if valid_count == total_records and not is_infy_mismatch:
            status = "VALID"
        else:
            status = "PARTIAL"

    return {
        "symbol": symbol,
        "status": status,
        "records": total_records,
        "valid_eps_observations": valid_count,
        "missing_eps_observations": missing_count,
        "latest_close": latest_close,
        "ttm_eps": ttm_eps,
        "pe_ratio": pe_ratio,
        "earnings_yield": earnings_yield,
        "valuation_classification": valuation_classification,
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
    print("VALUATION ANALYZER V1")
    print("==========================================")

    for symbol in test_stocks:
        res = analyze_valuation(symbol)

        print(f"\n------------------------------------------")
        print(f"{res['symbol']}")
        print(f"------------------------------------------")
        print(f"Status                 : {res['status']}")
        print(f"Records                : {res['records']}")
        print(f"Valid EPS observations : {res['valid_eps_observations']}")
        print(f"Missing EPS            : {res['missing_eps_observations']}")
        close_str = f"{res['latest_close']:.4f}" if res['latest_close'] is not None else "None"
        print(f"Latest Close           : {close_str}")
        ttm_str = f"{res['ttm_eps']:.4f}" if res['ttm_eps'] is not None else "None"
        print(f"TTM EPS                : {ttm_str}")
        pe_str = f"{res['pe_ratio']:.4f}" if res['pe_ratio'] is not None else "None"
        print(f"P/E Ratio              : {pe_str}")
        ey_str = f"{res['earnings_yield']:.4f}%" if res['earnings_yield'] is not None else "None"
        print(f"Earnings Yield         : {ey_str}")
        print(f"Valuation Class        : {res['valuation_classification']}")

    print("\n==========================================")
    print("VALUATION ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
