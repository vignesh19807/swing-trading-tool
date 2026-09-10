"""
Week 14 - TradingView Validation Infrastructure
================================================

Provides a validation layer to compare platform technical indicator values
and market data against manually recorded TradingView observations.

IMPORTANT CONSTRAINTS:
- Does NOT fabricate or generate TradingView reference data.
- Unrecorded TradingView observations remain explicitly None / PENDING.
- Reuses Week 13 tolerances and discrepancy categories directly from real_market_validator.py.
- Platform calculation engines and Data Engineer files are NOT modified.
- Proprietary platform outputs (entry zone, stop loss, target, risk/reward) are clearly
  distinguished from standard TradingView reference indicators.

Author: Logic Engineer
"""

import math
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import run_technical_pipeline
from backend.logic.historical_signal_evaluator import evaluate_historical_signal
from backend.logic.real_market_validator import (
    TOLERANCE_CATEGORICAL,
    TOLERANCE_PRICE_ABS,
    TOLERANCE_INDICATOR_ABS,
    TOLERANCE_INDICATOR_REL,
    TOLERANCE_SCORE_ABS,
    DiscrepancyCategory,
)

# =============================================================================
# APPROVED 15-SCENARIO VALIDATION MATRIX
# =============================================================================

APPROVED_VALIDATION_STOCKS = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "TATASTEEL"]
APPROVED_VALIDATION_DATES = ["2025-10-15", "2026-03-13", "2026-08-14"]


# =============================================================================
# TRADINGVIEW OBSERVATIONS REGISTRY (INITIALIZED AS UNRECORDED / PENDING)
# =============================================================================

def create_empty_observation(symbol: str, evaluation_date: str) -> Dict[str, Any]:
    """
    Create a standardized empty TradingView observation record.
    Unrecorded values are explicitly set to None, with status 'PENDING'.
    """
    return {
        "metadata": {
            "symbol": symbol.strip().upper(),
            "exchange": "NSE",
            "evaluation_date": evaluation_date,
            "timeframe": "1D",
            "timezone": "IST (+05:30)",
            "data_adjustment": "Unadjusted Close",
            "recording_timestamp": None,
            "status": "PENDING"
        },
        "ohlcv": {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None
        },
        "indicators": {
            "rsi14": None,
            "ema20": None,
            "ema50": None,
            "ema200": None,
            "macd_line": None,
            "macd_signal": None,
            "macd_histogram": None,
            "atr14": None
        },
        "market_structure": {
            "visual_support": None,
            "visual_resistance": None,
            "observable_trend": None
        }
    }


# In-memory registry of manual TradingView observations initialized as PENDING for all 15 scenarios.
TRADINGVIEW_OBSERVATIONS: Dict[str, Dict[str, Any]] = {
    f"{sym}_{date}": create_empty_observation(sym, date)
    for sym in APPROVED_VALIDATION_STOCKS
    for date in APPROVED_VALIDATION_DATES
}


def register_tradingview_observation(
    symbol: str,
    evaluation_date: str,
    observation: Dict[str, Any]
) -> None:
    """
    Register a manually observed TradingView record for a stock and evaluation date.
    Does NOT accept fabricated data; validates schema structure before storing.
    """
    sym_clean = symbol.strip().upper()
    key = f"{sym_clean}_{evaluation_date}"

    if not isinstance(observation, dict):
        raise TypeError("Observation payload must be a dictionary.")

    # Ensure required top-level sections exist
    required_sections = {"metadata", "ohlcv", "indicators", "market_structure"}
    missing_sections = required_sections - set(observation.keys())
    if missing_sections:
        raise ValueError(f"Observation payload missing required sections: {sorted(list(missing_sections))}")

    # Copy and update status to RECORDED if valid data supplied
    obs_copy = {
        "metadata": dict(observation.get("metadata", {})),
        "ohlcv": dict(observation.get("ohlcv", {})),
        "indicators": dict(observation.get("indicators", {})),
        "market_structure": dict(observation.get("market_structure", {}))
    }

    obs_copy["metadata"]["symbol"] = sym_clean
    obs_copy["metadata"]["evaluation_date"] = evaluation_date
    obs_copy["metadata"]["status"] = "RECORDED" if obs_copy["metadata"].get("recording_timestamp") else "RECORDED"

    TRADINGVIEW_OBSERVATIONS[key] = obs_copy


def get_tradingview_observation(symbol: str, evaluation_date: str) -> Dict[str, Any]:
    """
    Retrieve the registered TradingView observation for a stock and evaluation date.
    Returns an empty PENDING record if no observation has been registered yet.
    """
    sym_clean = symbol.strip().upper()
    key = f"{sym_clean}_{evaluation_date}"
    if key in TRADINGVIEW_OBSERVATIONS:
        return TRADINGVIEW_OBSERVATIONS[key]
    return create_empty_observation(sym_clean, evaluation_date)


# =============================================================================
# SINGLE SCENARIO VALIDATION RUNNER
# =============================================================================

def validate_tradingview_observation(
    symbol: str,
    evaluation_date: str,
    custom_observation: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validates platform engine outputs against a manually recorded TradingView observation
    for a single stock symbol and historical evaluation_date.

    Parameters
    ----------
    symbol : str
        NSE ticker symbol (e.g., "INFY").
    evaluation_date : str
        Historical date (YYYY-MM-DD).
    custom_observation : dict, optional
        Optional custom TradingView observation payload. If None, retrieves from registry.

    Returns
    -------
    dict
        Structured comparison result exposing metadata, platform values, reference values,
        field-by-field deltas, discrepancy categories, and overall scenario status.
    """
    sym_clean = symbol.strip().upper()

    # 1. Fetch Reference Observation
    ref_obs = custom_observation or get_tradingview_observation(sym_clean, evaluation_date)
    ref_meta = ref_obs.get("metadata", {})
    ref_ohlcv = ref_obs.get("ohlcv", {})
    ref_indicators = ref_obs.get("indicators", {})
    ref_market_struct = ref_obs.get("market_structure", {})

    # Determine if reference observation is recorded or pending
    has_ref_data = any(v is not None for v in ref_indicators.values()) or any(v is not None for v in ref_ohlcv.values())
    observation_status = "RECORDED" if has_ref_data else "PENDING"

    # 2. Fetch Point-in-Time Historical Market Data
    market_df = get_stock_data(sym_clean, end_date=evaluation_date)

    if market_df is None or market_df.empty:
        return {
            "symbol": sym_clean,
            "evaluation_date": evaluation_date,
            "tradingview_observation_status": observation_status,
            "overall_status": "INSUFFICIENT_DATA",
            "platform_values": None,
            "reference_values": ref_obs,
            "comparisons": [],
            "discrepancies": [{
                "field": "market_data",
                "platform_value": None,
                "reference_value": None,
                "abs_diff": None,
                "rel_diff": None,
                "tolerance": None,
                "status": "FAIL",
                "discrepancy_category": DiscrepancyCategory.INSUFFICIENT_DATA,
                "reason": f"No historical market data in database for {sym_clean} on or before {evaluation_date}"
            }]
        }

    # 3. Calculate Platform Technical Indicators (Point-in-Time)
    tech_pipeline_res = run_technical_pipeline(market_df)
    indicators_df = tech_pipeline_res.get("indicators", pd.DataFrame())
    latest_tech = indicators_df.iloc[-1] if not indicators_df.empty else {}

    # Extract latest bar OHLCV from platform market data
    latest_bar = market_df.iloc[-1]
    platform_ohlcv = {
        "open": float(latest_bar["open"]) if "open" in latest_bar and pd.notna(latest_bar["open"]) else None,
        "high": float(latest_bar["high"]) if "high" in latest_bar and pd.notna(latest_bar["high"]) else None,
        "low": float(latest_bar["low"]) if "low" in latest_bar and pd.notna(latest_bar["low"]) else None,
        "close": float(latest_bar["close"]) if pd.notna(latest_bar["close"]) else None,
        "volume": float(latest_bar["volume"]) if pd.notna(latest_bar["volume"]) else None
    }

    platform_indicators = {
        "rsi14": float(latest_tech.get("rsi")) if pd.notna(latest_tech.get("rsi")) else None,
        "ema20": float(latest_tech.get("ema20")) if pd.notna(latest_tech.get("ema20")) else None,
        "ema50": float(latest_tech.get("ema50")) if pd.notna(latest_tech.get("ema50")) else None,
        "ema200": float(latest_tech.get("ema200")) if pd.notna(latest_tech.get("ema200")) else None,
        "macd_line": float(latest_tech.get("macd")) if pd.notna(latest_tech.get("macd")) else None,
        "macd_signal": float(latest_tech.get("signal")) if pd.notna(latest_tech.get("signal")) else None,
        "macd_histogram": float(latest_tech.get("histogram")) if pd.notna(latest_tech.get("histogram")) else None,
        "atr14": float(latest_tech.get("atr14")) if pd.notna(latest_tech.get("atr14")) else None
    }

    # 4. Fetch Proprietary Platform Signal & Decision Outputs
    signal_res = evaluate_historical_signal(sym_clean, evaluation_date=evaluation_date)

    platform_outputs = {
        "technical_score": float(latest_tech.get("technical_score")) if pd.notna(latest_tech.get("technical_score")) else None,
        "recommendation": signal_res.get("recommendation"),
        "entry_lower": signal_res.get("entry_lower"),
        "entry_upper": signal_res.get("entry_upper"),
        "stop_loss": signal_res.get("stop_loss"),
        "target": signal_res.get("target"),
        "risk": signal_res.get("risk"),
        "reward": signal_res.get("reward"),
        "risk_reward_ratio": signal_res.get("risk_reward_ratio"),
        "signal_valid": signal_res.get("signal_valid"),
        "is_eligible": signal_res.get("is_eligible"),
        "trade_quality": signal_res.get("trade_quality")
    }

    # 5. Perform Field-by-Field Comparison
    comparisons = []
    discrepancies = []

    def _compare(
        field_name: str,
        plat_val: Any,
        ref_val: Any,
        abs_tolerance: float,
        rel_tolerance: Optional[float] = None,
        is_categorical: bool = False
    ):
        record = {
            "field": field_name,
            "platform_value": plat_val,
            "reference_value": ref_val,
            "abs_diff": None,
            "rel_diff": None,
            "tolerance": abs_tolerance,
            "status": "PENDING",
            "discrepancy_category": None
        }

        # Unrecorded or missing values
        if plat_val is None or ref_val is None:
            record["status"] = "PENDING" if ref_val is None else "FAIL"
            record["discrepancy_category"] = DiscrepancyCategory.INSUFFICIENT_DATA
            comparisons.append(record)
            if record["status"] == "FAIL":
                discrepancies.append(record)
            return

        if is_categorical:
            if str(plat_val) == str(ref_val):
                record["status"] = "PASS"
            else:
                record["status"] = "FAIL"
                record["discrepancy_category"] = DiscrepancyCategory.UNRESOLVED
                discrepancies.append(record)
            comparisons.append(record)
            return

        # Numeric comparisons
        try:
            p_f = float(plat_val)
            r_f = float(ref_val)
            abs_diff = abs(p_f - r_f)

            # Safe relative diff calculation (zero-reference safe)
            rel_diff = abs_diff / abs(r_f) if abs(r_f) > 1e-9 else 0.0

            record["abs_diff"] = round(abs_diff, 6)
            record["rel_diff"] = round(rel_diff, 6)

            # Check absolute tolerance or relative tolerance
            is_abs_pass = abs_diff <= abs_tolerance
            is_rel_pass = (rel_tolerance is not None) and (rel_diff <= rel_tolerance)

            if is_abs_pass or is_rel_pass:
                record["status"] = "PASS"
            else:
                record["status"] = "FAIL"
                # Safe automatic classification: tiny precision diff (< 0.01) is rounding, otherwise UNRESOLVED
                if abs_diff < 0.01:
                    record["discrepancy_category"] = DiscrepancyCategory.ROUNDING_DIFFERENCE
                else:
                    record["discrepancy_category"] = DiscrepancyCategory.UNRESOLVED
                discrepancies.append(record)
        except (ValueError, TypeError):
            record["status"] = "FAIL"
            record["discrepancy_category"] = DiscrepancyCategory.INSUFFICIENT_DATA
            discrepancies.append(record)

        comparisons.append(record)

    # Compare OHLCV
    _compare("open", platform_ohlcv["open"], ref_ohlcv.get("open"), TOLERANCE_PRICE_ABS)
    _compare("high", platform_ohlcv["high"], ref_ohlcv.get("high"), TOLERANCE_PRICE_ABS)
    _compare("low", platform_ohlcv["low"], ref_ohlcv.get("low"), TOLERANCE_PRICE_ABS)
    _compare("close", platform_ohlcv["close"], ref_ohlcv.get("close"), TOLERANCE_PRICE_ABS)
    _compare("volume", platform_ohlcv["volume"], ref_ohlcv.get("volume"), abs_tolerance=1.0)

    # Compare Indicators
    _compare("rsi14", platform_indicators["rsi14"], ref_indicators.get("rsi14"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("ema20", platform_indicators["ema20"], ref_indicators.get("ema20"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("ema50", platform_indicators["ema50"], ref_indicators.get("ema50"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("ema200", platform_indicators["ema200"], ref_indicators.get("ema200"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("macd_line", platform_indicators["macd_line"], ref_indicators.get("macd_line"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("macd_signal", platform_indicators["macd_signal"], ref_indicators.get("macd_signal"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("macd_histogram", platform_indicators["macd_histogram"], ref_indicators.get("macd_histogram"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)
    _compare("atr14", platform_indicators["atr14"], ref_indicators.get("atr14"), TOLERANCE_INDICATOR_ABS, TOLERANCE_INDICATOR_REL)

    # Determine overall status
    if observation_status == "PENDING":
        overall_status = "PENDING"
    elif discrepancies:
        overall_status = "FAIL"
    else:
        overall_status = "PASS"

    return {
        "symbol": sym_clean,
        "evaluation_date": evaluation_date,
        "tradingview_observation_status": observation_status,
        "overall_status": overall_status,
        "platform_values": {
            "ohlcv": platform_ohlcv,
            "indicators": platform_indicators,
            "outputs": platform_outputs
        },
        "reference_values": ref_obs,
        "comparisons": comparisons,
        "discrepancies": discrepancies
    }


# =============================================================================
# 15-SCENARIO ORCHESTRATOR
# =============================================================================

def run_tradingview_market_validation(
    symbols: Optional[List[str]] = None,
    evaluation_dates: Optional[List[str]] = None,
    custom_observations: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Executes full TradingView validation across the approved 15-scenario matrix (5 stocks x 3 dates).

    Parameters
    ----------
    symbols : list of str, optional
        List of stock symbols. Defaults to APPROVED_VALIDATION_STOCKS.
    evaluation_dates : list of str, optional
        List of evaluation dates. Defaults to APPROVED_VALIDATION_DATES.
    custom_observations : dict, optional
        Dictionary mapping 'SYMBOL_DATE' to custom TradingView observation records.

    Returns
    -------
    dict
        Structured validation results covering all scenarios, aggregate counts,
        and discrepancy breakdowns.
    """
    target_symbols = symbols or APPROVED_VALIDATION_STOCKS
    target_dates = evaluation_dates or APPROVED_VALIDATION_DATES

    scenario_results = []
    all_discrepancies = []

    recorded_count = 0
    pending_count = 0
    passed_count = 0
    failed_count = 0

    for sym in target_symbols:
        for eval_date in target_dates:
            key = f"{sym.strip().upper()}_{eval_date}"
            custom_obs = (custom_observations or {}).get(key)

            res = validate_tradingview_observation(sym, eval_date, custom_observation=custom_obs)
            scenario_results.append(res)
            all_discrepancies.extend(res.get("discrepancies", []))

            obs_st = res.get("tradingview_observation_status", "PENDING")
            if obs_st == "RECORDED":
                recorded_count += 1
            else:
                pending_count += 1

            ov_st = res.get("overall_status", "PENDING")
            if ov_st == "PASS":
                passed_count += 1
            elif ov_st == "FAIL":
                failed_count += 1

    total_scenarios = len(scenario_results)

    if pending_count == total_scenarios:
        overall_validation_status = "PENDING_REFERENCE_DATA"
    elif failed_count > 0:
        overall_validation_status = "DISCREPANCIES_FOUND"
    else:
        overall_validation_status = "VALIDATED_SUCCESS"

    return {
        "status": overall_validation_status,
        "total_scenarios_evaluated": total_scenarios,
        "recorded_scenarios_count": recorded_count,
        "pending_scenarios_count": pending_count,
        "passed_scenarios_count": passed_count,
        "failed_scenarios_count": failed_count,
        "symbols_evaluated": target_symbols,
        "dates_evaluated": target_dates,
        "scenario_results": scenario_results,
        "all_discrepancies": all_discrepancies
    }
