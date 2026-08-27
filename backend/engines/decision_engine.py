"""
Decision Engine V1 (Engine 7)
=============================

Calculates the composite Opportunity Score (0.0 to 100.0) for a stock symbol
by combining Technical, Financial, and Momentum scores.

Weighting Model:
----------------
- Technical Score = 40% (via Technical Analysis Engine)
- Financial Score = 35% (via Financial Health Aggregator Engine)
- Momentum Score  = 25% (derived from Technical RSI & MACD sub-scores)

Double-Counting Overlap Warning:
-------------------------------
Momentum is derived directly from Technical Engine's RSI Score (max 30 pts)
and MACD Score (max 30 pts). Since Technical Score already incorporates
RSI (30%) and MACD (30%), the combined total influence of RSI and MACD
in the final Opportunity Score is:
    Technical contribution: 40% * 60% = 24%
    Momentum contribution: 25% * 100% = 25%
    Combined RSI / MACD influence = 49% of final Opportunity Score.
This overlap is documented, intentional, and accepted for V1.

Author: Logic Engineer
"""

import math
from typing import Any, Dict, Optional

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import run_technical_pipeline


def calculate_opportunity_score(symbol: str, evaluation_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate composite Opportunity Score (0-100) and actionable recommendation
    for a stock ticker symbol.

    Parameters
    ----------
    symbol : str
        NSE stock ticker symbol (e.g. "TCS", "INFY").

    Returns
    -------
    Dict[str, Any]
        Dictionary matching the public API output contract:
        {
            "symbol": str,
            "status": "VALID" | "PARTIAL" | "INSUFFICIENT",
            "technical_score": float | None,
            "financial_score": float | None,
            "momentum_score": float | None,
            "opportunity_score": float | None,
            "recommendation": "BUY" | "WATCH" | "HOLD" | "AVOID" | "INSUFFICIENT_DATA"
        }
    """
    # Import financial_engine lazily inside function to prevent circular import chains
    from backend.engines.financial_engine import analyze_financial_health

    # 1. Symbol Normalization & Validation
    if symbol is None or not isinstance(symbol, str):
        symbol_clean = ""
    else:
        symbol_clean = symbol.strip().upper()

    if not symbol_clean:
        return {
            "symbol": symbol_clean,
            "status": "INSUFFICIENT",
            "technical_score": None,
            "financial_score": None,
            "momentum_score": None,
            "opportunity_score": None,
            "recommendation": "INSUFFICIENT_DATA",
        }

    # 2. Retrieve Financial Health Result safely
    financial_score = None
    financial_status = "INSUFFICIENT"
    try:
        financial_res = analyze_financial_health(symbol_clean, evaluation_date=evaluation_date)
        if isinstance(financial_res, dict):
            financial_score = financial_res.get("overall_score")
            financial_status = financial_res.get("status", "INSUFFICIENT")
    except Exception:
        financial_score = None
        financial_status = "INSUFFICIENT"

    # Validate financial_score is numeric non-NaN
    if financial_score is not None:
        try:
            val = float(financial_score)
            if math.isnan(val) or math.isinf(val):
                financial_score = None
            else:
                financial_score = val
        except (ValueError, TypeError):
            financial_score = None

    # 3. Retrieve Technical Engine Result safely
    technical_score = None
    rsi_score = None
    macd_score = None
    technical_status = "INSUFFICIENT"

    try:
        df = get_stock_data(symbol_clean, end_date=evaluation_date)
        if df is not None and not df.empty and len(df) >= 20:
            tech_pipeline = run_technical_pipeline(df)
            indicators = tech_pipeline.get("indicators")
            if indicators is not None and not indicators.empty:
                latest_row = indicators.iloc[-1]

                raw_tech = latest_row.get("technical_score")
                if raw_tech is not None and not math.isnan(float(raw_tech)):
                    technical_score = round(float(raw_tech), 4)
                    technical_status = "VALID"

                raw_rsi = latest_row.get("rsi_score")
                if raw_rsi is not None and not math.isnan(float(raw_rsi)):
                    rsi_score = float(raw_rsi)

                raw_macd = latest_row.get("macd_score")
                if raw_macd is not None and not math.isnan(float(raw_macd)):
                    macd_score = float(raw_macd)
    except Exception:
        technical_score = None
        technical_status = "INSUFFICIENT"

    # 4. Derive Momentum Score
    momentum_score = None
    if rsi_score is not None and macd_score is not None:
        momentum_score = round(((rsi_score + macd_score) / 60.0) * 100.0, 4)

    # 5. Core Mandatory Component Check
    # If technical_score is None OR financial_score is None -> INSUFFICIENT
    if technical_score is None or financial_score is None:
        return {
            "symbol": symbol_clean,
            "status": "INSUFFICIENT",
            "technical_score": technical_score,
            "financial_score": financial_score,
            "momentum_score": momentum_score,
            "opportunity_score": None,
            "recommendation": "INSUFFICIENT_DATA",
        }

    # 6. Calculate Opportunity Score
    if momentum_score is not None:
        raw_opp = (
            (technical_score * 0.40)
            + (financial_score * 0.35)
            + (momentum_score * 0.25)
        )
        opportunity_score = round(raw_opp, 4)
    else:
        # Fallback Dynamic Re-Weighting (Momentum missing, but Tech + Fin available)
        # Effective W_tech = 0.40 / 0.75 = 0.5333333333333333
        # Effective W_fin  = 0.35 / 0.75 = 0.4666666666666667
        w_tech = 0.40 / 0.75
        w_fin = 0.35 / 0.75
        raw_opp = (technical_score * w_tech) + (financial_score * w_fin)
        opportunity_score = round(raw_opp, 4)

    # Clamp opportunity_score to [0.0, 100.0]
    opportunity_score = max(0.0, min(100.0, opportunity_score))

    # 7. Recommendation Rules
    if opportunity_score >= 75.0:
        recommendation = "BUY"
    elif opportunity_score >= 60.0:
        recommendation = "WATCH"
    elif opportunity_score >= 45.0:
        recommendation = "HOLD"
    else:
        recommendation = "AVOID"

    # 8. Status Propagation Rules (Rule C)
    if (
        technical_status == "VALID"
        and financial_status == "VALID"
        and momentum_score is not None
    ):
        status = "VALID"
    else:
        status = "PARTIAL"

    return {
        "symbol": symbol_clean,
        "status": status,
        "technical_score": technical_score,
        "financial_score": financial_score,
        "momentum_score": momentum_score,
        "opportunity_score": opportunity_score,
        "recommendation": recommendation,
    }
