"""
Opportunity Explanation Logic
=============================

Orchestrates the final Wednesday explanation contract by combining Technical,
Financial, and Sector explanations. Computes the exact Decision Engine weights.
"""

from typing import Dict, Any, Optional
import pandas as pd

from backend.logic.explanation.technical_explanation import explain_technical_factors
from backend.logic.explanation.financial_explanation import explain_financial_factors
from backend.logic.explanation.sector_explanation import explain_sector_context


def explain_momentum(decision_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Since Momentum is a derived subscore within the Decision Engine,
    we explicitly explain its score directly.
    """
    momentum_score = decision_payload.get("momentum_score")
    if momentum_score is None:
        return {
            "category": "Momentum",
            "metric": "Momentum Composite",
            "reason": "Insufficient technical data (RSI or MACD) to derive Momentum."
        }

    try:
        val = float(momentum_score)

        # Max momentum is 100.
        if val >= 80.0:
            sentiment = "positive"
            interpretation = "Strong combined momentum (derived from RSI and MACD)."
        elif val <= 40.0:
            sentiment = "negative"
            interpretation = "Weak combined momentum."
        else:
            sentiment = "neutral"
            interpretation = "Neutral or mixed momentum."

        return {
            "category": "Momentum",
            "metric": "Momentum Composite",
            "value": f"Score: {val:.2f}/100",
            "interpretation": interpretation,
            "sentiment": sentiment
        }
    except (ValueError, TypeError):
        return {
            "category": "Momentum",
            "metric": "Momentum Composite",
            "reason": "Invalid momentum score format."
        }


def explain_opportunity(
    decision_payload: Dict[str, Any],
    indicators_df: Optional[pd.DataFrame],
    financial_result: Optional[Dict[str, Any]],
    evaluation_date: Optional[str]
) -> Dict[str, Any]:
    """
    Builds the finalized Week 9 Explanation Contract for the given Opportunity Score.
    """
    symbol = decision_payload.get("symbol", "")
    status = decision_payload.get("status", "INSUFFICIENT")
    opp_score = decision_payload.get("opportunity_score")
    rec = decision_payload.get("recommendation", "INSUFFICIENT_DATA")

    # If the decision was aborted, return a minimal explicit explanation.
    if status == "INSUFFICIENT" or opp_score is None:
        return {
            "symbol": symbol,
            "evaluation_date": evaluation_date,
            "opportunity_score": None,
            "recommendation": rec,
            "status": status,
            "score_breakdown": {
                "technical_score": decision_payload.get("technical_score"),
                "technical_weight": 0.40,
                "technical_weighted_contribution": None,
                "financial_score": decision_payload.get("financial_score"),
                "financial_weight": 0.35,
                "financial_weighted_contribution": None,
                "momentum_score": None,
                "momentum_weight": 0.25,
                "momentum_weighted_contribution": None,
            },
            "explanation": {
                "summary": f"Opportunity score calculation aborted due to missing mandatory data for {symbol}.",
                "positive_factors": [],
                "negative_factors": [],
                "neutral_factors": [],
                "missing_factors": [
                    {
                        "category": "Core",
                        "metric": "Mandatory Data",
                        "reason": "Technical or Financial base score was entirely missing or invalid."
                    }
                ],
                "sector_context": explain_sector_context(symbol, decision_payload.get("sector_intelligence"))
            }
        }

    # Extract Component Scores
    tech_score = decision_payload.get("technical_score")
    fin_score = decision_payload.get("financial_score")
    mom_score = decision_payload.get("momentum_score")

    # Determine exact weights (dynamic re-weighting logic from Decision Engine)
    if mom_score is None:
        tech_weight = 0.40 / 0.75
        fin_weight = 0.35 / 0.75
        mom_weight = 0.25

        tech_contrib = (tech_score * tech_weight) if tech_score is not None else None
        fin_contrib = (fin_score * fin_weight) if fin_score is not None else None
        mom_contrib = None
    else:
        tech_weight = 0.40
        fin_weight = 0.35
        mom_weight = 0.25

        tech_contrib = (tech_score * tech_weight) if tech_score is not None else None
        fin_contrib = (fin_score * fin_weight) if fin_score is not None else None
        mom_contrib = (mom_score * mom_weight) if mom_score is not None else None

    # Build Breakdown
    score_breakdown = {
        "technical_score": tech_score,
        "technical_weight": round(tech_weight, 4),
        "technical_weighted_contribution": round(tech_contrib, 4) if tech_contrib is not None else None,
        "financial_score": fin_score,
        "financial_weight": round(fin_weight, 4),
        "financial_weighted_contribution": round(fin_contrib, 4) if fin_contrib is not None else None,
        "momentum_score": mom_score,
        "momentum_weight": round(mom_weight, 4),
        "momentum_weighted_contribution": round(mom_contrib, 4) if mom_contrib is not None else None,
    }

    # Fetch underlying factor explanations
    tech_factors = explain_technical_factors(indicators_df) if indicators_df is not None else []
    fin_factors = explain_financial_factors(financial_result) if financial_result else []
    mom_factor = explain_momentum(decision_payload)

    # Classify factors
    positives = []
    negatives = []
    neutrals = []
    missing = []

    all_factors = tech_factors + fin_factors
    if mom_factor:
        all_factors.append(mom_factor)

    for f in all_factors:
        sentiment = f.pop("sentiment", None)
        if sentiment == "missing" or "reason" in f:
            missing.append({
                "category": f.get("category"),
                "metric": f.get("metric"),
                "reason": f.get("reason") or f.get("interpretation", "Unavailable data.")
            })
        elif sentiment == "positive":
            positives.append(f)
        elif sentiment == "negative":
            negatives.append(f)
        elif sentiment == "neutral":
            neutrals.append(f)

    # Synthesize Summary String
    if rec == "BUY":
        summary = f"{symbol} generates a BUY recommendation driven by strong contributing factors."
    elif rec == "WATCH":
        summary = f"{symbol} is placed on WATCH due to a balanced mix of positive and cautionary factors."
    elif rec == "HOLD":
        summary = f"{symbol} generates a HOLD recommendation, showing moderate or mixed signals."
    else:
        summary = f"{symbol} generates an AVOID recommendation due to weak technical or financial metrics."

    if mom_score is None:
        summary += " Note: Momentum metrics were missing, causing Technical and Financial factors to be dynamically overweighted."

    sector_context = explain_sector_context(symbol, decision_payload.get("sector_intelligence"))

    return {
        "symbol": symbol,
        "evaluation_date": evaluation_date,
        "opportunity_score": opp_score,
        "recommendation": rec,
        "status": status,
        "score_breakdown": score_breakdown,
        "explanation": {
            "summary": summary,
            "positive_factors": positives,
            "negative_factors": negatives,
            "neutral_factors": neutrals,
            "missing_factors": missing,
            "sector_context": sector_context
        }
    }
