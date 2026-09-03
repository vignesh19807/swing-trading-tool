"""
Technical Explanation Logic
===========================

Generates structured explanations for Technical Engine outputs.
Reads the exact output row from `run_technical_pipeline` and classifies
factors based strictly on existing logic.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


def _is_invalid(val: Any) -> bool:
    if val is None or pd.isna(val):
        return True
    try:
        f = float(val)
        return np.isnan(f) or np.isinf(f)
    except (ValueError, TypeError):
        return True


def explain_rsi(latest_row: pd.Series) -> Dict[str, Any]:
    rsi_val = latest_row.get("rsi")
    rsi_score = latest_row.get("rsi_score")

    if _is_invalid(rsi_val) or _is_invalid(rsi_score):
        return {
            "category": "Technical",
            "metric": "RSI",
            "value": "Unavailable",
            "interpretation": "Insufficient historical data for RSI calculation.",
            "sentiment": "missing"
        }

    rsi_val = float(rsi_val)
    rsi_score = float(rsi_score)
    value_str = f"{rsi_val:.2f}"

    if rsi_score >= 24.0:
        sentiment = "positive"
        interpretation = "RSI is in a strong momentum zone (40-70)."
    elif rsi_score <= 10.0:
        sentiment = "negative"
        if rsi_val < 30:
            interpretation = "RSI indicates oversold conditions with weak momentum (<30)."
        else:
            interpretation = "RSI indicates overbought conditions (>=80)."
    else:
        sentiment = "neutral"
        interpretation = "RSI momentum is neutral or slightly elevated/depressed."

    return {
        "category": "Technical",
        "metric": "RSI",
        "value": value_str,
        "interpretation": interpretation,
        "sentiment": sentiment
    }


def explain_macd(latest_row: pd.Series) -> Dict[str, Any]:
    macd_val = latest_row.get("macd")
    signal_val = latest_row.get("signal")
    macd_score = latest_row.get("macd_score")

    if _is_invalid(macd_val) or _is_invalid(signal_val) or _is_invalid(macd_score):
        return {
            "category": "Technical",
            "metric": "MACD",
            "value": "Unavailable",
            "interpretation": "Insufficient historical data for MACD calculation.",
            "sentiment": "missing"
        }

    macd_score = float(macd_score)
    value_str = f"MACD: {float(macd_val):.2f}, Signal: {float(signal_val):.2f}"

    if macd_score >= 24.0:
        sentiment = "positive"
        interpretation = "MACD line is above the Signal line with positive histogram, indicating strong bullish momentum."
    elif macd_score <= 12.0:
        sentiment = "negative"
        interpretation = "MACD line is below the Signal line, indicating bearish momentum."
    else:
        sentiment = "neutral"
        interpretation = "MACD and Signal line are approximately equal or showing mixed signals."

    return {
        "category": "Technical",
        "metric": "MACD",
        "value": value_str,
        "interpretation": interpretation,
        "sentiment": sentiment
    }


def explain_trend(latest_row: pd.Series) -> Dict[str, Any]:
    close_val = latest_row.get("close")
    ema20 = latest_row.get("ema20")
    ema50 = latest_row.get("ema50")
    ema200 = latest_row.get("ema200")
    trend_score = latest_row.get("trend_score")

    if _is_invalid(trend_score) or _is_invalid(close_val) or _is_invalid(ema50):
        return {
            "category": "Technical",
            "metric": "Trend",
            "value": "Unavailable",
            "interpretation": "Insufficient historical data for Trend (EMA) calculation.",
            "sentiment": "missing"
        }

    trend_score = float(trend_score)

    emas = []
    if not _is_invalid(ema20): emas.append(f"EMA20: {float(ema20):.2f}")
    emas.append(f"EMA50: {float(ema50):.2f}")
    if not _is_invalid(ema200): emas.append(f"EMA200: {float(ema200):.2f}")
    value_str = f"Close: {float(close_val):.2f} (" + ", ".join(emas) + ")"

    if trend_score >= 15.0:
        sentiment = "positive"
        interpretation = "Price is trending above key short-term and medium-term moving averages."
    elif trend_score <= 2.0:
        sentiment = "negative"
        interpretation = "Price is trending below key moving averages, indicating a downtrend."
    else:
        sentiment = "neutral"
        interpretation = "Price is showing mixed alignment with moving averages."

    return {
        "category": "Technical",
        "metric": "Trend",
        "value": value_str,
        "interpretation": interpretation,
        "sentiment": sentiment
    }


def explain_volume(latest_row: pd.Series) -> Dict[str, Any]:
    volume_score = latest_row.get("volume_score")

    if _is_invalid(volume_score):
        return {
            "category": "Technical",
            "metric": "Volume",
            "value": "Unavailable",
            "interpretation": "Insufficient volume data for calculation.",
            "sentiment": "missing"
        }

    volume_score = float(volume_score)
    if volume_score >= 20.0:
        val_str = "Ratio >= 2.0x"
    elif volume_score >= 17.0:
        val_str = "1.5x <= Ratio < 2.0x"
    elif volume_score >= 14.0:
        val_str = "1.2x <= Ratio < 1.5x"
    elif volume_score >= 10.0:
        val_str = "1.0x <= Ratio < 1.2x"
    elif volume_score >= 7.0:
        val_str = "0.8x <= Ratio < 1.0x"
    elif volume_score >= 3.0:
        val_str = "0.5x <= Ratio < 0.8x"
    else:
        val_str = "Ratio < 0.5x"

    if volume_score >= 14.0:
        sentiment = "positive"
        interpretation = "Recent trading volume is significantly higher than the 20-day average."
    elif volume_score <= 3.0:
        sentiment = "negative"
        interpretation = "Recent trading volume is significantly lower than the 20-day average."
    else:
        sentiment = "neutral"
        interpretation = "Trading volume is around the 20-day average."

    return {
        "category": "Technical",
        "metric": "Volume",
        "value": val_str,
        "interpretation": interpretation,
        "sentiment": sentiment
    }


def explain_technical_factors(indicators_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Given the technical indicators dataframe output from the Technical Engine,
    extract and interpret the latest factors.
    """
    if indicators_df is None or indicators_df.empty:
        return []

    latest_row = indicators_df.iloc[-1]

    factors = [
        explain_rsi(latest_row),
        explain_macd(latest_row),
        explain_trend(latest_row),
        explain_volume(latest_row)
    ]

    return factors
