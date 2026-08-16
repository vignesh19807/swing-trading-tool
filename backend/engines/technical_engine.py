"""
Technical Engine
================

Provides technical analysis indicators for stock market data.

This module contains indicator calculation functions for technical analysis.
Currently implements:
- Relative Strength Index (RSI)
- Exponential Moving Average (EMA)
- Moving Average Convergence Divergence (MACD)
- Average True Range (ATR)
- Support and Resistance Zone Detection
- Technical Score Engine v1 (0 - 100)
- Standardized Technical Analysis Pipeline (run_technical_pipeline)

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


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA) for a price Series.

    EMA applies more weight to recent prices using the smoothing multiplier:
    alpha = 2 / (period + 1)

    Standard Formula:
    -----------------
    EMA_today = Price_today * alpha + EMA_previous * (1 - alpha)

    Implemented using pandas EWM:
    prices.ewm(span=period, adjust=False).mean()

    Parameters
    ----------
    prices : pd.Series
        Pandas Series containing stock closing prices (numeric).
    period : int
        The lookback period for EMA calculation (e.g. 20, 50, 200). Must be an integer >= 1.

    Returns
    -------
    pd.Series
        Pandas Series containing numeric EMA values, preserving the exact index
        of the input `prices` Series.

    Edge Cases & Behavior:
    ----------------------
    - Input Validation: Raises TypeError if `prices` is not a pd.Series or `period`
      is not an int (bool is excluded). Raises ValueError if `period` < 1.
    - Insufficient Data: If len(prices) < period, returns a Series filled with NaN
      matching the input index (project convention).
    - Non-Mutation: The original `prices` Series is left unmodified.
    - Missing / NaN Values: Calculated directly via pandas EWM without silent
      forward-filling or data fabrication.
    """
    if not isinstance(prices, pd.Series):
        raise TypeError("Input 'prices' must be a pandas Series.")

    if isinstance(period, bool) or not isinstance(period, int):
        raise TypeError("Parameter 'period' must be an integer.")

    if period < 1:
        raise ValueError("Parameter 'period' must be a positive integer >= 1.")

    # Preserve input index and prevent side-effects on original input
    prices_clean = prices.copy()

    # Handle insufficient historical data convention
    if len(prices_clean) < period:
        return pd.Series(np.nan, index=prices.index, dtype=float, name=f"EMA_{period}")

    # Calculate EMA using pandas EWM span
    ema = prices_clean.ewm(span=period, adjust=False).mean()
    ema.name = f"EMA_{period}"

    return ema


def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    Calculate the Moving Average Convergence Divergence (MACD) for a price Series.

    MACD is a trend-following momentum indicator that shows the relationship
    between two exponential moving averages (EMAs) of a security's price.

    Standard Parameters:
    --------------------
    - Fast Period: 12
    - Slow Period: 26
    - Signal Period: 9

    Formula:
    --------
    1. MACD Line   = EMA(prices, fast_period) - EMA(prices, slow_period)
    2. Signal Line = EMA(MACD Line, signal_period)
    3. Histogram   = MACD Line - Signal Line

    Parameters
    ----------
    prices : pd.Series
        Pandas Series containing stock closing prices (numeric).
    fast_period : int, default 12
        Lookback period for the fast EMA. Must be >= 1.
    slow_period : int, default 26
        Lookback period for the slow EMA. Must be > fast_period.
    signal_period : int, default 9
        Lookback period for the signal line EMA. Must be >= 1.

    Returns
    -------
    pd.DataFrame
        Pandas DataFrame containing columns ['macd', 'signal', 'histogram'],
        preserving the exact index of the input `prices` Series.

    Edge Cases & Behavior:
    ----------------------
    - Input Validation: Raises TypeError if `prices` is not a pd.Series or any period
      is not an integer (booleans excluded). Raises ValueError if fast_period < 1,
      signal_period < 1, or slow_period <= fast_period.
    - Insufficient Data: If len(prices) < slow_period, returns a DataFrame filled with NaN
      matching the input index and expected columns.
    - Non-Mutation: The original `prices` Series is left unmodified.
    - Missing / NaN Values: Handled consistently with existing EMA engine without silent
      forward-filling or data fabrication.
    """
    if not isinstance(prices, pd.Series):
        raise TypeError("Input 'prices' must be a pandas Series.")

    for p_name, p_val in [("fast_period", fast_period), ("slow_period", slow_period), ("signal_period", signal_period)]:
        if isinstance(p_val, bool) or not isinstance(p_val, int):
            raise TypeError(f"Parameter '{p_name}' must be an integer.")

    if fast_period < 1 or signal_period < 1:
        raise ValueError("Parameters 'fast_period' and 'signal_period' must be >= 1.")

    if slow_period <= fast_period:
        raise ValueError("Parameter 'slow_period' must be strictly greater than 'fast_period'.")

    prices_clean = prices.copy()

    cols = ["macd", "signal", "histogram"]

    # Handle insufficient historical data convention
    if len(prices_clean) < slow_period:
        return pd.DataFrame(np.nan, index=prices.index, columns=cols)

    # Calculate component EMAs by reusing calculate_ema()
    fast_ema = calculate_ema(prices_clean, period=fast_period)
    slow_ema = calculate_ema(prices_clean, period=slow_period)

    # MACD Line = Fast EMA - Slow EMA
    macd_line = fast_ema - slow_ema

    # Signal Line = EMA(MACD Line, signal_period) reusing calculate_ema()
    signal_line = calculate_ema(macd_line, period=signal_period)

    # Histogram = MACD Line - Signal Line
    histogram = macd_line - signal_line

    result_df = pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }, index=prices.index)

    return result_df


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate the Average True Range (ATR) volatility indicator for a price Series.

    ATR measures market volatility by decomposing the entire range of an asset
    price for that period. It measures price volatility only and does not determine
    market direction.

    Formula:
    --------
    1. True Range (TR) = max(
           High - Low,
           abs(High - Previous Close),
           abs(Low - Previous Close)
       )
    2. ATR = Wilder's EWM of TR over `period`:
       tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    Parameters
    ----------
    high : pd.Series
        Pandas Series containing stock high prices (numeric).
    low : pd.Series
        Pandas Series containing stock low prices (numeric).
    close : pd.Series
        Pandas Series containing stock closing prices (numeric).
    period : int, default 14
        Lookback period for ATR calculation. Must be an integer >= 1.

    Returns
    -------
    pd.Series
        Pandas Series containing numeric ATR values, preserving the exact index
        of the input Series.

    Edge Cases & Behavior:
    ----------------------
    - Input Validation: Raises TypeError if `high`, `low`, or `close` is not a pd.Series
      or `period` is not an int (bool is excluded). Raises ValueError if indexes do not match
      or `period` < 1.
    - Insufficient Data: If len(close) < period + 1, returns a Series filled with NaN
      matching the input index.
    - Non-Mutation: The original input Series are left unmodified.
    - Missing / NaN Values: Handled consistently without silent forward-filling or data fabrication.
    """
    if not isinstance(high, pd.Series):
        raise TypeError("Input 'high' must be a pandas Series.")
    if not isinstance(low, pd.Series):
        raise TypeError("Input 'low' must be a pandas Series.")
    if not isinstance(close, pd.Series):
        raise TypeError("Input 'close' must be a pandas Series.")

    if not high.index.equals(low.index) or not high.index.equals(close.index):
        raise ValueError("Input Series ('high', 'low', 'close') must have identical indexes.")

    if isinstance(period, bool) or not isinstance(period, int):
        raise TypeError("Parameter 'period' must be an integer.")

    if period < 1:
        raise ValueError("Parameter 'period' must be a positive integer >= 1.")

    high_clean = high.copy()
    low_clean = low.copy()
    close_clean = close.copy()

    # Handle insufficient historical data convention
    if len(close_clean) < period + 1:
        return pd.Series(np.nan, index=close.index, dtype=float, name=f"ATR_{period}")

    # Calculate previous close
    prev_close = close_clean.shift(1)

    # True Range components
    tr1 = high_clean - low_clean
    tr2 = (high_clean - prev_close).abs()
    tr3 = (low_clean - prev_close).abs()

    # True Range = max(tr1, tr2, tr3)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's EWM smoothing for ATR
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    atr.name = f"ATR_{period}"

    return atr


def calculate_support_resistance(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    pivot_window: int = 3,
    zone_tolerance: float = 0.01
) -> pd.DataFrame:
    """
    Detect deterministic Support and Resistance price zones from historical market data.

    A Swing High (resistance candidate) occurs when a candle's high is greater than the highs
    of the preceding `pivot_window` candles AND greater than or equal to the highs of the
    following `pivot_window` candles.

    A Swing Low (support candidate) occurs when a candle's low is lower than the lows
    of the preceding `pivot_window` candles AND lower than or equal to the lows of the
    following `pivot_window` candles.

    Candidates of the SAME type are grouped into zones when their levels are within
    `zone_tolerance * level` (default 1%). Support and Resistance levels are never merged.

    Parameters
    ----------
    high : pd.Series
        Pandas Series containing stock high prices (numeric).
    low : pd.Series
        Pandas Series containing stock low prices (numeric).
    close : pd.Series
        Pandas Series containing stock closing prices (numeric).
    pivot_window : int, default 3
        Number of candles required on each side of a swing point. Must be an integer >= 1.
    zone_tolerance : float, default 0.01
        Percentage tolerance for clustering nearby swing points into a single zone. Must be > 0.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['level', 'zone_low', 'zone_high', 'type', 'touches', 'strength'],
        sorted by ['type', 'level'] ascending with a clean reset index.
    """
    if not isinstance(high, pd.Series):
        raise TypeError("Input 'high' must be a pandas Series.")
    if not isinstance(low, pd.Series):
        raise TypeError("Input 'low' must be a pandas Series.")
    if not isinstance(close, pd.Series):
        raise TypeError("Input 'close' must be a pandas Series.")

    if not high.index.equals(low.index) or not high.index.equals(close.index):
        raise ValueError("Input Series ('high', 'low', 'close') must have identical indexes.")

    if isinstance(pivot_window, bool) or not isinstance(pivot_window, int):
        raise TypeError("Parameter 'pivot_window' must be an integer.")
    if pivot_window < 1:
        raise ValueError("Parameter 'pivot_window' must be a positive integer >= 1.")

    if isinstance(zone_tolerance, bool) or not isinstance(zone_tolerance, (int, float)):
        raise TypeError("Parameter 'zone_tolerance' must be a numeric float or int.")
    if zone_tolerance <= 0:
        raise ValueError("Parameter 'zone_tolerance' must be strictly positive > 0.")

    cols = ["level", "zone_low", "zone_high", "type", "touches", "strength"]

    high_clean = high.copy()
    low_clean = low.copy()
    close_clean = close.copy()

    n = len(close_clean)
    if n < 2 * pivot_window + 1:
        empty_df = pd.DataFrame(columns=cols)
        empty_df["touches"] = empty_df["touches"].astype(int)
        empty_df["strength"] = empty_df["strength"].astype(float)
        empty_df["level"] = empty_df["level"].astype(float)
        empty_df["zone_low"] = empty_df["zone_low"].astype(float)
        empty_df["zone_high"] = empty_df["zone_high"].astype(float)
        empty_df["type"] = empty_df["type"].astype(str)
        return empty_df

    high_vals = high_clean.values
    low_vals = low_clean.values

    resistance_candidates = []
    support_candidates = []

    for i in range(pivot_window, n - pivot_window):
        left_h = high_vals[i - pivot_window:i]
        right_h = high_vals[i + 1:i + 1 + pivot_window]
        curr_h = high_vals[i]

        left_l = low_vals[i - pivot_window:i]
        right_l = low_vals[i + 1:i + 1 + pivot_window]
        curr_l = low_vals[i]

        if np.isnan(curr_h) or np.isnan(left_h).any() or np.isnan(right_h).any():
            is_swing_high = False
        else:
            is_swing_high = (curr_h > left_h.max()) and (curr_h >= right_h.max())

        if np.isnan(curr_l) or np.isnan(left_l).any() or np.isnan(right_l).any():
            is_swing_low = False
        else:
            is_swing_low = (curr_l < left_l.min()) and (curr_l <= right_l.min())

        if is_swing_high:
            resistance_candidates.append(float(curr_h))

        if is_swing_low:
            support_candidates.append(float(curr_l))

    def cluster_candidates(candidates, zone_type):
        if not candidates:
            return []

        sorted_cand = sorted(candidates)
        clusters = []

        current_cluster = [sorted_cand[0]]

        for price in sorted_cand[1:]:
            cluster_base = current_cluster[0]
            if abs(price - cluster_base) <= cluster_base * zone_tolerance:
                current_cluster.append(price)
            else:
                clusters.append(current_cluster)
                current_cluster = [price]

        if current_cluster:
            clusters.append(current_cluster)

        rows = []
        for cl in clusters:
            z_low = float(min(cl))
            z_high = float(max(cl))
            z_level = float(np.mean(cl))
            touches = len(cl)
            strength = float(touches)

            rows.append({
                "level": z_level,
                "zone_low": z_low,
                "zone_high": z_high,
                "type": zone_type,
                "touches": touches,
                "strength": strength
            })

        return rows

    res_rows = cluster_candidates(resistance_candidates, "resistance")
    sup_rows = cluster_candidates(support_candidates, "support")

    all_rows = sup_rows + res_rows

    if not all_rows:
        empty_df = pd.DataFrame(columns=cols)
        empty_df["touches"] = empty_df["touches"].astype(int)
        empty_df["strength"] = empty_df["strength"].astype(float)
        empty_df["level"] = empty_df["level"].astype(float)
        empty_df["zone_low"] = empty_df["zone_low"].astype(float)
        empty_df["zone_high"] = empty_df["zone_high"].astype(float)
        empty_df["type"] = empty_df["type"].astype(str)
        return empty_df

    result_df = pd.DataFrame(all_rows, columns=cols)
    result_df = result_df.sort_values(by=["type", "level"]).reset_index(drop=True)

    return result_df


def calculate_technical_score(
    close: pd.Series,
    volume: pd.Series,
    rsi: pd.Series,
    macd: pd.Series,
    signal: pd.Series,
    histogram: pd.Series,
    ema20: pd.Series,
    ema50: pd.Series,
    ema200: pd.Series
) -> pd.DataFrame:
    """
    Calculate the deterministic composite Technical Score (0 - 100) for stock data.

    Sub-Score Components:
    ---------------------
    1. RSI Score (Max 30):
       - RSI < 30        -> 10
       - 30 <= RSI < 40  -> 18
       - 40 <= RSI < 50  -> 24
       - 50 <= RSI < 60  -> 30
       - 60 <= RSI < 70  -> 27
       - 70 <= RSI < 80  -> 20
       - RSI >= 80       -> 10

    2. MACD Score (Max 30):
       - Approx equality: abs(macd - signal) <= max(0.01 * abs(signal), 0.01)
       - Priority sequence:
         - Cond 8: MACD < Signal AND MACD < 0 AND Histogram < 0 -> 0
         - Cond 1: MACD > Signal AND MACD > 0 AND Histogram > 0 -> 30
         - Cond 2: MACD > Signal AND MACD > 0                   -> 27
         - Cond 3: MACD > Signal AND Histogram > 0              -> 24
         - Cond 4: MACD > Signal                                -> 20
         - Cond 5: MACD approx equal Signal                      -> 15
         - Cond 6: MACD < Signal AND Histogram > 0              -> 12
         - Cond 7: MACD < Signal                                -> 8

    3. Trend Score (Max 20):
       - Priority sequence:
         - Cond 8: EMA20 < EMA50 < EMA200 AND Close < EMA20    -> 0
         - Cond 1: EMA20 > EMA50 > EMA200 AND Close > EMA20    -> 20
         - Cond 2: EMA20 > EMA50 > EMA200                      -> 18
         - Cond 3: EMA20 > EMA50 AND Close > EMA20              -> 15
         - Cond 4: EMA20 > EMA50                                -> 12
         - Cond 5: Close > EMA50                                -> 8
         - Cond 7: EMA20 < EMA50 AND Close < EMA20              -> 2
         - Cond 6 (Neutral / Mixed):                            -> 5

    4. Volume Score (Max 20):
       - avg_volume_20 = volume.rolling(20, min_periods=20).mean()
       - ratio = volume / avg_volume_20
       - ratio >= 2.0         -> 20
       - 1.5 <= ratio < 2.0   -> 17
       - 1.2 <= ratio < 1.5   -> 14
       - 1.0 <= ratio < 1.2   -> 10
       - 0.8 <= ratio < 1.0   -> 7
       - 0.5 <= ratio < 0.8   -> 3
       - ratio < 0.5          -> 0

    5. Composite Technical Score:
       - rsi_score + macd_score + trend_score + volume_score
       - Clipped to [0, 100]

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['rsi_score', 'macd_score', 'trend_score', 'volume_score', 'technical_score'],
        preserving the exact index of the input Series.
    """
    inputs = [
        ("close", close),
        ("volume", volume),
        ("rsi", rsi),
        ("macd", macd),
        ("signal", signal),
        ("histogram", histogram),
        ("ema20", ema20),
        ("ema50", ema50),
        ("ema200", ema200)
    ]

    for name, s in inputs:
        if not isinstance(s, pd.Series):
            raise TypeError(f"Input '{name}' must be a pandas Series.")

    first_index = close.index
    for name, s in inputs:
        if not s.index.equals(first_index):
            raise ValueError(f"Input Series '{name}' index does not match 'close' index.")

    # 1. RSI Score calculation
    rsi_score = pd.Series(np.nan, index=first_index, dtype=float)
    rsi_val = rsi.copy()
    valid_rsi = rsi_val.notna()

    c_rsi_lt30 = valid_rsi & (rsi_val < 30.0)
    c_rsi_30_40 = valid_rsi & (rsi_val >= 30.0) & (rsi_val < 40.0)
    c_rsi_40_50 = valid_rsi & (rsi_val >= 40.0) & (rsi_val < 50.0)
    c_rsi_50_60 = valid_rsi & (rsi_val >= 50.0) & (rsi_val < 60.0)
    c_rsi_60_70 = valid_rsi & (rsi_val >= 60.0) & (rsi_val < 70.0)
    c_rsi_70_80 = valid_rsi & (rsi_val >= 70.0) & (rsi_val < 80.0)
    c_rsi_gte80 = valid_rsi & (rsi_val >= 80.0)

    rsi_score[c_rsi_lt30] = 10.0
    rsi_score[c_rsi_30_40] = 18.0
    rsi_score[c_rsi_40_50] = 24.0
    rsi_score[c_rsi_50_60] = 30.0
    rsi_score[c_rsi_60_70] = 27.0
    rsi_score[c_rsi_70_80] = 20.0
    rsi_score[c_rsi_gte80] = 10.0

    # 2. MACD Score calculation
    macd_score = pd.Series(np.nan, index=first_index, dtype=float)
    valid_macd = macd.notna() & signal.notna() & histogram.notna()

    # Approx equality
    macd_diff = (macd - signal).abs()
    approx_tol = np.maximum(0.01 * signal.abs(), 0.01)
    is_approx_equal = valid_macd & (macd_diff <= approx_tol)

    # Priority conditions for MACD
    c_m8 = valid_macd & (macd < signal) & (macd < 0.0) & (histogram < 0.0)
    c_m1 = valid_macd & (macd > signal) & (macd > 0.0) & (histogram > 0.0)
    c_m2 = valid_macd & (macd > signal) & (macd > 0.0)
    c_m3 = valid_macd & (macd > signal) & (histogram > 0.0)
    c_m4 = valid_macd & (macd > signal)
    c_m5 = is_approx_equal
    c_m6 = valid_macd & (macd < signal) & (histogram > 0.0)
    c_m7 = valid_macd & (macd < signal)

    # Apply in reverse priority order (lowest priority first, highest priority last)
    macd_score[c_m7] = 8.0
    macd_score[c_m8] = 0.0
    macd_score[c_m6] = 12.0
    macd_score[c_m5] = 15.0
    macd_score[c_m4] = 20.0
    macd_score[c_m3] = 24.0
    macd_score[c_m2] = 27.0
    macd_score[c_m1] = 30.0

    # 3. Trend Score calculation
    trend_score = pd.Series(np.nan, index=first_index, dtype=float)
    valid_trend = close.notna() & ema20.notna() & ema50.notna() & ema200.notna()

    c_t8 = valid_trend & (ema20 < ema50) & (ema50 < ema200) & (close < ema20)
    c_t1 = valid_trend & (ema20 > ema50) & (ema50 > ema200) & (close > ema20)
    c_t2 = valid_trend & (ema20 > ema50) & (ema50 > ema200)
    c_t3 = valid_trend & (ema20 > ema50) & (close > ema20)
    c_t4 = valid_trend & (ema20 > ema50)
    c_t5 = valid_trend & (close > ema50)
    c_t7 = valid_trend & (ema20 < ema50) & (close < ema20)

    # Default neutral for all valid rows is 5.0
    trend_score[valid_trend] = 5.0
    trend_score[c_t7] = 2.0
    trend_score[c_t5] = 8.0
    trend_score[c_t4] = 12.0
    trend_score[c_t3] = 15.0
    trend_score[c_t2] = 18.0
    trend_score[c_t1] = 20.0
    trend_score[c_t8] = 0.0

    # 4. Volume Score calculation
    volume_score = pd.Series(np.nan, index=first_index, dtype=float)
    avg_vol_20 = volume.rolling(window=20, min_periods=20).mean()
    vol_ratio = volume / avg_vol_20
    valid_vol = vol_ratio.notna()

    c_v_gte20 = valid_vol & (vol_ratio >= 2.0)
    c_v_15_20 = valid_vol & (vol_ratio >= 1.5) & (vol_ratio < 2.0)
    c_v_12_15 = valid_vol & (vol_ratio >= 1.2) & (vol_ratio < 1.5)
    c_v_10_12 = valid_vol & (vol_ratio >= 1.0) & (vol_ratio < 1.2)
    c_v_08_10 = valid_vol & (vol_ratio >= 0.8) & (vol_ratio < 1.0)
    c_v_05_08 = valid_vol & (vol_ratio >= 0.5) & (vol_ratio < 0.8)
    c_v_lt05  = valid_vol & (vol_ratio < 0.5)

    volume_score[c_v_gte20] = 20.0
    volume_score[c_v_15_20] = 17.0
    volume_score[c_v_12_15] = 14.0
    volume_score[c_v_10_12] = 10.0
    volume_score[c_v_08_10] = 7.0
    volume_score[c_v_05_08] = 3.0
    volume_score[c_v_lt05]  = 0.0

    # 5. Composite Technical Score
    all_valid = rsi_score.notna() & macd_score.notna() & trend_score.notna() & volume_score.notna()
    technical_score = pd.Series(np.nan, index=first_index, dtype=float)

    raw_sum = rsi_score[all_valid] + macd_score[all_valid] + trend_score[all_valid] + volume_score[all_valid]
    technical_score[all_valid] = raw_sum.clip(0.0, 100.0)

    result_df = pd.DataFrame({
        "rsi_score": rsi_score,
        "macd_score": macd_score,
        "trend_score": trend_score,
        "volume_score": volume_score,
        "technical_score": technical_score
    }, index=first_index)

    return result_df


def run_technical_pipeline(df: pd.DataFrame) -> dict:
    """
    Standardized technical-analysis pipeline executing all Phase 1 indicators
    and Technical Score calculation for a stock DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns ['high', 'low', 'close', 'volume'] (and optional 'date', 'open').

    Returns
    -------
    dict
        Dictionary containing:
        - 'indicators': pd.DataFrame with close, volume, rsi, ema20, ema50, ema200,
                        macd, signal, histogram, atr14, rsi_score, macd_score,
                        trend_score, volume_score, technical_score
        - 'support_resistance': pd.DataFrame with support/resistance zones
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")
    required_cols = {"high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        missing = sorted(list(required_cols - set(df.columns)))
        raise ValueError(f"Input DataFrame is missing required columns: {missing}")

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi = calculate_rsi(close, period=14)
    ema20 = calculate_ema(close, period=20)
    ema50 = calculate_ema(close, period=50)
    ema200 = calculate_ema(close, period=200)

    macd_df = calculate_macd(close, fast_period=12, slow_period=26, signal_period=9)
    atr14 = calculate_atr(high, low, close, period=14)
    sr_df = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)

    scores_df = calculate_technical_score(
        close=close,
        volume=volume,
        rsi=rsi,
        macd=macd_df["macd"],
        signal=macd_df["signal"],
        histogram=macd_df["histogram"],
        ema20=ema20,
        ema50=ema50,
        ema200=ema200
    )

    indicators_df = pd.DataFrame({
        "close": close,
        "volume": volume,
        "rsi": rsi,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "macd": macd_df["macd"],
        "signal": macd_df["signal"],
        "histogram": macd_df["histogram"],
        "atr14": atr14,
        "rsi_score": scores_df["rsi_score"],
        "macd_score": scores_df["macd_score"],
        "trend_score": scores_df["trend_score"],
        "volume_score": scores_df["volume_score"],
        "technical_score": scores_df["technical_score"],
    }, index=df.index)

    return {
        "indicators": indicators_df,
        "support_resistance": sr_df
    }






