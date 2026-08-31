"""
Week 6 - Stock Context Analyzer
===============================
Connects an individual stock symbol to its sector and industry context
using the Data Engineer's classification_service.

Architectural Constraints:
- Read-only consumption of Data Engineer services.
- No direct SQLite access.
- No yfinance or external APIs.
"""

from typing import Dict, Any, List, Optional
from backend.data_pipeline.classification_service import (
    get_company_classification,
    get_sector_stocks,
    get_industry_stocks
)
from backend.logic.sector_engine import evaluate_sector, calculate_constituent_returns

def get_stock_context(symbol: str) -> Dict[str, Any]:
    """
    Retrieves the sector and industry context for a given stock symbol.

    Parameters:
    -----------
    symbol : str
        The stock ticker symbol.

    Returns:
    --------
    dict
        A structured dictionary containing the stock's classification context.
        If the symbol is not found, returns a safe fallback dictionary with
        status = "NOT_FOUND".
    """
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        return {
            "symbol": str(symbol).strip().upper() if (symbol and str(symbol).strip()) else "UNKNOWN",
            "status": "NOT_FOUND",
            "company_name": None,
            "sector": None,
            "industry": None
        }

    norm_symbol = symbol.strip().upper()
    classification = get_company_classification(norm_symbol)

    if classification is None:
        return {
            "symbol": norm_symbol,
            "status": "NOT_FOUND",
            "company_name": None,
            "sector": None,
            "industry": None
        }

    return {
        "symbol": classification["symbol"],
        "status": "VALID",
        "company_name": classification["company_name"],
        "sector": classification["sector"],
        "industry": classification["industry"]
    }

def get_sector_contexts(sector: str) -> List[Dict[str, Any]]:
    """
    Retrieves the stock contexts for all constituents belonging to a sector.

    Parameters:
    -----------
    sector : str
        The sector name.

    Returns:
    --------
    list[dict]
        A list of structured dictionaries containing classification contexts.
        Returns [] if the sector is unknown, empty, None, or whitespace.
    """
    if not sector or not isinstance(sector, str) or not sector.strip():
        return []

    norm_sector = sector.strip()
    symbols = get_sector_stocks(norm_sector)

    return [get_stock_context(sym) for sym in symbols]

def get_industry_contexts(industry: str) -> List[Dict[str, Any]]:
    """
    Retrieves the stock contexts for all constituents belonging to an industry.

    Parameters:
    -----------
    industry : str
        The industry name.

    Returns:
    --------
    list[dict]
        A list of structured dictionaries containing classification contexts.
        Returns [] if the industry is unknown, empty, None, or whitespace.
    """
    if not industry or not isinstance(industry, str) or not industry.strip():
        return []

    norm_industry = industry.strip()
    symbols = get_industry_stocks(norm_industry)

    return [get_stock_context(sym) for sym in symbols]

def get_stock_sector_performance_context(
    symbol: str,
    evaluation_date: Optional[str] = None,
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Combines the individual stock's performance with its overarching Sector context.

    Parameters:
    -----------
    symbol : str
        The stock ticker symbol.
    evaluation_date : str, optional
        Date to evaluate the performance up to.
    lookback_periods : list of int, optional
        Custom lookback periods for momentum calculation.

    Returns:
    --------
    dict
        A structured dictionary containing stock context, stock performance,
        and the entire sector's aggregated performance metrics.
    """
    stock_context = get_stock_context(symbol)

    # Baseline missing response if stock is completely unknown
    if stock_context.get("status") == "NOT_FOUND":
        return {
            "symbol": stock_context.get("symbol", "UNKNOWN"),
            "evaluation_date": evaluation_date,
            "status": "NOT_FOUND",
            "classification": {
                "company_name": None,
                "sector": None,
                "industry": None
            },
            "stock_performance": None,
            "sector_performance": None
        }

    sector = stock_context["sector"]

    # 1. Fetch individual stock returns using Week 5 logic mathematically
    stock_perf = calculate_constituent_returns(
        symbol=stock_context["symbol"],
        evaluation_date=evaluation_date,
        lookback_periods=lookback_periods
    )

    # 2. Fetch aggregated sector returns using Week 5 engine recursively
    sector_perf_data = evaluate_sector(
        sector=sector,
        evaluation_date=evaluation_date,
        lookback_periods=lookback_periods
    )

    # 3. Construct unified JSON payload
    return {
        "symbol": stock_context["symbol"],
        "evaluation_date": evaluation_date,
        "status": stock_context["status"],
        "classification": {
            "company_name": stock_context["company_name"],
            "sector": stock_context["sector"],
            "industry": stock_context["industry"]
        },
        "stock_performance": stock_perf,
        "sector_performance": {
            "data_quality": sector_perf_data["data_quality"]["status"],
            "performance": sector_perf_data["performance"],
            "preliminary_score": sector_perf_data["preliminary_score"],
            "relative_strength": sector_perf_data["relative_strength"]
        }
    }
