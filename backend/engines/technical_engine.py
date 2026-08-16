"""
Technical Engine
================

Provides technical analysis indicators for stock market data.

This module contains indicator calculation functions for technical analysis.
Currently implements:
- Relative Strength Index (RSI)

Author: Logic Engineer
"""

import numpy as np
import pandas as pd


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI) for a price Series using
    Wilder's exponential smoothing method.

    RSI is a momentum oscillator that measures the speed and change of price
    movements on a scale from 0 to 100.

    Standard Formula (Wilder's RSI):
    --------------------------------
    1. delta = price[t] - price[t-1]
    2. gain = max(delta, 0), loss = max(-delta, 0)
    3. avg_gain = Wilder's Exponential Moving Average of gains over `period`
       avg_loss = Wilder's Exponential Moving Average of losses over `period`
    4. RS = avg_gain / avg_loss
    5. RSI = 100 - (100 / (1 + RS))

    Parameters
    ----------
    prices : pd.Series
        Pandas Series containing stock closing prices (numeric).
    period : int, default 14
        The lookback period for RSI calculation. Must be an integer >= 1.

    Returns
    -------
    pd.Series
        Pandas Series containing numeric RSI values (range 0 to 100),
        preserving the exact index of the input `prices` Series.

    Edge Cases & Behavior:
    ----------------------
    - Input Validation: Raises TypeError if `prices` is not a pd.Series, or
      ValueError if `period` < 1.
    - Insufficient Data: If len(prices) < period + 1, returns a Series filled
      with NaN matching the input index.
    - Zero Loss (avg_loss == 0, avg_gain > 0): Returns RSI = 100.0.
    - Zero Gain (avg_gain == 0, avg_loss > 0): Returns RSI = 0.0.
    - Flat Prices (avg_gain == 0, avg_loss == 0): Returns neutral RSI = 50.0.
    - Missing / NaN Values: Missing prices produce NaN in price changes and
      consequently NaN in RSI. No silent forward-fill or data imputation is performed.
    - Non-Mutation: The original `prices` Series is left unmodified.
    """
    if not isinstance(prices, pd.Series):
        raise TypeError("Input 'prices' must be a pandas Series.")

    if not isinstance(period, int) or period < 1:
        raise ValueError("Parameter 'period' must be a positive integer >= 1.")

    # Preserve input index and prevent side-effects on original input
    prices_clean = prices.copy()

    # Handle insufficient historical data
    if len(prices_clean) < period + 1:
        return pd.Series(np.nan, index=prices.index, dtype=float, name="RSI")

    # 1. Price delta
    delta = prices_clean.diff()

    # 2. Separate gains and losses
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # 3. Wilder's Exponential Moving Average (alpha = 1 / period)
    # min_periods=period ensures NaNs for the warm-up period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # 4 & 5. Compute RSI with explicit edge-case handling
    rsi = pd.Series(np.nan, index=prices.index, dtype=float, name="RSI")

    # Masks for edge case resolution
    both_zero = (avg_gain == 0.0) & (avg_loss == 0.0)
    loss_zero = (avg_loss == 0.0) & (avg_gain > 0.0)
    gain_zero = (avg_gain == 0.0) & (avg_loss > 0.0)
    normal_case = (avg_loss > 0.0) & (avg_gain > 0.0)

    # Apply edge cases safely
    rsi[both_zero] = 50.0
    rsi[loss_zero] = 100.0
    rsi[gain_zero] = 0.0

    # Normal calculation (no division by zero)
    rs = avg_gain[normal_case] / avg_loss[normal_case]
    rsi[normal_case] = 100.0 - (100.0 / (1.0 + rs))

    return rsi
