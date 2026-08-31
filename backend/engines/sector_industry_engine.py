"""
Week 5 - Sector & Industry Engine
=================================
Orchestrator for the Sector/Industry Intelligence module.

This engine unifies the sector and industry logic evaluations into a single
consolidated report containing structured rankings, relative strength,
and preliminary scoring.

Architectural Constraints:
- Consumes logic components as read-only dependencies.
- No direct SQLite access.
- No yfinance or external API requests.
- Bypasses missing benchmark data safely.
"""

from typing import Dict, Any, Optional
from backend.logic.sector_engine import rank_sectors, rank_industries
from backend.data_pipeline.classification_service import get_sectors, get_industries

def run_sector_industry_engine(
    evaluation_date: Optional[str] = None,
    ranking_period: str = "63D"
) -> Dict[str, Any]:
    """
    Orchestrates the evaluation and ranking of all sectors and industries
    across the entire market universe.

    Parameters:
    -----------
    evaluation_date : str, optional
        Date to evaluate the performance up to.
    ranking_period : str
        The primary period used for ranking groups (default: "63D").

    Returns:
    --------
    dict
        Consolidated report containing ranked sectors and industries
        with their underlying scores and relative strength components.
    """
    # 1. Fetch available sectors and industries from the Data Engineer classification layer
    try:
        sectors = get_sectors()
    except Exception:
        sectors = []

    try:
        industries_df = get_industries()
        if not industries_df.empty and "industry" in industries_df.columns:
            # Extract unique industries securely
            industries = industries_df["industry"].unique().tolist()
        else:
            industries = []
    except Exception:
        industries = []

    # 2. Evaluate and Rank Sectors via Logic Layer
    if sectors:
        sector_results = rank_sectors(
            sectors=sectors,
            evaluation_date=evaluation_date,
            ranking_period=ranking_period
        )
    else:
        sector_results = {
            "evaluation_date": evaluation_date,
            "ranking_period": ranking_period,
            "ranked_sectors": []
        }

    # 3. Evaluate and Rank Industries via Logic Layer
    if industries:
        industry_results = rank_industries(
            industries=industries,
            evaluation_date=evaluation_date,
            ranking_period=ranking_period
        )
    else:
        industry_results = {
            "evaluation_date": evaluation_date,
            "ranking_period": ranking_period,
            "ranked_industries": []
        }

    # 4. Construct Top-Level Unified Output Contract
    status = "VALID" if sectors and industries else "INSUFFICIENT_DATA"
    if sectors and not industries:
        status = "PARTIAL"
    elif industries and not sectors:
        status = "PARTIAL"

    return {
        "status": status,
        "evaluation_date": evaluation_date,
        "ranking_period": ranking_period,
        "sectors_analyzed": len(sectors),
        "industries_analyzed": len(industries),
        "sector_rankings": sector_results.get("ranked_sectors", []),
        "industry_rankings": industry_results.get("ranked_industries", [])
    }
