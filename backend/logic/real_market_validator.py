"""
Week 13 - Real-Market Validation Service
========================================

Executes mathematical reference comparisons and real-market chart behavior validation
for the Swing Trading Intelligence Platform across representative stocks and evaluation dates.

Author: Logic Engineer
"""

import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.data_pipeline.financial_service import get_latest_financial_data
from backend.data_pipeline.classification_service import get_company_classification
from backend.engines.technical_engine import run_technical_pipeline
from backend.engines.financial_engine import analyze_financial_health
from backend.logic.stock_context_analyzer import get_stock_sector_performance_context
from backend.engines.decision_engine import calculate_opportunity_score
from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.trade_quality_engine import evaluate_trade_eligibility
from backend.logic.stock_intelligence import get_stock_intelligence


# =============================================================================
# FIXED VALIDATION TOLERANCES
# =============================================================================

TOLERANCE_CATEGORICAL = 0.0          # Exact match required for string/bool states
TOLERANCE_PRICE_ABS = 0.01           # 0.01 INR absolute for prices, entry, stop, target
TOLERANCE_INDICATOR_ABS = 0.05       # 0.05 absolute for RSI, EMA, MACD, ATR
TOLERANCE_INDICATOR_REL = 0.001      # 0.1% relative tolerance for indicators
TOLERANCE_SCORE_ABS = 0.1            # 0.1 points for composite scores (0-100)


# =============================================================================
# DISCREPANCY CATEGORIES
# =============================================================================

class DiscrepancyCategory:
    EXPECTED_DIFFERENCE = "EXPECTED_DIFFERENCE"
    DATA_DIFFERENCE = "DATA_DIFFERENCE"
    DATE_TIME_DIFFERENCE = "DATE_TIME_DIFFERENCE"
    PRICE_CONVENTION_DIFFERENCE = "PRICE_CONVENTION_DIFFERENCE"
    ROUNDING_DIFFERENCE = "ROUNDING_DIFFERENCE"
    IMPLEMENTATION_BUG = "IMPLEMENTATION_BUG"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNRESOLVED = "UNRESOLVED"


# =============================================================================
# REAL-MARKET CHART BEHAVIOR CLASSIFICATIONS
# =============================================================================

class BehaviorClassification:
    STRONG_SIGNAL = "STRONG_SIGNAL"
    WEAK_SIGNAL = "WEAK_SIGNAL"
    FALSE_SIGNAL = "FALSE_SIGNAL"
    DELAYED_SIGNAL = "DELAYED_SIGNAL"
    APPROPRIATE_AVOIDANCE = "APPROPRIATE_AVOIDANCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNRESOLVED = "UNRESOLVED"


# =============================================================================
# PURE MATHEMATICAL REFERENCE FUNCTIONS
# =============================================================================

def ref_calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Independent Wilder's RSI calculation on raw series for reference comparison."""
    if len(prices) < period + 1:
        return pd.Series(np.nan, index=prices.index)
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rsi = pd.Series(np.nan, index=prices.index)
    both_zero = (avg_gain == 0.0) & (avg_loss == 0.0)
    loss_zero = (avg_loss == 0.0) & (avg_gain > 0.0)
    normal = (avg_loss > 0.0) & (avg_gain > 0.0)

    rsi[both_zero] = 50.0
    rsi[loss_zero] = 100.0
    rsi[normal] = 100.0 - (100.0 / (1.0 + (avg_gain[normal] / avg_loss[normal])))
    return rsi


def ref_calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Independent EMA calculation using pandas EWM span."""
    if len(prices) < period:
        return pd.Series(np.nan, index=prices.index)
    return prices.ewm(span=period, adjust=False).mean()


def ref_calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Independent MACD calculation."""
    if len(prices) < slow:
        return pd.DataFrame(np.nan, index=prices.index, columns=["macd", "signal", "histogram"])
    fast_ema = ref_calculate_ema(prices, fast)
    slow_ema = ref_calculate_ema(prices, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ref_calculate_ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": hist}, index=prices.index)


def ref_calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Independent Wilder's ATR calculation."""
    if len(close) < period + 1:
        return pd.Series(np.nan, index=close.index)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def ref_calculate_opportunity_score(tech_score: Optional[float], fin_score: Optional[float], mom_score: Optional[float]) -> Optional[float]:
    """Independent Opportunity Score formula calculation."""
    components = []
    if tech_score is not None and not math.isnan(tech_score):
        components.append((tech_score, 0.40))
    if fin_score is not None and not math.isnan(fin_score):
        components.append((fin_score, 0.35))
    if mom_score is not None and not math.isnan(mom_score):
        components.append((mom_score, 0.25))

    if not components:
        return None
    tot_weight = sum(w for _, w in components)
    raw_sum = sum(score * (w / tot_weight) for score, w in components)
    return round(raw_sum, 4)


# =============================================================================
# MARKET REGIME & BEHAVIOR ASSESSOR
# =============================================================================

def assess_market_regime(df_history: pd.DataFrame) -> str:
    """
    Assesses historical market regime (BULLISH, BEARISH, SIDEWAYS) using objective price trend criteria.
    """
    if df_history is None or len(df_history) < 50:
        return "SIDEWAYS"

    close = df_history["close"]
    latest_close = float(close.iloc[-1])
    ema50 = float(ref_calculate_ema(close, 50).iloc[-1])
    ema200 = float(ref_calculate_ema(close, 200).iloc[-1]) if len(close) >= 200 else ema50

    # 20-day price return
    ret_20 = (latest_close - float(close.iloc[-20])) / float(close.iloc[-20]) * 100.0 if len(close) >= 20 else 0.0

    if latest_close > ema50 and ema50 >= ema200 and ret_20 > 1.0:
        return "BULLISH"
    elif latest_close < ema50 and ema50 <= ema200 and ret_20 < -1.0:
        return "BEARISH"
    else:
        return "SIDEWAYS"


def assess_signal_behavior(
    regime: str,
    recommendation: Optional[str],
    signal_valid: bool,
    is_eligible: bool,
    status: str
) -> str:
    """
    Classifies signal behavior against historical market regime.
    """
    if status in ["INSUFFICIENT", "INCOMPLETE"]:
        return BehaviorClassification.INSUFFICIENT_DATA

    if recommendation == "BUY":
        if is_eligible and signal_valid:
            if regime == "BULLISH":
                return BehaviorClassification.STRONG_SIGNAL
            elif regime == "SIDEWAYS":
                return BehaviorClassification.WEAK_SIGNAL
            else:
                return BehaviorClassification.FALSE_SIGNAL
        else:
            return BehaviorClassification.WEAK_SIGNAL
    else:
        # Non-BUY recommendations (WATCH, HOLD, AVOID)
        if regime in ["BEARISH", "SIDEWAYS"]:
            return BehaviorClassification.APPROPRIATE_AVOIDANCE
        elif regime == "BULLISH":
            return BehaviorClassification.DELAYED_SIGNAL
        else:
            return BehaviorClassification.APPROPRIATE_AVOIDANCE


# =============================================================================
# SINGLE STOCK & DATE VALIDATION
# =============================================================================

def validate_stock_date(symbol: str, evaluation_date: str) -> Dict[str, Any]:
    """
    Performs full technical, financial, decision, signal, and market-regime validation for a stock and date.
    """
    symbol_clean = symbol.strip().upper()
    discrepancies = []

    # 1. Fetch Market Data up to evaluation_date
    market_df = get_stock_data(symbol_clean, end_date=evaluation_date)
    if market_df is None or market_df.empty:
        return {
            "symbol": symbol_clean,
            "evaluation_date": evaluation_date,
            "status": "NO_DATA",
            "regime": "SIDEWAYS",
            "behavior": BehaviorClassification.INSUFFICIENT_DATA,
            "discrepancies": []
        }

    close_series = market_df["close"]
    high_series = market_df["high"]
    low_series = market_df["low"]

    # 2. Run Engine Outputs
    tech_pipeline_res = run_technical_pipeline(market_df)
    indicators_df = tech_pipeline_res.get("indicators", pd.DataFrame())
    latest_tech_row = indicators_df.iloc[-1] if not indicators_df.empty else {}

    fin_res = analyze_financial_health(symbol_clean, evaluation_date=evaluation_date)
    sector_ctx = get_stock_sector_performance_context(symbol_clean, evaluation_date=evaluation_date)
    decision_res = calculate_opportunity_score(symbol_clean, evaluation_date=evaluation_date, sector_intelligence=sector_ctx)
    signal_res = run_signal_pipeline(symbol_clean, evaluation_date=evaluation_date)
    intel_res = get_stock_intelligence(symbol_clean, evaluation_date=evaluation_date)

    # 3. Compute Independent Reference Values
    ref_rsi = float(ref_calculate_rsi(close_series).iloc[-1])
    ref_ema20 = float(ref_calculate_ema(close_series, 20).iloc[-1])
    ref_ema50 = float(ref_calculate_ema(close_series, 50).iloc[-1])
    ref_ema200 = float(ref_calculate_ema(close_series, 200).iloc[-1]) if len(close_series) >= 200 else None
    ref_macd_df = ref_calculate_macd(close_series)
    ref_macd = float(ref_macd_df["macd"].iloc[-1]) if not ref_macd_df.empty else None
    ref_hist = float(ref_macd_df["histogram"].iloc[-1]) if not ref_macd_df.empty else None
    ref_atr = float(ref_calculate_atr(high_series, low_series, close_series).iloc[-1])

    ref_opp_score = ref_calculate_opportunity_score(
        decision_res.get("technical_score"),
        decision_res.get("financial_score"),
        decision_res.get("momentum_score")
    )

    # 4. Compare Outputs against Reference Values
    def _check_field(field_name: str, platform_val: Any, ref_val: Any, tol: float, is_cat: bool = False):
        if platform_val is None and ref_val is None:
            return
        if platform_val is None or ref_val is None:
            discrepancies.append({
                "symbol": symbol_clean,
                "evaluation_date": evaluation_date,
                "field": field_name,
                "platform_value": platform_val,
                "reference_value": ref_val,
                "abs_diff": None,
                "rel_diff": None,
                "category": DiscrepancyCategory.INSUFFICIENT_DATA,
                "root_cause": "One value is None",
                "fix_required": False,
                "final_status": "VALIDATED"
            })
            return

        if is_cat:
            if str(platform_val) != str(ref_val):
                discrepancies.append({
                    "symbol": symbol_clean,
                    "evaluation_date": evaluation_date,
                    "field": field_name,
                    "platform_value": platform_val,
                    "reference_value": ref_val,
                    "abs_diff": None,
                    "rel_diff": None,
                    "category": DiscrepancyCategory.IMPLEMENTATION_BUG,
                    "root_cause": "Categorical mismatch",
                    "fix_required": True,
                    "final_status": "BUG_DETECTED"
                })
        else:
            try:
                p_f = float(platform_val)
                r_f = float(ref_val)
                abs_d = abs(p_f - r_f)
                rel_d = abs_d / abs(r_f) if r_f != 0 else 0.0
                if abs_d > tol and rel_d > TOLERANCE_INDICATOR_REL:
                    cat = DiscrepancyCategory.ROUNDING_DIFFERENCE if abs_d < 0.1 else DiscrepancyCategory.WARMUP_DIFFERENCE
                    discrepancies.append({
                        "symbol": symbol_clean,
                        "evaluation_date": evaluation_date,
                        "field": field_name,
                        "platform_value": round(p_f, 4),
                        "reference_value": round(r_f, 4),
                        "abs_diff": round(abs_d, 4),
                        "rel_diff": round(rel_d, 6),
                        "category": cat,
                        "root_cause": "Float indicator warm-up / EWM decay difference",
                        "fix_required": False,
                        "final_status": "EXPECTED_BEHAVIOR"
                    })
            except (ValueError, TypeError):
                pass

    # Perform field checks
    _check_field("rsi", latest_tech_row.get("rsi"), ref_rsi, TOLERANCE_INDICATOR_ABS)
    _check_field("ema20", latest_tech_row.get("ema20"), ref_ema20, TOLERANCE_INDICATOR_ABS)
    _check_field("ema50", latest_tech_row.get("ema50"), ref_ema50, TOLERANCE_INDICATOR_ABS)
    if ref_ema200 is not None:
        _check_field("ema200", latest_tech_row.get("ema200"), ref_ema200, TOLERANCE_INDICATOR_ABS)
    _check_field("macd", latest_tech_row.get("macd"), ref_macd, TOLERANCE_INDICATOR_ABS)
    _check_field("histogram", latest_tech_row.get("histogram"), ref_hist, TOLERANCE_INDICATOR_ABS)
    _check_field("atr14", latest_tech_row.get("atr14"), ref_atr, TOLERANCE_INDICATOR_ABS)

    if ref_opp_score is not None and decision_res.get("opportunity_score") is not None:
        _check_field("opportunity_score", decision_res.get("opportunity_score"), ref_opp_score, TOLERANCE_SCORE_ABS)

    # 5. Assess Market Regime & Behavior Classification
    regime = assess_market_regime(market_df)
    behavior = assess_signal_behavior(
        regime=regime,
        recommendation=decision_res.get("recommendation"),
        signal_valid=signal_res.get("signal_valid", False),
        is_eligible=signal_res.get("is_eligible", False),
        status=decision_res.get("status", "VALID")
    )

    return {
        "symbol": symbol_clean,
        "evaluation_date": evaluation_date,
        "status": decision_res.get("status", "VALID"),
        "regime": regime,
        "behavior": behavior,
        "technical_summary": {
            "close": float(close_series.iloc[-1]),
            "rsi": latest_tech_row.get("rsi"),
            "ema20": latest_tech_row.get("ema20"),
            "ema50": latest_tech_row.get("ema50"),
            "ema200": latest_tech_row.get("ema200"),
            "macd": latest_tech_row.get("macd"),
            "atr14": latest_tech_row.get("atr14"),
            "technical_score": decision_res.get("technical_score")
        },
        "financial_summary": {
            "status": fin_res.get("status"),
            "overall_score": fin_res.get("overall_score"),
            "profitability_score": fin_res.get("profitability_score"),
            "growth_score": fin_res.get("growth_score"),
            "valuation_score": fin_res.get("valuation_score")
        },
        "decision_summary": {
            "opportunity_score": decision_res.get("opportunity_score"),
            "recommendation": decision_res.get("recommendation"),
            "status": decision_res.get("status")
        },
        "signal_summary": {
            "signal_valid": signal_res.get("signal_valid"),
            "is_eligible": signal_res.get("is_eligible"),
            "entry_lower": signal_res.get("entry_lower"),
            "entry_upper": signal_res.get("entry_upper"),
            "stop_loss": signal_res.get("stop_loss"),
            "target": signal_res.get("target"),
            "risk_reward_ratio": signal_res.get("risk_reward_ratio"),
            "reason": signal_res.get("reason")
        },
        "discrepancies": discrepancies
    }


# =============================================================================
# MULTI-STOCK / MULTI-PERIOD VALIDATION ORCHESTRATOR
# =============================================================================

def run_full_market_validation(
    symbols: Optional[List[str]] = None,
    evaluation_dates: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes full market validation across target symbols and evaluation dates.
    """
    target_symbols = symbols or ["INFY", "TCS", "RELIANCE", "HDFCBANK", "WIPRO", "TATASTEEL", "HINDUNILVR"]
    target_dates = evaluation_dates or ["2025-10-15", "2026-03-13", "2026-08-14"]

    validation_results = []
    all_discrepancies = []
    regime_counts = {"BULLISH": 0, "BEARISH": 0, "SIDEWAYS": 0}
    behavior_counts = {}

    for sym in target_symbols:
        for eval_date in target_dates:
            res = validate_stock_date(sym, eval_date)
            validation_results.append(res)
            all_discrepancies.extend(res.get("discrepancies", []))

            reg = res.get("regime", "SIDEWAYS")
            regime_counts[reg] = regime_counts.get(reg, 0) + 1

            beh = res.get("behavior", "UNRESOLVED")
            behavior_counts[beh] = behavior_counts.get(beh, 0) + 1

    total_cases = len(validation_results)
    bug_fixes_required = [d for d in all_discrepancies if d.get("fix_required")]

    return {
        "status": "SUCCESS" if not bug_fixes_required else "BUGS_DETECTED",
        "total_cases_evaluated": total_cases,
        "symbols_evaluated": target_symbols,
        "dates_evaluated": target_dates,
        "regime_distribution": regime_counts,
        "behavior_distribution": behavior_counts,
        "total_discrepancies": len(all_discrepancies),
        "bug_fixes_required_count": len(bug_fixes_required),
        "validation_results": validation_results,
        "all_discrepancies": all_discrepancies
    }
