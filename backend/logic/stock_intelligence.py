"""
Stock Intelligence Service (Week 11 - Structured Stock Intelligence)
=====================================================================

Assembles a unified, API-ready, deterministic stock-level intelligence payload
combining Data Pipeline snapshot context with Logic Engine outputs:
- Symbol & Evaluation Date
- Identity & Classification
- Data Quality & Status
- Technical Intelligence Summary
- Financial Health Summary
- Sector Performance Context
- Decision Engine / Opportunity Score Result
- Signal Engine Result
- Trade Quality & Risk Context
- Structured Opportunity Explanation

Author: Logic Engineer
"""

from typing import Any, Dict, Optional
import logging
import math

from backend.data_pipeline.stock_snapshot_service import get_stock_snapshot
from backend.engines.decision_engine import calculate_opportunity_score
from backend.logic.stock_context_analyzer import get_stock_sector_performance_context
from backend.logic.explanation.opportunity_explanation import explain_opportunity
from backend.logic.signal_integration import run_signal_pipeline

logger = logging.getLogger(__name__)


def _sanitize_primitives(obj: Any) -> Any:
    """Recursively convert float NaNs / Infs and non-primitive objects to clean JSON types."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _sanitize_primitives(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_primitives(v) for v in obj]
    return None


def get_stock_intelligence(
    symbol: str,
    evaluation_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns an API-ready, deterministic stock-level intelligence payload.

    Parameters
    ----------
    symbol : str
        NSE stock symbol (e.g. "TCS", "INFY").
    evaluation_date : str, optional
        Target point-in-time evaluation date (YYYY-MM-DD).

    Returns
    -------
    dict
        Structured stock intelligence dictionary.
    """
    symbol_clean = symbol.upper().strip() if isinstance(symbol, str) else ""

    if not symbol_clean:
        return {
            "symbol": "",
            "evaluation_date": evaluation_date,
            "status": "INVALID",
            "identity": None,
            "data_quality": {"status": "INVALID", "warnings": ["Invalid stock symbol"]},
            "technical_intelligence": None,
            "financial_intelligence": None,
            "sector_intelligence": None,
            "decision_result": {
                "symbol": "",
                "status": "INSUFFICIENT",
                "opportunity_score": None,
                "recommendation": "INSUFFICIENT_DATA"
            },
            "signal_result": None,
            "trade_quality": None,
            "structured_explanation": None
        }

    # 1. Fetch Data Engineer Unified Stock Snapshot
    snapshot = None
    try:
        snapshot = get_stock_snapshot(symbol_clean, evaluation_date=evaluation_date)
    except Exception as e:
        logger.warning(f"Failed to fetch stock snapshot for {symbol_clean}: {e}")

    identity = snapshot.get("identity") if isinstance(snapshot, dict) else None
    data_quality = snapshot.get("data_quality") if isinstance(snapshot, dict) else None
    overall_status = snapshot.get("status", "INCOMPLETE") if isinstance(snapshot, dict) else "INCOMPLETE"

    # 2. Fetch Sector Performance Intelligence Context
    sector_intel = None
    try:
        sector_intel = get_stock_sector_performance_context(symbol_clean, evaluation_date=evaluation_date)
    except Exception as e:
        logger.warning(f"Failed to fetch sector context for {symbol_clean}: {e}")

    # 3. Execute Decision Engine
    decision_res = None
    public_decision_res = None
    explanation_ctx = {}
    try:
        decision_res = calculate_opportunity_score(
            symbol_clean,
            evaluation_date=evaluation_date,
            sector_intelligence=sector_intel
        )
        if isinstance(decision_res, dict):
            explanation_ctx = decision_res.get("_explanation_context", {})
            if not isinstance(explanation_ctx, dict):
                explanation_ctx = {}
            public_decision_res = {k: v for k, v in decision_res.items() if k != "_explanation_context"}
        else:
            public_decision_res = decision_res
    except Exception as e:
        logger.error(f"Decision Engine calculation failed for {symbol_clean}: {e}")
        decision_res = {
            "symbol": symbol_clean,
            "status": "INSUFFICIENT",
            "opportunity_score": None,
            "recommendation": "INSUFFICIENT_DATA",
            "error": str(e)
        }
        public_decision_res = decision_res

    # Extract clean Technical & Financial summaries from context if available
    indicators_df = explanation_ctx.get("indicators_df") if isinstance(explanation_ctx, dict) else None
    financial_res = explanation_ctx.get("financial_result") if isinstance(explanation_ctx, dict) else None

    technical_intel = None
    if indicators_df is not None and not indicators_df.empty:
        try:
            latest_row = indicators_df.iloc[-1]
            technical_intel = {
                "technical_score": _sanitize_primitives(latest_row.get("technical_score")),
                "rsi_score": _sanitize_primitives(latest_row.get("rsi_score")),
                "macd_score": _sanitize_primitives(latest_row.get("macd_score")),
                "trend_score": _sanitize_primitives(latest_row.get("trend_score")),
                "volume_score": _sanitize_primitives(latest_row.get("volume_score")),
            }
        except Exception:
            technical_intel = None

    financial_intel = None
    if isinstance(financial_res, dict):
        financial_intel = {
            "status": financial_res.get("status"),
            "overall_score": _sanitize_primitives(financial_res.get("overall_score")),
            "profitability_score": _sanitize_primitives(financial_res.get("profitability_score")),
            "growth_score": _sanitize_primitives(financial_res.get("growth_score")),
            "valuation_score": _sanitize_primitives(financial_res.get("valuation_score")),
            "component_statuses": _sanitize_primitives(financial_res.get("component_statuses")),
            "data_completeness": _sanitize_primitives(financial_res.get("data_completeness"))
        }

    # 4. Generate Structured Explanation
    explanation = None
    try:
        explanation = explain_opportunity(
            decision_payload=decision_res,
            indicators_df=indicators_df,
            financial_result=financial_res,
            evaluation_date=evaluation_date
        )
    except Exception as e:
        logger.warning(f"Explanation Engine failed for {symbol_clean}: {e}")

    # 5. Execute Signal Engine & Trade Quality Pipeline
    signal_res = None
    trade_quality = None
    try:
        signal_res = run_signal_pipeline(symbol_clean, evaluation_date=evaluation_date)
        if isinstance(signal_res, dict):
            trade_quality = signal_res.get("trade_quality")
    except Exception as e:
        logger.warning(f"Signal Pipeline failed for {symbol_clean}: {e}")

    # Assemble API-Ready Stock Intelligence Payload
    payload = {
        "symbol": symbol_clean,
        "evaluation_date": evaluation_date,
        "status": public_decision_res.get("status", overall_status) if isinstance(public_decision_res, dict) else overall_status,
        "identity": _sanitize_primitives(identity),
        "data_quality": _sanitize_primitives(data_quality),
        "technical_intelligence": _sanitize_primitives(technical_intel),
        "financial_intelligence": _sanitize_primitives(financial_intel),
        "sector_intelligence": _sanitize_primitives(sector_intel),
        "decision_result": _sanitize_primitives(public_decision_res),
        "signal_result": _sanitize_primitives(signal_res),
        "trade_quality": _sanitize_primitives(trade_quality),
        "structured_explanation": _sanitize_primitives(explanation),
    }

    return payload
