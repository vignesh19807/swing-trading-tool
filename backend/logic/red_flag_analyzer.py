"""
Red Flag Analyzer v1
====================

Pure logic component for detecting financial red flags based on annual financial trends.

Purpose:
    Identifies problematic financial deterioration (e.g., declining revenue, shrinking profit margins)
    using the outputs of the Annual Financial Analyzer.

Rules:
    - Only flags definitive deterioration (e.g., "Declining" trends).
    - Missing data yields NO red flag (no false positives).
    - Returns structured explanation for every flag.
    - No external API or database access.

Architecture:
    Annual Financial Analyzer -> Red Flag Analyzer
"""

from typing import Dict, Any, List


def detect_red_flags(annual_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detects financial red flags from the structured output of analyze_annual_financials.

    Parameters:
    -----------
    annual_analysis : dict
        The output dictionary from analyze_annual_financials.

    Returns:
    --------
    dict
        Structured red flag results:
        {
            "has_red_flags": bool,
            "red_flags": [
                {
                    "type": str,
                    "severity": str,
                    "metric": str,
                    "reason": str
                }
            ]
        }
    """
    flags: List[Dict[str, str]] = []

    # If insufficient data, we cannot reliably determine red flags.
    if not annual_analysis or annual_analysis.get("status") == "INSUFFICIENT":
        return {
            "has_red_flags": False,
            "red_flags": []
        }

    # A. Revenue deterioration
    if annual_analysis.get("revenue_trend") == "Declining":
        flags.append({
            "type": "revenue_decline",
            "severity": "warning",
            "metric": "revenue",
            "reason": "Revenue shows a declining trend across the available consecutive annual periods."
        })

    # B. Net Profit deterioration
    if annual_analysis.get("net_profit_trend") == "Declining":
        flags.append({
            "type": "net_profit_decline",
            "severity": "warning",
            "metric": "net_profit",
            "reason": "Net profit shows a declining trend across the available consecutive annual periods."
        })

    # C. ROE weakness/deterioration
    if annual_analysis.get("roe_trend") == "Declining":
        flags.append({
            "type": "roe_decline",
            "severity": "warning",
            "metric": "roe",
            "reason": "Return on Equity (ROE) shows a materially declining trend across annual periods."
        })

    # D. ROCE weakness/deterioration
    if annual_analysis.get("roce_trend") == "Declining":
        flags.append({
            "type": "roce_decline",
            "severity": "warning",
            "metric": "roce",
            "reason": "Return on Capital Employed (ROCE) shows a materially declining trend across annual periods."
        })

    # E. Severe CAGR degradation (optional severe flags)
    # E.g., if Revenue CAGR is negative
    rev_cagr = annual_analysis.get("revenue_cagr")
    if rev_cagr is not None and rev_cagr < 0.0:
        # Check if we already added a revenue decline flag to avoid spam, or just add a severe variant.
        # We will keep it simple and deterministic.
        if not any(f["type"] == "revenue_decline" for f in flags):
             flags.append({
                "type": "negative_revenue_cagr",
                "severity": "high",
                "metric": "revenue",
                "reason": "Overall Revenue Compound Annual Growth Rate (CAGR) is negative."
            })

    np_cagr = annual_analysis.get("net_profit_cagr")
    if np_cagr is not None and np_cagr < 0.0:
        if not any(f["type"] == "net_profit_decline" for f in flags):
             flags.append({
                "type": "negative_profit_cagr",
                "severity": "high",
                "metric": "net_profit",
                "reason": "Overall Net Profit Compound Annual Growth Rate (CAGR) is negative."
            })

    return {
        "has_red_flags": len(flags) > 0,
        "red_flags": flags
    }
