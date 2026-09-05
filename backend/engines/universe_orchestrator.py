"""
Universe Orchestrator
=====================
Coordinates the End-to-End flow of the Swing Trading Tool universe.
Reads from Data Engineer classification layer, loops over all stocks,
fetches contextual data, executes the Decision Engine, and funnels
the results to the Ranking Engine for the Top 10 outcome.
"""

from typing import Dict, Any, Optional
import traceback
import logging

from backend.data_pipeline.classification_service import get_all_classifications
from backend.logic.stock_context_analyzer import get_stock_sector_performance_context
from backend.engines.decision_engine import calculate_opportunity_score
from backend.engines.ranking_engine import generate_top_10_ranking
from backend.logic.explanation.opportunity_explanation import explain_opportunity

logger = logging.getLogger(__name__)

def rank_universe(evaluation_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Ranks the entire stock universe for a given evaluation date.

    Parameters
    ----------
    evaluation_date : str, optional
        Target evaluation date. Defaults to None (latest).

    Returns
    -------
    Dict[str, Any]
        The final Top 10 structure matching Ranking Engine contract.
    """

    # 1. Fetch Universe from the Data Engineer classification boundary
    try:
        classifications_df = get_all_classifications()
        if classifications_df is None or classifications_df.empty:
            symbols = []
        else:
            symbols = classifications_df["symbol"].dropna().unique().tolist()
    except Exception as e:
        logger.error(f"Failed to fetch stock universe: {str(e)}")
        symbols = []

    decision_results = []
    explanation_contexts = {}

    # 2. Collect Decision Engine payload for each stock
    for symbol in symbols:
        try:
            # Safely fetch sector intelligence
            sector_intel = None
            try:
                sector_intel = get_stock_sector_performance_context(
                    symbol,
                    evaluation_date=evaluation_date
                )
            except Exception as e:
                logger.warning(f"Failed to fetch sector intelligence for {symbol}: {str(e)}")

            # Safely execute Decision Engine
            res = calculate_opportunity_score(
                symbol,
                evaluation_date=evaluation_date,
                sector_intelligence=sector_intel
            )

            # Pop the internal transient explanation context to keep the public payload clean
            ctx = res.pop("_explanation_context", {})
            explanation_contexts[symbol] = {
                "context": ctx,
                "sector_intelligence": sector_intel,
                "original_payload": res.copy()
            }

            decision_results.append(res)

        except Exception as e:
            # Failure isolation: one stock crash does not abort the universe sweep
            logger.error(f"Critical failure executing Decision Engine for {symbol}: {str(e)}")
            # Push an artificial INSUFFICIENT struct so ranking engine natively filters it out
            decision_results.append({
                "symbol": symbol,
                "status": "INSUFFICIENT",
                "opportunity_score": None,
                "recommendation": "INSUFFICIENT_DATA",
                "error": str(e)
            })

    # 3. Generate Final Top 10 Ranking
    ranking = generate_top_10_ranking(
        decision_results,
        evaluation_date=evaluation_date
    )

    # 4. Generate and attach Explanations and Trade Quality Context to Top 10 Only
    for stock in ranking.get("top_10", []):
        sym = stock.get("symbol")
        data = explanation_contexts.get(sym, {})
        ctx = data.get("context", {})

        # We pass original_payload because explain_opportunity expects the exact decision payload fields
        # Note: sector_intelligence is typically embedded in the decision payload, but we ensure it's there.
        explanation = explain_opportunity(
            decision_payload=data.get("original_payload", stock),
            indicators_df=ctx.get("indicators_df"),
            financial_result=ctx.get("financial_result"),
            evaluation_date=evaluation_date
        )

        stock["structured_explanation"] = explanation

        # Safely attach Trade Quality & Risk Context as additive information without altering ranking
        try:
            from backend.logic.signal_integration import run_signal_pipeline
            sig = run_signal_pipeline(sym, evaluation_date=evaluation_date)
            stock["trade_quality"] = sig.get("trade_quality")
            stock["is_eligible"] = sig.get("is_eligible", False)
        except Exception as e:
            logger.warning(f"Failed to attach trade quality for {sym}: {str(e)}")
            stock["trade_quality"] = {
                "is_eligible": False,
                "risk_status": "INCOMPLETE",
                "eligibility_reason": "SIGNAL_EVALUATION_ERROR",
                "risk_flags": ["SIGNAL_EVALUATION_ERROR"],
                "signal_reason": str(e),
                "missing_inputs": []
            }
            stock["is_eligible"] = False
    return ranking
