"""
Volatility Analyzer Module (v1)
================================

Provides price-based Volatility Analysis for stock market data.

Consumes historical daily market price data strictly via:
`from backend.data_pipeline.data_service import get_stock_data`

Calculates Core Metrics:
1. volatility_20d_annualized : 20-Day Annualized Historical Volatility (%)
2. volatility_60d_annualized : 60-Day Annualized Historical Volatility (%)
3. max_drawdown_60d         : 60-Day Maximum Drawdown (%)
4. atr_14                   : 14-Day Average True Range
5. atr_percent              : 14-Day ATR as % of Latest Close

Status Rules:
- INSUFFICIENT : < 21 valid positive close price observations
- PARTIAL      : 21 <= valid observations < 61 (or missing required ATR data)
- VALID        : >= 61 valid observations with all metrics successfully computed

Author: Logic Engineer
"""

import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import calculate_atr


# ============================================================
# PROVISIONAL LOGIC THRESHOLDS (v1)
# ============================================================

VOLATILITY_TREND_DELTA_THRESHOLD = 2.0  # Percentage point difference for trend classification

VOLATILITY_LOW_MAX_HV20 = 15.0         # HV20 <= 15.0% -> Low
VOLATILITY_MODERATE_MAX_HV20 = 30.0    # 15.0% < HV20 <= 30.0% -> Moderate


def analyze_volatility(symbol: str) -> Dict[str, Any]:
    """
    Perform Volatility analysis (HV20, HV60, MaxDD60, ATR14, ATR%) for a stock symbol.

    Parameters
    ----------
    symbol : str
        NSE stock symbol, for example "INFY".

    Returns
    -------
    dict
        Structured analysis dictionary:
        {
            "symbol": str,
            "status": str,  # "VALID", "PARTIAL", or "INSUFFICIENT"
            "records": int,
            "valid_price_observations": int,
            "missing_price_observations": int,
            "latest_close": float or None,
            "volatility_20d_annualized": float or None,
            "volatility_60d_annualized": float or None,
            "volatility_trend": str,
            "volatility_classification": str,
            "max_drawdown_60d": float or None,
            "atr_14": float or None,
            "atr_percent": float or None
        }
    """
    # 1. Normalize Symbol
    if not isinstance(symbol, str):
        symbol = str(symbol) if symbol is not None else ""
    symbol_clean = symbol.upper().strip()

    default_result: Dict[str, Any] = {
        "symbol": symbol_clean,
        "status": "INSUFFICIENT",
        "records": 0,
        "valid_price_observations": 0,
        "missing_price_observations": 0,
        "latest_close": None,
        "volatility_20d_annualized": None,
        "volatility_60d_annualized": None,
        "volatility_trend": "Insufficient Data",
        "volatility_classification": "Insufficient Data",
        "max_drawdown_60d": None,
        "atr_14": None,
        "atr_percent": None,
    }

    if not symbol_clean:
        return default_result

    # 2. Fetch Data from Data Service
    try:
        df = get_stock_data(symbol_clean)
    except Exception:
        return default_result

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return default_result

    total_records = int(len(df))

    # Validate required columns
    required_cols = {"date", "close"}
    if not required_cols.issubset(set(df.columns)):
        return default_result

    # 3. Sort Chronologically & Deduplicate Dates
    df_clean = df.copy()
    df_clean["date_dt"] = pd.to_datetime(df_clean["date"], errors="coerce")
    df_clean = df_clean.dropna(subset=["date_dt"])
    df_clean = df_clean.sort_values("date_dt", ascending=True)
    df_clean = df_clean.drop_duplicates(subset=["date_dt"], keep="last")

    # 4. Numeric Conversion & Positive Price Validation
    df_clean["close_num"] = pd.to_numeric(df_clean["close"], errors="coerce")
    valid_df = df_clean[df_clean["close_num"] > 0].copy()

    valid_obs_count = int(len(valid_df))
    missing_obs_count = int(total_records - valid_obs_count)

    # If fewer than 21 valid positive close price observations -> INSUFFICIENT
    if valid_obs_count < 21:
        return {
            "symbol": symbol_clean,
            "status": "INSUFFICIENT",
            "records": total_records,
            "valid_price_observations": valid_obs_count,
            "missing_price_observations": missing_obs_count,
            "latest_close": None,
            "volatility_20d_annualized": None,
            "volatility_60d_annualized": None,
            "volatility_trend": "Insufficient Data",
            "volatility_classification": "Insufficient Data",
            "max_drawdown_60d": None,
            "atr_14": None,
            "atr_percent": None,
        }

    latest_close_val = float(valid_df["close_num"].iloc[-1])

    # 5. Logarithmic Returns Calculation
    valid_df["log_return"] = np.log(valid_df["close_num"] / valid_df["close_num"].shift(1))
    valid_returns = valid_df["log_return"].dropna().tolist()

    # 6. 20-Day Annualized Historical Volatility (HV20)
    hv_20: Optional[float] = None
    if len(valid_returns) >= 20:
        recent_20_returns = valid_returns[-20:]
        std_20 = float(pd.Series(recent_20_returns).std(ddof=1))
        hv_20 = float(std_20 * math.sqrt(252.0) * 100.0)

    # 7. 60-Day Annualized Historical Volatility (HV60)
    hv_60: Optional[float] = None
    if len(valid_returns) >= 60:
        recent_60_returns = valid_returns[-60:]
        std_60 = float(pd.Series(recent_60_returns).std(ddof=1))
        hv_60 = float(std_60 * math.sqrt(252.0) * 100.0)

    # 8. 60-Day Maximum Drawdown (MaxDD60)
    max_dd_60: Optional[float] = None
    if valid_obs_count >= 60:
        p60 = valid_df["close_num"].iloc[-60:]
        running_peak = p60.cummax()
        drawdown = ((p60 - running_peak) / running_peak) * 100.0
        max_dd_60 = float(drawdown.min())

    # 9. ATR-14 and ATR% Calculation
    atr_14: Optional[float] = None
    atr_percent: Optional[float] = None

    if {"high", "low"}.issubset(set(valid_df.columns)):
        valid_df["high_num"] = pd.to_numeric(valid_df["high"], errors="coerce")
        valid_df["low_num"] = pd.to_numeric(valid_df["low"], errors="coerce")

        atr_valid_df = valid_df.dropna(subset=["high_num", "low_num", "close_num"]).copy()

        if len(atr_valid_df) >= 15:
            try:
                atr_series = calculate_atr(
                    atr_valid_df["high_num"],
                    atr_valid_df["low_num"],
                    atr_valid_df["close_num"],
                    period=14
                )
                latest_atr = atr_series.iloc[-1]
                if pd.notna(latest_atr):
                    atr_14 = float(latest_atr)
                    atr_percent = float((atr_14 / latest_close_val) * 100.0)
            except Exception:
                atr_14 = None
                atr_percent = None

    # 10. Volatility Trend Classification
    volatility_trend: str = "Insufficient Data"
    if hv_20 is not None and hv_60 is not None:
        delta = hv_20 - hv_60
        if delta > VOLATILITY_TREND_DELTA_THRESHOLD:
            volatility_trend = "Expanding"
        elif delta < -VOLATILITY_TREND_DELTA_THRESHOLD:
            volatility_trend = "Contracting"
        else:
            volatility_trend = "Stable"

    # 11. Volatility Classification
    volatility_classification: str = "Insufficient Data"
    if hv_20 is not None:
        if hv_20 <= VOLATILITY_LOW_MAX_HV20:
            volatility_classification = "Low"
        elif hv_20 <= VOLATILITY_MODERATE_MAX_HV20:
            volatility_classification = "Moderate"
        else:
            volatility_classification = "High"

    # 12. Determine Status
    if valid_obs_count < 21 or hv_20 is None:
        status = "INSUFFICIENT"
    elif valid_obs_count < 61 or hv_60 is None or max_dd_60 is None or atr_14 is None:
        status = "PARTIAL"
    else:
        status = "VALID"

    # 13. Return Formatted Dictionary with 4 Decimal Precision
    return {
        "symbol": symbol_clean,
        "status": status,
        "records": total_records,
        "valid_price_observations": valid_obs_count,
        "missing_price_observations": missing_obs_count,
        "latest_close": round(latest_close_val, 4) if latest_close_val is not None else None,
        "volatility_20d_annualized": round(hv_20, 4) if hv_20 is not None else None,
        "volatility_60d_annualized": round(hv_60, 4) if hv_60 is not None else None,
        "volatility_trend": volatility_trend,
        "volatility_classification": volatility_classification,
        "max_drawdown_60d": round(max_dd_60, 4) if max_dd_60 is not None else None,
        "atr_14": round(atr_14, 4) if atr_14 is not None else None,
        "atr_percent": round(atr_percent, 4) if atr_percent is not None else None,
    }


def main():
    """CLI runner to display Volatility metrics for key platform stocks."""
    test_symbols = ["INFY", "TCS", "WIPRO", "RELIANCE", "HDFCBANK"]
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("VOLATILITY ANALYSIS V1")
    print("==========================================")

    for symbol in test_symbols:
        res = analyze_volatility(symbol)
        print(f"\n------------------------------------------")
        print(f"{symbol}")
        print(f"------------------------------------------")
        print(f"Status                       : {res['status']}")
        print(f"Records                      : {res['records']}")
        print(f"Valid Price Observations     : {res['valid_price_observations']}")
        print(f"Missing Price Observations   : {res['missing_price_observations']}")
        print(f"Latest Close                 : {res['latest_close']:,.2f}" if res['latest_close'] else "Latest Close                 : None")
        print(f"Volatility 20d Annualized    : {res['volatility_20d_annualized']:.2f}%" if res['volatility_20d_annualized'] is not None else "Volatility 20d Annualized    : None")
        print(f"Volatility 60d Annualized    : {res['volatility_60d_annualized']:.2f}%" if res['volatility_60d_annualized'] is not None else "Volatility 60d Annualized    : None")
        print(f"Volatility Trend             : {res['volatility_trend']}")
        print(f"Volatility Classification    : {res['volatility_classification']}")
        print(f"Max Drawdown (60d)           : {res['max_drawdown_60d']:.2f}%" if res['max_drawdown_60d'] is not None else "Max Drawdown (60d)           : None")
        print(f"ATR (14)                     : {res['atr_14']:,.2f}" if res['atr_14'] is not None else "ATR (14)                     : None")
        print(f"ATR %                        : {res['atr_percent']:.2f}%" if res['atr_percent'] is not None else "ATR %                        : None")

    print("\n==========================================")
    print("VOLATILITY ANALYSIS COMPLETE")
    print("==========================================")


if __name__ == "__main__":
    main()
