"""
Week 5 - Sector & Industry Intelligence Logic Engine
"""
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from backend.data_pipeline.classification_service import (
    get_sector_stocks,
    get_industry_stocks,
    get_company_classification
)
from backend.data_pipeline.historical_data_service import get_historical_data

try:
    from backend.data_pipeline.historical_data_service import get_benchmark_historical_data
except ImportError:
    get_benchmark_historical_data = None

DEFAULT_LOOKBACK_PERIODS = [21, 63, 126, 252]

def _calculate_constituent_returns(
    symbol: str,
    evaluation_date: Optional[str],
    lookback_periods: List[int]
) -> Dict[str, Any]:
    """Calculates returns for a single constituent over the given lookbacks."""
    # We fetch a large enough window assuming ~252 trading days is max,
    # but to be safe and cover all historical data up to evaluation_date,
    # we don't specify start_date, which means fetch all.
    # For optimization in a real scenario we'd pass start_date = eval_date - max_days,
    # but without knowing calendar vs trading days, passing None is safer.
    hist = get_historical_data(
        symbol=symbol,
        start_date=None,
        end_date=evaluation_date,
        include_adjusted_close=True
    )

    returns = {f"{period}D": None for period in lookback_periods}
    valid = False

    if hist.get("status") in ["EMPTY", "INVALID"]:
        return returns

    df = hist.get("data", pd.DataFrame())
    if df.empty:
        return returns

    if "adjusted_close" in df.columns:
        price_col = "adjusted_close"
    elif "close" in df.columns:
        price_col = "close"
    else:
        return returns

    if df.empty:
        return returns

    latest_price = df.iloc[-1][price_col]
    if pd.isna(latest_price) or latest_price <= 0:
        return returns

    for period in lookback_periods:
        if len(df) > period:
            # We want the price from 'period' trading days ago
            # If length is N, latest is N-1. The observation 'period' days ago is N - 1 - period.
            hist_idx = len(df) - 1 - period
            if hist_idx >= 0:
                hist_price = df.iloc[hist_idx][price_col]
                if not pd.isna(hist_price) and hist_price > 0:
                    returns[f"{period}D"] = float((latest_price / hist_price) - 1.0)
                    valid = True

    return returns

def _calculate_benchmark_returns(benchmark_symbol: str, evaluation_date: Optional[str], lookback_periods: List[int]) -> Dict[str, Any]:
    if get_benchmark_historical_data is None:
        return {}

    hist = get_benchmark_historical_data(
        symbol=benchmark_symbol,
        start_date=None,
        end_date=evaluation_date,
        include_adjusted_close=True
    )

    returns = {f"{period}D": None for period in lookback_periods}
    if hist.get("status") in ["EMPTY", "INVALID"]:
        return returns

    df = hist.get("data", pd.DataFrame())
    if df.empty:
        return returns

    if "adjusted_close" in df.columns:
        price_col = "adjusted_close"
    elif "close" in df.columns:
        price_col = "close"
    else:
        return returns

    latest_price = df.iloc[-1][price_col]
    if pd.isna(latest_price) or latest_price <= 0:
        return returns

    for period in lookback_periods:
        if len(df) > period:
            hist_idx = len(df) - 1 - period
            if hist_idx >= 0:
                hist_price = df.iloc[hist_idx][price_col]
                if not pd.isna(hist_price) and hist_price > 0:
                    returns[f"{period}D"] = float((latest_price / hist_price) - 1.0)

    return returns

def _evaluate_group(
    group_name: str,
    group_type: str,
    evaluation_date: Optional[str] = None,
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Internal helper to evaluate a sector or industry."""
    if lookback_periods is None:
        lookback_periods = DEFAULT_LOOKBACK_PERIODS

    if group_type == "sector":
        constituents = get_sector_stocks(group_name)
    else:
        constituents = get_industry_stocks(group_name)

    # Validate classifications (optional per spec, but we do it to check missing classifications)
    missing_stocks = []
    warnings = []

    returns_matrix = {f"{period}D": [] for period in lookback_periods}

    for symbol in constituents:
        cls_data = get_company_classification(symbol)
        if cls_data is None:
            # explicit missing representation
            warnings.append(f"Classification missing for constituent {symbol}")

        stock_returns = _calculate_constituent_returns(symbol, evaluation_date, lookback_periods)

        has_all_returns = True
        for period in lookback_periods:
            val = stock_returns.get(f"{period}D")
            if val is not None:
                returns_matrix[f"{period}D"].append(val)
            else:
                has_all_returns = False

        if not has_all_returns:
            missing_stocks.append(symbol)

    # Aggregate returns
    performance = {}
    for period in lookback_periods:
        vals = returns_matrix[f"{period}D"]
        if vals:
            performance[f"{period}D"] = float(np.mean(vals))
        else:
            performance[f"{period}D"] = None

    # Data Quality status
    if len(constituents) == 0:
        status = "INSUFFICIENT_DATA"
        warnings.append(f"No constituents found for {group_type} {group_name}")
    elif len(missing_stocks) == len(constituents):
        status = "INSUFFICIENT_DATA"
        warnings.append(f"No valid historical data for any constituents in {group_type}")
    elif len(missing_stocks) > 0:
        status = "PARTIAL"
        warnings.append(f"Missing sufficient historical data for {len(missing_stocks)} constituents")
    else:
        status = "VALID"

    # Benchmark relative strength section
    benchmark_symbol = "NIFTY_50"
    relative_strength = {
        "benchmark": benchmark_symbol,
        **{f"{period}D_rs": None for period in lookback_periods},
    }

    if get_benchmark_historical_data is not None:
        bench_returns = _calculate_benchmark_returns(benchmark_symbol, evaluation_date, lookback_periods)

        has_any_rs = False
        missing_bench = False
        for period in lookback_periods:
            s_ret = performance.get(f"{period}D")
            b_ret = bench_returns.get(f"{period}D")

            if s_ret is not None and b_ret is not None:
                relative_strength[f"{period}D_rs"] = float(s_ret - b_ret)
                has_any_rs = True
            elif s_ret is not None and b_ret is None:
                missing_bench = True

        if has_any_rs and not missing_bench:
            relative_strength["status"] = "VALID"
        elif has_any_rs and missing_bench:
            relative_strength["status"] = "PARTIAL"
            relative_strength["warning"] = "Benchmark data missing for some periods."
        else:
            relative_strength["status"] = "UNAVAILABLE"
            relative_strength["warning"] = "Benchmark data unavailable for calculation."
    else:
        relative_strength["status"] = "UNAVAILABLE"
        relative_strength["warning"] = "Benchmark historical data service is not currently available."

    # Preliminary Sector Score
    preliminary_score = None
    components = {}

    p21 = performance.get("21D")
    p63 = performance.get("63D")

    if p21 is not None or p63 is not None:
        base = 50.0
        c21 = 0.0
        c63 = 0.0
        if p21 is not None:
            c21 = float(max(-25.0, min(25.0, p21 * 100.0)))
        if p63 is not None:
            c63 = float(max(-25.0, min(25.0, p63 * 100.0)))

        preliminary_score = float(base + c21 + c63)
        components = {
            "base": base,
            "21D_component": c21 if p21 is not None else None,
            "63D_component": c63 if p63 is not None else None
        }

    score_data = {
        "score": preliminary_score,
        "components": components,
        "range": {"min": 0.0, "max": 100.0}
    }

    result = {
        group_type: group_name,
        "evaluation_date": evaluation_date,
        "constituents_count": len(constituents),
        "valid_constituents_count": len(constituents) - len(missing_stocks),
        "constituents": constituents,
        "performance": performance,
        "relative_strength": relative_strength,
        "preliminary_score": score_data,
        "data_quality": {
            "status": status,
            "missing_stocks": missing_stocks,
            "warnings": warnings
        }
    }

    return result

def evaluate_sector(
    sector: str,
    evaluation_date: Optional[str] = None,
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Evaluates a sector's performance and relative strength.
    """
    return _evaluate_group(sector, "sector", evaluation_date, lookback_periods)

def evaluate_industry(
    industry: str,
    evaluation_date: Optional[str] = None,
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Evaluates an industry's performance and relative strength.
    """
    return _evaluate_group(industry, "industry", evaluation_date, lookback_periods)

def _rank_groups(
    groups: List[str],
    group_type: str,
    evaluation_date: Optional[str] = None,
    ranking_period: str = "63D",
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Internal helper to rank sectors or industries."""
    if lookback_periods is None:
        lookback_periods = list(DEFAULT_LOOKBACK_PERIODS)

    period_int = int(ranking_period.replace("D", ""))
    if period_int not in lookback_periods:
        lookback_periods.append(period_int)

    results = []

    for group in groups:
        if group_type == "sector":
            res = evaluate_sector(group, evaluation_date, lookback_periods)
        else:
            res = evaluate_industry(group, evaluation_date, lookback_periods)

        perf = res["performance"].get(ranking_period)

        results.append({
            group_type: group,
            "performance": perf,
            "relative_strength": res["relative_strength"],
            "preliminary_score": res["preliminary_score"],
            "constituents_count": res["constituents_count"],
            "valid_constituents_count": res["valid_constituents_count"],
            "data_quality": res["data_quality"]["status"],
            "warnings": res["data_quality"]["warnings"]
        })

    rankable = [g for g in results if g["performance"] is not None]
    unrankable = [g for g in results if g["performance"] is None]

    # Sort alphabetically first (secondary sort for ties)
    rankable.sort(key=lambda x: x[group_type])
    # Then sort by performance descending (primary sort)
    rankable.sort(key=lambda x: x["performance"], reverse=True)

    ranked_output = []
    for i, g in enumerate(rankable):
        g_out = {"rank": i + 1}
        g_out.update(g)
        ranked_output.append(g_out)

    unrankable.sort(key=lambda x: x[group_type])
    for g in unrankable:
        g_out = {"rank": None}
        g_out.update(g)
        ranked_output.append(g_out)

    output_key = f"ranked_{group_type}s"
    if group_type == "industry":
        output_key = "ranked_industries"

    return {
        "evaluation_date": evaluation_date,
        "ranking_period": ranking_period,
        output_key: ranked_output
    }

def rank_sectors(
    sectors: List[str],
    evaluation_date: Optional[str] = None,
    ranking_period: str = "63D",
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Ranks multiple sectors based on their aggregate performance over a specific period.
    """
    return _rank_groups(sectors, "sector", evaluation_date, ranking_period, lookback_periods)

def rank_industries(
    industries: List[str],
    evaluation_date: Optional[str] = None,
    ranking_period: str = "63D",
    lookback_periods: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Ranks multiple industries based on their aggregate performance over a specific period.
    """
    return _rank_groups(industries, "industry", evaluation_date, ranking_period, lookback_periods)
