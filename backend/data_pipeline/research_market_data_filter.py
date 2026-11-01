"""
Research Market Data Filter & Anomaly Detection Layer
=====================================================

Provides non-destructive filtering and anomaly detection for daily OHLCV market data.
Preserves production database records while allowing research backtests and indicator
calculations to mask confirmed synthetic holiday carry-forward bars or isolate suspicious
price discontinuities (e.g. unadjusted corporate actions).
"""

from typing import Dict, List, Optional, Tuple, Set
import pandas as pd
import numpy as np


# Confirmed NSE Holidays where synthetic flat carry-forward bars were recorded
KNOWN_EXCHANGE_HOLIDAYS: Set[str] = {
    "2025-03-18",  # Holi (51 stocks recorded O=H=L=C, Volume=0)
    "2026-01-15",  # Makar Sankranti / Municipal Election (52 stocks recorded O=H=L=C, Volume=0)
}

# Known/Verified Corporate Actions vs Unresolved Anomalies
KNOWN_CORPORATE_ACTIONS: Dict[str, Set[str]] = {
    "TMPV": {"2025-10-14"},  # Verified demerger
}

UNRESOLVED_ANOMALIES: Dict[str, Set[str]] = {
    "TRENT": {"2026-01-01"},  # Suspected 3:2 split/bonus, unadjusted in data
}


def detect_market_data_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scans a market price DataFrame for:
    1. SYNTHETIC_HOLIDAY_BAR: O=H=L=C, Volume=0 on known exchange holiday
    2. STALE_FLAT_BAR: O=H=L=C, Volume=0 on non-holiday trading session
    3. INVERTED_OHLC: High < Low, or Open/Close outside [Low, High]
    4. NON_POSITIVE_PRICE: Price <= 0
    5. LARGE_DISCONTINUITY: |Daily Return| > 25% (indicative of unadjusted corporate action)

    Returns a copy with attached boolean flags and 'anomaly_classification'.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    # 1. Flat bar condition
    is_flat = (
        (out["open"] == out["high"]) &
        (out["high"] == out["low"]) &
        (out["low"] == out["close"]) &
        (out["volume"] == 0)
    )

    # 2. Known holiday (normalize to YYYY-MM-DD string series for robust comparison)
    date_strs = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    is_known_holiday = date_strs.isin(KNOWN_EXCHANGE_HOLIDAYS)

    # 3. Inverted OHLC
    is_inverted = (
        (out["high"] < out["low"]) |
        (out["open"] > out["high"]) |
        (out["open"] < out["low"]) |
        (out["close"] > out["high"]) |
        (out["close"] < out["low"])
    )

    # 4. Non-positive
    is_non_positive = (
        (out["open"] <= 0) |
        (out["high"] <= 0) |
        (out["low"] <= 0) |
        (out["close"] <= 0)
    )

    # 5. Price Discontinuity
    if "close" in out.columns:
        if "symbol" in out.columns:
            prev_close = out.groupby("symbol")["close"].shift(1)
        else:
            prev_close = out["close"].shift(1)
        ret = (out["close"] - prev_close) / prev_close
        is_large_move = ret.abs() > 0.25
    else:
        is_large_move = pd.Series(False, index=out.index)

    out["is_synthetic_holiday"] = is_flat & is_known_holiday
    out["is_stale_flat_bar"] = is_flat & (~is_known_holiday)
    out["is_inverted_ohlc"] = is_inverted
    out["is_non_positive"] = is_non_positive
    out["is_large_discontinuity"] = is_large_move.fillna(False)

    conditions = [
        out["is_inverted_ohlc"],
        out["is_non_positive"],
        out["is_synthetic_holiday"],
        out["is_stale_flat_bar"],
        out["is_large_discontinuity"],
    ]
    choices = [
        "INVERTED_OHLC",
        "NON_POSITIVE_PRICE",
        "SYNTHETIC_HOLIDAY_BAR",
        "STALE_FLAT_BAR",
        "LARGE_PRICE_DISCONTINUITY",
    ]
    out["anomaly_classification"] = np.select(conditions, choices, default="NORMAL_SESSION")
    return out


def filter_research_market_data(
    df: pd.DataFrame,
    exclude_synthetic_holidays: bool = True,
    exclude_stale_flat_bars: bool = False,
    exclude_anomalies: bool = True,
    quarantine_unresolved_anomalies: bool = False,
) -> pd.DataFrame:
    """
    Returns a cleaned view of market data for research and backtesting.
    Does NOT alter the underlying database.

    Parameters
    ----------
    quarantine_unresolved_anomalies : bool, default False
        When True, excludes observations corresponding to confirmed unresolved price
        discontinuities (e.g. TRENT on 2026-01-01) so research simulations cannot
        be silently distorted by unadjusted artificial drops.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    annotated = detect_market_data_anomalies(df)
    mask = pd.Series(True, index=annotated.index)

    if exclude_synthetic_holidays:
        mask = mask & (~annotated["is_synthetic_holiday"])

    if exclude_stale_flat_bars:
        mask = mask & (~annotated["is_stale_flat_bar"])

    if exclude_anomalies:
        mask = mask & (~annotated["is_inverted_ohlc"]) & (~annotated["is_non_positive"])

    if quarantine_unresolved_anomalies:
        date_strs = pd.to_datetime(annotated["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        if "symbol" in annotated.columns:
            is_unresolved = pd.Series(False, index=annotated.index)
            for sym, dates in UNRESOLVED_ANOMALIES.items():
                match = (annotated["symbol"] == sym) & (date_strs.isin(dates))
                is_unresolved = is_unresolved | match
            mask = mask & (~is_unresolved)

    return annotated[mask].copy()


def validate_research_dataset_safety(
    df: pd.DataFrame,
    symbol: Optional[str] = None,
    allow_unresolved_anomalies: bool = False,
) -> Dict[str, Any]:
    """
    Explicit safeguard check: Inspects whether a research dataset contains
    unresolved price discontinuities or unmasked synthetic holiday bars.
    Raises ValueError or returns an invalid diagnostic report if an unresolved
    anomaly threatens research integrity.
    """
    if df is None or df.empty:
        return {"status": "EMPTY", "is_safe": True, "anomalies_detected": []}

    annotated = detect_market_data_anomalies(df)
    anomalies = []

    # Check for holiday flat bars
    holidays = annotated[annotated["is_synthetic_holiday"]]
    if not holidays.empty:
        anomalies.append(f"Contains {len(holidays)} unmasked synthetic holiday bars")

    # Check for large discontinuities
    disc = annotated[annotated["is_large_discontinuity"]]
    if not disc.empty:
        date_strs = pd.to_datetime(disc["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        for idx, r in disc.iterrows():
            sym = r.get("symbol", symbol or "UNKNOWN")
            d_str = date_strs.loc[idx]
            if sym in UNRESOLVED_ANOMALIES and d_str in UNRESOLVED_ANOMALIES[sym]:
                anomalies.append(f"UNRESOLVED_PRICE_ANOMALY detected in {sym} on {d_str}")
            elif sym in KNOWN_CORPORATE_ACTIONS and d_str in KNOWN_CORPORATE_ACTIONS[sym]:
                # Documented verified action
                pass
            else:
                anomalies.append(f"Unclassified price discontinuity in {sym} on {d_str}")

    is_safe = len(anomalies) == 0 or allow_unresolved_anomalies
    return {
        "status": "SAFE" if is_safe else "FAIL_UNRESOLVED_ANOMALY",
        "is_safe": is_safe,
        "anomalies_detected": anomalies,
    }
