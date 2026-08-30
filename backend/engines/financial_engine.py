"""
Financial Health Score Aggregator Engine V1
===========================================

Combines individual financial logic analyzer results (ROE, ROCE, Debt/Equity,
Profit Margin, Growth, Valuation) into a standardized Financial Health Score (0 - 100).

Architectural Constraints:
- Consumes logic analyzers as read-only dependencies.
- No direct SQLite access.
- No yfinance or external API requests.
- Input data immutability.
- Deterministic 4-decimal precision calculations.

Author: Logic Engineer
"""

from typing import Any, Dict, Optional
import math
import pandas as pd



def _is_invalid(val: Any) -> bool:
    """Helper to check if a numeric value is None, NaN, or infinite."""
    if val is None:
        return True
    try:
        f = float(val)
        return math.isnan(f) or math.isinf(f)
    except (ValueError, TypeError):
        return True


def _normalize_roe(roe: Optional[float]) -> Optional[float]:
    """
    Piecewise linear normalization for Return on Equity (ROE).
    ROE is provided as a float decimal (e.g. 0.15 for 15%).
    - roe <= 0.0 -> 0.0
    - 0.0 < roe <= 0.10 -> 0.0 to 60.0
    - 0.10 < roe <= 0.15 -> 60.0 to 80.0
    - 0.15 < roe <= 0.20 -> 80.0 to 100.0
    - roe > 0.20 -> 100.0
    """
    if _is_invalid(roe):
        return None
    f = float(roe)
    if f <= 0.0:
        return 0.0
    elif f <= 0.10:
        return round((f / 0.10) * 60.0, 4)
    elif f <= 0.15:
        return round(60.0 + ((f - 0.10) / 0.05) * 20.0, 4)
    elif f <= 0.20:
        return round(80.0 + ((f - 0.15) / 0.05) * 20.0, 4)
    else:
        return 100.0


def _normalize_roce(roce: Optional[float]) -> Optional[float]:
    """
    Piecewise linear normalization for Return on Capital Employed (ROCE).
    Normalizes input float to percentage p (e.g. 8.01 for 8.01%).
    - p <= 0.0 -> 0.0
    - 0.0 < p <= 10.0 -> 0.0 to 60.0
    - 10.0 < p <= 15.0 -> 60.0 to 80.0
    - 15.0 < p <= 20.0 -> 80.0 to 100.0
    - p > 20.0 -> 100.0
    """
    if _is_invalid(roce):
        return None
    p = float(roce)
    if p <= 1.0:
        p = p * 100.0
    if p <= 0.0:
        return 0.0
    elif p <= 10.0:
        return round((p / 10.0) * 60.0, 4)
    elif p <= 15.0:
        return round(60.0 + ((p - 10.0) / 5.0) * 20.0, 4)
    elif p <= 20.0:
        return round(80.0 + ((p - 15.0) / 5.0) * 20.0, 4)
    else:
        return 100.0


def _normalize_margin(margin: Optional[float]) -> Optional[float]:
    """
    Piecewise linear normalization for Net Margin.
    Input m is a percentage (e.g. 16.012 for 16.012%).
    - m <= 0.0 -> 0.0
    - 0.0 < m <= 5.0 -> 0.0 to 40.0
    - 5.0 < m <= 10.0 -> 40.0 to 60.0
    - 10.0 < m <= 15.0 -> 60.0 to 80.0
    - 15.0 < m <= 20.0 -> 80.0 to 100.0
    - m > 20.0 -> 100.0
    """
    if _is_invalid(margin):
        return None
    m = float(margin)
    if m <= 0.0:
        return 0.0
    elif m <= 5.0:
        return round((m / 5.0) * 40.0, 4)
    elif m <= 10.0:
        return round(40.0 + ((m - 5.0) / 5.0) * 20.0, 4)
    elif m <= 15.0:
        return round(60.0 + ((m - 10.0) / 5.0) * 20.0, 4)
    elif m <= 20.0:
        return round(80.0 + ((m - 15.0) / 5.0) * 20.0, 4)
    else:
        return 100.0


def _normalize_de(de: Optional[float]) -> Optional[float]:
    """
    Piecewise linear normalization for Debt to Equity ratio.
    Normalizes input to ratio r (e.g. 0.1152 for 11.52%).
    - r <= 0.5 -> 100.0
    - 0.5 < r <= 1.5 -> 100.0 to 60.0
    - 1.5 < r <= 3.0 -> 60.0 to 10.0
    - r > 3.0 -> 10.0
    """
    if _is_invalid(de):
        return None
    r = float(de)
    if r > 1.0:
        r = r / 100.0
    if r <= 0.5:
        return 100.0
    elif r <= 1.5:
        return round(100.0 - ((r - 0.5) / 1.0) * 40.0, 4)
    elif r <= 3.0:
        return round(60.0 - ((r - 1.5) / 1.5) * 50.0, 4)
    else:
        return 10.0


def _normalize_growth(g: Optional[float]) -> Optional[float]:
    """
    Piecewise linear normalization for Growth rates (Revenue YoY / Profit YoY).
    Input g is a percentage (e.g. 12.35 for 12.35%).
    - g <= -20.0 -> 0.0
    - -20.0 < g <= 0.0 -> 20.0 to 50.0
    - 0.0 < g <= 15.0 -> 50.0 to 80.0
    - 15.0 < g <= 30.0 -> 80.0 to 100.0
    - g > 30.0 -> 100.0
    """
    if _is_invalid(g):
        return None
    g_val = float(g)
    if g_val <= -20.0:
        return 0.0
    elif g_val <= 0.0:
        return round(20.0 + ((g_val - (-20.0)) / 20.0) * 30.0, 4)
    elif g_val <= 15.0:
        return round(50.0 + (g_val / 15.0) * 30.0, 4)
    elif g_val <= 30.0:
        return round(80.0 + ((g_val - 15.0) / 15.0) * 20.0, 4)
    else:
        return 100.0


def _calculate_valuation_score(
    pe: Optional[float], classification: Optional[str]
) -> Optional[float]:
    """
    Continuous valuation scoring function based on P/E ratio and classification.
    - None / Insufficient Data / Missing P/E -> None
    - Unprofitable / pe <= 0 -> 10.0
    - 0 < pe < 5.0 -> 90.0 (Capped high score)
    - 5.0 <= pe < 15.0 -> 100.0 to 90.0
    - 15.0 <= pe <= 25.0 -> 90.0 to 60.0
    - pe > 25.0 -> 60.0 down to min 20.0 at pe >= 50.0
    """
    if classification == "Insufficient Data" or pe is None or _is_invalid(pe):
        return None
    if classification == "Unprofitable" or float(pe) <= 0.0:
        return 10.0

    p = float(pe)
    if p < 5.0:
        return 90.0
    elif p < 15.0:
        return round(100.0 - ((p - 5.0) / 10.0) * 10.0, 4)
    elif p <= 25.0:
        return round(90.0 - ((p - 15.0) / 10.0) * 30.0, 4)
    else:
        return round(max(20.0, 60.0 - ((p - 25.0) / 25.0) * 40.0), 4)


def analyze_financial_health(symbol: str, evaluation_date: Optional[str] = None, annual_records: Optional[list] = None) -> Dict[str, Any]:
    """
    Calculates the composite Financial Health Score (0 - 100) for a stock symbol
    by aggregating outputs from individual financial analyzers.

    Parameters:
    -----------
    symbol : str
        Stock ticker symbol (e.g., "TCS", "INFY").
    evaluation_date : Optional[str]
        Evaluation date cut-off.
    annual_records : Optional[list]
        Optional list of standardized annual financial records for the stock.

    Returns:
    --------
    dict
        Dictionary conforming to the approved V1 output contract:
        - symbol: str
        - status: "VALID" | "PARTIAL" | "INSUFFICIENT"
        - overall_score: float | None
        - profitability_score: float | None
        - growth_score: float | None
        - valuation_score: float | None
        - component_statuses: dict
        - data_completeness: float
    """
    # 1. Symbol Sanitization & Handling
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        norm_symbol = str(symbol).strip().upper() if symbol else ""
        return {
            "symbol": norm_symbol,
            "status": "INSUFFICIENT",
            "overall_score": None,
            "profitability_score": None,
            "growth_score": None,
            "valuation_score": None,
            "component_statuses": {
                "roe": "INSUFFICIENT",
                "roce": "INSUFFICIENT",
                "debt_equity": "INSUFFICIENT",
                "profit_margin": "INSUFFICIENT",
                "growth": "INSUFFICIENT",
                "volatility": "INSUFFICIENT",
                "valuation": "INSUFFICIENT",
            },
            "data_completeness": 0.0,
            "annual": None,
            "red_flags": None,
        }

    norm_symbol = symbol.strip().upper()

    # 2. Invoke Underlying Logic Analyzers (Read-Only)
    try:
        from backend.logic.roe_analyzer import analyze_roe
        from backend.logic.roce_analyzer import analyze_roce
        from backend.logic.debt_equity_analyzer import analyze_debt_equity
        from backend.logic.profit_margin_analyzer import analyze_profit_margin
        from backend.logic.growth_analyzer import analyze_growth
        from backend.logic.volatility_analyzer import analyze_volatility
        from backend.logic.valuation_analyzer import analyze_valuation

        roe_res = analyze_roe(norm_symbol)

        roce_res = analyze_roce(norm_symbol)
        de_res = analyze_debt_equity(norm_symbol)
        margin_res = analyze_profit_margin(norm_symbol)
        growth_res = analyze_growth(norm_symbol)
        volatility_res = analyze_volatility(norm_symbol, evaluation_date=evaluation_date)
        valuation_res = analyze_valuation(norm_symbol, evaluation_date=evaluation_date)
    except Exception:
        return {
            "symbol": norm_symbol,
            "status": "INSUFFICIENT",
            "overall_score": None,
            "profitability_score": None,
            "growth_score": None,
            "valuation_score": None,
            "component_statuses": {
                "roe": "INSUFFICIENT",
                "roce": "INSUFFICIENT",
                "debt_equity": "INSUFFICIENT",
                "profit_margin": "INSUFFICIENT",
                "growth": "INSUFFICIENT",
                "volatility": "INSUFFICIENT",
                "valuation": "INSUFFICIENT",
            },
            "data_completeness": 0.0,
            "annual": None,
            "red_flags": None,
        }

    # 3. Calculate Profitability Sub-Score
    s_roe = _normalize_roe(roe_res.get("latest_roe"))
    s_roce = _normalize_roce(roce_res.get("latest_roce"))
    s_margin = _normalize_margin(margin_res.get("latest_net_margin"))
    s_de = _normalize_de(de_res.get("latest_debt_equity"))

    prof_components = []
    if s_roe is not None:
        prof_components.append((s_roe, 0.30))
    if s_roce is not None:
        prof_components.append((s_roce, 0.30))
    if s_margin is not None:
        prof_components.append((s_margin, 0.25))
    if s_de is not None:
        prof_components.append((s_de, 0.15))

    if not prof_components:
        profitability_score = None
    else:
        tot_prof_weight = sum(w for _, w in prof_components)
        profitability_score = round(
            sum(val * (w / tot_prof_weight) for val, w in prof_components), 4
        )

    # 4. Calculate Growth Sub-Score
    s_rev_yoy = _normalize_growth(growth_res.get("revenue_yoy_growth"))
    s_profit_yoy = _normalize_growth(growth_res.get("net_profit_yoy_growth"))

    growth_components = []
    if s_rev_yoy is not None:
        growth_components.append((s_rev_yoy, 0.50))
    if s_profit_yoy is not None:
        growth_components.append((s_profit_yoy, 0.50))

    if not growth_components:
        growth_score = None
    else:
        tot_growth_weight = sum(w for _, w in growth_components)
        growth_score = round(
            sum(val * (w / tot_growth_weight) for val, w in growth_components), 4
        )

    # 5. Calculate Valuation Sub-Score
    valuation_score = _calculate_valuation_score(
        valuation_res.get("pe_ratio"),
        valuation_res.get("valuation_classification"),
    )

    # 6. Composite Score & Dynamic Re-Weighting (40% Profitability / 35% Growth / 25% Valuation)
    subscores = []
    if profitability_score is not None:
        subscores.append(("profitability", profitability_score, 0.40))
    if growth_score is not None:
        subscores.append(("growth", growth_score, 0.35))
    if valuation_score is not None:
        subscores.append(("valuation", valuation_score, 0.25))

    if len(subscores) < 2:
        overall_score = None
    else:
        tot_weight = sum(w for _, _, w in subscores)
        overall_score = round(
            sum(val * (w / tot_weight) for _, val, w in subscores), 4
        )

    # 7. Aggregate Status Determination (Rule C)
    analyzer_results = [
        roe_res,
        roce_res,
        de_res,
        margin_res,
        growth_res,
        volatility_res,
        valuation_res,
    ]

    all_analyzers_valid = all(
        r.get("status") == "VALID" for r in analyzer_results
    )
    valid_subscores_count = len(subscores)

    if valid_subscores_count < 2:
        status = "INSUFFICIENT"
    elif valid_subscores_count == 3 and all_analyzers_valid:
        status = "VALID"
    else:
        status = "PARTIAL"

    # 8. Data Completeness Calculation
    valid_components_count = sum(
        1 for r in analyzer_results if r.get("status") == "VALID"
    )
    data_completeness = round(valid_components_count / 7.0, 4)

    # 9. Return Contract Dictionary
    result = {
        "symbol": norm_symbol,
        "status": status,
        "overall_score": overall_score,
        "profitability_score": profitability_score,
        "growth_score": growth_score,
        "valuation_score": valuation_score,
        "component_statuses": {
            "roe": roe_res.get("status", "INSUFFICIENT"),
            "roce": roce_res.get("status", "INSUFFICIENT"),
            "debt_equity": de_res.get("status", "INSUFFICIENT"),
            "profit_margin": margin_res.get("status", "INSUFFICIENT"),
            "growth": growth_res.get("status", "INSUFFICIENT"),
            "volatility": volatility_res.get("status", "INSUFFICIENT"),
            "valuation": valuation_res.get("status", "INSUFFICIENT"),
        },
        "data_completeness": data_completeness,
    }

    # 10. Optional Annual and Red Flag Integration
    if annual_records is not None and isinstance(annual_records, list) and len(annual_records) > 0:
        try:
            from backend.logic.annual_financial_analyzer import analyze_annual_financials
            from backend.logic.red_flag_analyzer import detect_red_flags

            annual_analysis = analyze_annual_financials(annual_records)
            red_flag_results = detect_red_flags(annual_analysis)

            result["annual"] = annual_analysis
            result["red_flags"] = red_flag_results
        except Exception:
            result["annual"] = None
            result["red_flags"] = None
    else:
        result["annual"] = None
        result["red_flags"] = None

    return result
