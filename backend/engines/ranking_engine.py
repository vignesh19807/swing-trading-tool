"""
Ranking Engine V1 (Engine 8)
=============================

Generates the final Top 10 Ranked Stocks by consuming the unmodified Opportunity Score
from the Decision Engine and applying Sector Intelligence as a macroeconomic overlay.

Ranking Formula:
----------------
final_ranking_score = (opportunity_score * 0.70) + (sector_score * 0.30)

Missing Data Handling:
----------------------
If Sector Intelligence is unavailable, sector_score defaults to the opportunity_score
to preserve the intrinsic stock rating.

Author: Logic Engineer
"""

from typing import List, Dict, Any, Optional

def generate_top_10_ranking(
    decision_engine_results: List[Dict[str, Any]],
    evaluation_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Consumes a list of Decision Engine outputs and produces a Top 10 ranking.

    Parameters
    ----------
    decision_engine_results : List[Dict[str, Any]]
        List of dictionaries output by calculate_opportunity_score().
    evaluation_date : Optional[str]
        The uniform evaluation date applied to the batch.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing:
        {
            "evaluation_date": str,
            "top_10": List[Dict[str, Any]],
            "unranked": List[Dict[str, Any]]
        }
    """
    valid_stocks = []
    unranked_stocks = []

    if not isinstance(decision_engine_results, list):
        return {
            "evaluation_date": evaluation_date,
            "top_10": [],
            "unranked": []
        }

    # 1. Filter and Calculate Scores
    for record in decision_engine_results:
        symbol = record.get("symbol", "UNKNOWN")
        status = record.get("status", "INSUFFICIENT")
        opp_score = record.get("opportunity_score")

        # Determine if fundamentally valid
        if status not in ("VALID", "PARTIAL") or opp_score is None:
            unranked_stocks.append({
                "symbol": symbol,
                "status": "INSUFFICIENT",
                "reason": "MISSING_CORE_OPPORTUNITY_SCORE"
            })
            continue

        opp_score = float(opp_score)
        sector_score = opp_score # Option A: Default fallback
        sector_intel = record.get("sector_intelligence")

        classification = None
        if isinstance(sector_intel, dict):
            classification = sector_intel.get("classification")
            sp = sector_intel.get("sector_performance")
            if isinstance(sp, dict):
                ps = sp.get("preliminary_score")
                if isinstance(ps, dict):
                    ss = ps.get("score")
                    if ss is not None:
                        try:
                            sector_score = float(ss)
                        except (TypeError, ValueError):
                            sector_score = opp_score

        final_ranking_score = round((opp_score * 0.70) + (sector_score * 0.30), 4)

        valid_stocks.append({
            "symbol": symbol,
            "final_ranking_score": final_ranking_score,
            "opportunity_score": opp_score,
            "sector_score": sector_score,
            "recommendation": record.get("recommendation", "UNKNOWN"),
            "sector": classification.get("sector") if isinstance(classification, dict) else None,
            "industry": classification.get("industry") if isinstance(classification, dict) else None,
            "status": status
        })

    # 2. Sort valid stocks (Deterministic tie-breaking)
    # Sort primarily by final_ranking_score (DESC)
    # Secondary by opportunity_score (DESC)
    # Tertiary by symbol (ASC)
    valid_stocks.sort(key=lambda x: (-x["final_ranking_score"], -x["opportunity_score"], x["symbol"]))

    # 3. Extract Top 10
    top_10 = valid_stocks[:10]
    outside_top_10 = valid_stocks[10:]

    # Add ranks to top 10
    for i, stock in enumerate(top_10):
        stock["rank"] = i + 1

    # Shift outside top 10 into unranked
    for stock in outside_top_10:
        unranked_stocks.append({
            "symbol": stock["symbol"],
            "status": stock["status"],
            "reason": "OUTSIDE_TOP_10"
        })

    return {
        "evaluation_date": evaluation_date,
        "top_10": top_10,
        "unranked": unranked_stocks
    }
