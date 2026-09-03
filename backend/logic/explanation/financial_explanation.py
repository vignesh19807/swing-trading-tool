"""
Financial Explanation Logic
===========================

Generates structured explanations for Financial Engine outputs.
Reads the exact output from `analyze_financial_health` and classifies
factors based strictly on existing logic. Raw metrics not exported
by the engine are marked as unavailable.
"""

from typing import Dict, Any, List


def _explain_subscore(
    category_name: str,
    score: Any,
    status: str,
    positive_threshold: float,
    negative_threshold: float,
    positive_interp: str,
    negative_interp: str,
    neutral_interp: str
) -> Dict[str, Any]:
    if status == "INSUFFICIENT" or score is None:
        return {
            "category": "Financial",
            "metric": category_name,
            "value": "Unavailable upstream",
            "interpretation": f"Insufficient data for {category_name} calculation.",
            "sentiment": "missing"
        }

    try:
        score_val = float(score)
        # Using the engine's 0-100 subscores to determine sentiment
        if score_val > positive_threshold:
            sentiment = "positive"
            interpretation = positive_interp
        elif score_val <= negative_threshold:
            sentiment = "negative"
            interpretation = negative_interp
        else:
            sentiment = "neutral"
            interpretation = neutral_interp

        return {
            "category": "Financial",
            "metric": category_name,
            "value": f"Score: {score_val:.2f}/100",
            "interpretation": interpretation,
            "sentiment": sentiment
        }
    except (ValueError, TypeError):
        return {
            "category": "Financial",
            "metric": category_name,
            "value": "Unavailable upstream",
            "interpretation": f"Invalid score data for {category_name}.",
            "sentiment": "missing"
        }


def explain_profitability(fin_result: Dict[str, Any]) -> Dict[str, Any]:
    score = fin_result.get("profitability_score")

    # We aggregate the component statuses to see if they are valid
    comp_statuses = fin_result.get("component_statuses", {})
    roe_status = comp_statuses.get("roe", "INSUFFICIENT")
    roce_status = comp_statuses.get("roce", "INSUFFICIENT")
    margin_status = comp_statuses.get("profit_margin", "INSUFFICIENT")

    if roe_status == "INSUFFICIENT" and roce_status == "INSUFFICIENT" and margin_status == "INSUFFICIENT":
        status = "INSUFFICIENT"
    else:
        status = "VALID"

    return _explain_subscore(
        category_name="Profitability",
        score=score,
        status=status,
        positive_threshold=80.0,
        negative_threshold=40.0,
        positive_interp="Strong profitability metrics (e.g., high ROE, ROCE, or Net Margin).",
        negative_interp="Weak profitability metrics.",
        neutral_interp="Average profitability metrics."
    )


def explain_growth(fin_result: Dict[str, Any]) -> Dict[str, Any]:
    score = fin_result.get("growth_score")
    comp_statuses = fin_result.get("component_statuses", {})
    status = comp_statuses.get("growth", "INSUFFICIENT")

    # In the engine, growth > 15% gives > 80 score. growth <= 0 gives <= 50.
    return _explain_subscore(
        category_name="Growth",
        score=score,
        status=status,
        positive_threshold=80.0,
        negative_threshold=50.0,
        positive_interp="Strong growth in revenue and/or net profit.",
        negative_interp="Negative or very low growth.",
        neutral_interp="Stable but moderate growth."
    )


def explain_valuation(fin_result: Dict[str, Any]) -> Dict[str, Any]:
    score = fin_result.get("valuation_score")
    comp_statuses = fin_result.get("component_statuses", {})
    status = comp_statuses.get("valuation", "INSUFFICIENT")

    # In the engine, undervalued (PE < 15) gives score > 90 (capped at 90 sometimes)
    # Actually undervalued is 90-100.
    # Unprofitable / pe <= 0 gives 10.0.
    # pe > 25 gives <= 60.0.
    return _explain_subscore(
        category_name="Valuation",
        score=score,
        status=status,
        positive_threshold=90.0,
        negative_threshold=60.0,
        positive_interp="Undervalued or fairly valued with a very attractive P/E ratio.",
        negative_interp="Overvalued or Unprofitable.",
        neutral_interp="Fairly valued."
    )


def explain_financial_factors(fin_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Given the output from analyze_financial_health, extract and interpret the latest factors.
    Since raw metrics are not exported, we base explanations on subscores and component statuses.
    """
    if not fin_result:
        return []

    factors = [
        explain_profitability(fin_result),
        explain_growth(fin_result),
        explain_valuation(fin_result)
    ]

    return factors
