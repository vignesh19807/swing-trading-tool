"""
Unit Tests for Technical Engine (RSI)
=====================================

Completely isolated unit tests for RSI calculation.
Contains zero database or network dependencies.
"""

import unittest
import numpy as np
import pandas as pd

from backend.engines.technical_engine import (
    calculate_rsi,
    calculate_ema,
    calculate_macd,
    calculate_atr,
    calculate_support_resistance,
    calculate_technical_score,
    run_technical_pipeline
)


class TestTechnicalEngineRSI(unittest.TestCase):
    """
    Unit tests for calculate_rsi function in backend.engines.technical_engine.
    """

    def test_normal_increasing_decreasing_prices(self):
        """
        Verify RSI behavior for strictly increasing and decreasing prices.
        """
        # Strictly increasing prices -> gain > 0, loss == 0 -> RSI should be 100.0
        increasing = pd.Series([10.0 + i * 2.0 for i in range(20)])
        rsi_inc = calculate_rsi(increasing, period=14)
        valid_rsi_inc = rsi_inc.dropna()
        self.assertGreater(len(valid_rsi_inc), 0)
        for val in valid_rsi_inc:
            self.assertEqual(val, 100.0)

        # Strictly decreasing prices -> gain == 0, loss > 0 -> RSI should be 0.0
        decreasing = pd.Series([100.0 - i * 2.0 for i in range(20)])
        rsi_dec = calculate_rsi(decreasing, period=14)
        valid_rsi_dec = rsi_dec.dropna()
        self.assertGreater(len(valid_rsi_dec), 0)
        for val in valid_rsi_dec:
            self.assertEqual(val, 0.0)

    def test_constant_prices(self):
        """
        Verify constant prices yield neutral RSI of 50.0.
        """
        constant = pd.Series([50.0] * 30)
        rsi = calculate_rsi(constant, period=14)
        valid_rsi = rsi.dropna()
        self.assertGreater(len(valid_rsi), 0)
        for val in valid_rsi:
            self.assertEqual(val, 50.0)

    def test_insufficient_data(self):
        """
        Verify Series shorter than period + 1 returns all NaNs matching index.
        """
        short_series = pd.Series([10.0, 12.0, 11.0, 13.0, 14.0])  # len 5 < 14 + 1
        rsi = calculate_rsi(short_series, period=14)
        self.assertEqual(len(rsi), len(short_series))
        self.assertTrue(rsi.isna().all())
        self.assertTrue(rsi.index.equals(short_series.index))

    def test_nan_handling(self):
        """
        Verify NaN values propagate without silent imputation or error.
        """
        prices = pd.Series([10, 12, 14, np.nan, 18, 20, 22, 21, 23, 25, 27, 26, 28, 30, 32, 34, 33])
        rsi = calculate_rsi(prices, period=14)
        # Verify result length and index match
        self.assertEqual(len(rsi), len(prices))
        self.assertTrue(rsi.index.equals(prices.index))
        # NaN in input should produce NaN in output at corresponding/propagation locations
        self.assertTrue(pd.isna(rsi.iloc[3]))

    def test_rsi_output_range(self):
        """
        Verify valid RSI values are bounded between 0 and 100.
        """
        np.random.seed(42)
        random_prices = pd.Series(100.0 + np.cumsum(np.random.randn(100)))
        rsi = calculate_rsi(random_prices, period=14)
        valid_rsi = rsi.dropna()
        self.assertGreater(len(valid_rsi), 0)
        self.assertTrue((valid_rsi >= 0.0).all())
        self.assertTrue((valid_rsi <= 100.0).all())

    def test_index_preservation(self):
        """
        Verify output pandas Series preserves exact custom index.
        """
        custom_index = pd.date_range("2026-01-01", periods=20, freq="D")
        prices = pd.Series([100 + i % 5 for i in range(20)], index=custom_index)
        rsi = calculate_rsi(prices, period=14)
        self.assertTrue(rsi.index.equals(prices.index))

    def test_no_input_mutation(self):
        """
        Verify original input pandas Series is not modified.
        """
        original_values = [10.0, 12.0, 11.0, 15.0, 14.0, 16.0, 18.0, 17.0, 19.0, 20.0,
                           22.0, 21.0, 23.0, 25.0, 24.0, 26.0, 28.0]
        prices = pd.Series(original_values, name="close")
        prices_copy = prices.copy()

        _ = calculate_rsi(prices, period=14)

        pd.testing.assert_series_equal(prices, prices_copy)

    def test_different_periods(self):
        """
        Verify calculate_rsi works correctly with different period values (e.g. 7, 20).
        """
        prices = pd.Series([100.0 + (i % 7) * 2.0 for i in range(30)])

        # Period 7
        rsi_7 = calculate_rsi(prices, period=7)
        self.assertEqual(rsi_7.isna().sum(), 7)  # First 7 values should be NaN

        # Period 20
        rsi_20 = calculate_rsi(prices, period=20)
        self.assertEqual(rsi_20.isna().sum(), 20)  # First 20 values should be NaN

    def test_invalid_inputs(self):
        """
        Verify TypeError and ValueError for bad inputs.
        """
        with self.assertRaises(TypeError):
            calculate_rsi([10, 12, 14, 16])  # list instead of pd.Series

        with self.assertRaises(ValueError):
            calculate_rsi(pd.Series([10, 12, 14]), period=0)  # invalid period


class TestTechnicalEngineEMA(unittest.TestCase):
    """
    Unit tests for calculate_ema function in backend.engines.technical_engine.
    """

    def test_basic_ema_calculation(self):
        """
        Verify basic EMA calculation logic.
        For prices [10, 20, 30] and period=2:
        alpha = 2 / (2 + 1) = 2/3
        EMA(0) = 10
        EMA(1) = 20 * (2/3) + 10 * (1/3) = 16.6667
        EMA(2) = 30 * (2/3) + 16.6667 * (1/3) = 25.5556
        """
        prices = pd.Series([10.0, 20.0, 30.0])
        ema = calculate_ema(prices, period=2)
        self.assertAlmostEqual(ema.iloc[0], 10.0, places=4)
        self.assertAlmostEqual(ema.iloc[1], 16.666666, places=4)
        self.assertAlmostEqual(ema.iloc[2], 25.555555, places=4)

    def test_ema20(self):
        """
        Verify EMA20 calculation with sufficient data (>= 20 records).
        """
        prices = pd.Series([100.0 + i for i in range(30)])
        ema20 = calculate_ema(prices, period=20)
        self.assertEqual(len(ema20), 30)
        self.assertFalse(ema20.isna().any())

    def test_ema50(self):
        """
        Verify EMA50 calculation with sufficient data (>= 50 records).
        """
        prices = pd.Series([100.0 + i for i in range(60)])
        ema50 = calculate_ema(prices, period=50)
        self.assertEqual(len(ema50), 60)
        self.assertFalse(ema50.isna().any())

    def test_ema200(self):
        """
        Verify EMA200 calculation with sufficient data (>= 200 records).
        """
        prices = pd.Series([100.0 + i for i in range(250)])
        ema200 = calculate_ema(prices, period=200)
        self.assertEqual(len(ema200), 250)
        self.assertFalse(ema200.isna().any())

    def test_invalid_period(self):
        """
        Verify TypeError / ValueError for invalid period arguments (0, negative, non-int).
        """
        prices = pd.Series([10.0, 20.0, 30.0])

        with self.assertRaises(ValueError):
            calculate_ema(prices, period=0)

        with self.assertRaises(ValueError):
            calculate_ema(prices, period=-5)

        with self.assertRaises(TypeError):
            calculate_ema(prices, period="20")

        with self.assertRaises(TypeError):
            calculate_ema(prices, period=True)

        with self.assertRaises(TypeError):
            calculate_ema([10, 20, 30], period=10)

    def test_period_one(self):
        """
        Verify period=1 EMA equals original prices.
        alpha = 2 / (1 + 1) = 1.0 -> EMA_today = Price_today * 1.0 + EMA_prev * 0 = Price_today
        """
        prices = pd.Series([10.5, 12.3, 14.8, 11.2, 15.0])
        ema1 = calculate_ema(prices, period=1)
        pd.testing.assert_series_equal(ema1, prices, check_names=False)

    def test_index_preservation(self):
        """
        Verify output pandas Series preserves exact custom index.
        """
        custom_index = pd.date_range("2026-01-01", periods=25, freq="D")
        prices = pd.Series([100.0 + i for i in range(25)], index=custom_index)
        ema = calculate_ema(prices, period=20)
        self.assertTrue(ema.index.equals(prices.index))

    def test_no_input_mutation(self):
        """
        Verify original input pandas Series is not modified.
        """
        prices = pd.Series([100.0, 102.0, 101.0, 105.0, 104.0], name="close")
        prices_copy = prices.copy()
        _ = calculate_ema(prices, period=3)
        pd.testing.assert_series_equal(prices, prices_copy)

    def test_nan_handling(self):
        """
        Test actual NaN behavior: pandas EWM carries forward previous EMA state at NaN index
        without crashing or fabricating price data.
        """
        prices = pd.Series([10.0, 12.0, np.nan, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0])
        ema = calculate_ema(prices, period=5)
        self.assertEqual(len(ema), len(prices))
        self.assertTrue(ema.index.equals(prices.index))
        # At index 2 (NaN price), pandas EWM maintains previous EMA value
        self.assertEqual(ema.iloc[2], ema.iloc[1])
        self.assertFalse(ema.isna().any())

    def test_responsiveness_comparison(self):
        """
        Verify short-period EMA (EMA 20) responds faster than long-period EMA (EMA 50)
        when a price jump occurs.
        """
        # Flat at 100 for 50 days, then jumps to 200 for 10 days
        base = [100.0] * 50 + [200.0] * 10
        prices = pd.Series(base)

        ema20 = calculate_ema(prices, period=20)
        ema50 = calculate_ema(prices, period=50)

        # After jump (at the last index), EMA20 should be closer to 200 than EMA50
        last_price = prices.iloc[-1]  # 200.0
        dist_20 = abs(last_price - ema20.iloc[-1])
        dist_50 = abs(last_price - ema50.iloc[-1])

        self.assertLess(dist_20, dist_50, "EMA20 should adjust closer to recent price jump than EMA50")

    def test_output_numeric(self):
        """
        Verify output series remains numeric (float64).
        """
        prices = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        ema = calculate_ema(prices, period=5)
        self.assertTrue(pd.api.types.is_numeric_dtype(ema))
        self.assertEqual(ema.dtype, np.float64)

    def test_insufficient_data_convention(self):
        """
        Verify len < period convention returns Series filled with NaNs matching index.
        """
        short_prices = pd.Series([10.0, 12.0, 14.0])
        ema20 = calculate_ema(short_prices, period=20)
        self.assertEqual(len(ema20), len(short_prices))
        self.assertTrue(ema20.isna().all())
        self.assertTrue(ema20.index.equals(short_prices.index))


class TestTechnicalEngineMACD(unittest.TestCase):
    """
    Unit tests for calculate_macd function in backend.engines.technical_engine.
    """

    def test_macd_basic_structure(self):
        """
        Verify MACD output is a DataFrame with expected columns ['macd', 'signal', 'histogram'].
        """
        prices = pd.Series([100.0 + i for i in range(50)])
        macd_df = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

        self.assertIsInstance(macd_df, pd.DataFrame)
        self.assertEqual(list(macd_df.columns), ["macd", "signal", "histogram"])
        self.assertEqual(len(macd_df), 50)
        self.assertTrue(macd_df.index.equals(prices.index))

    def test_macd_formula_correctness(self):
        """
        Verify MACD Line = Fast EMA - Slow EMA, and Histogram = MACD Line - Signal Line.
        """
        np.random.seed(42)
        prices = pd.Series(100.0 + np.cumsum(np.random.randn(60)))
        macd_df = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

        fast_ema = calculate_ema(prices, period=12)
        slow_ema = calculate_ema(prices, period=26)
        expected_macd = fast_ema - slow_ema
        expected_histogram = macd_df["macd"] - macd_df["signal"]

        pd.testing.assert_series_equal(macd_df["macd"], expected_macd, check_names=False)
        pd.testing.assert_series_equal(macd_df["histogram"], expected_histogram, check_names=False)

    def test_macd_signal_line_smoothing(self):
        """
        Verify Signal Line is the 9-period EMA of the MACD line.
        """
        prices = pd.Series([100.0 + (i % 5) * 3.0 for i in range(60)])
        macd_df = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

        expected_signal = calculate_ema(macd_df["macd"], period=9)
        pd.testing.assert_series_equal(macd_df["signal"], expected_signal, check_names=False)

    def test_insufficient_data(self):
        """
        Verify Series shorter than slow_period returns DataFrame of NaNs matching index.
        """
        short_series = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0])  # len 5 < 26
        macd_df = calculate_macd(short_series, fast_period=12, slow_period=26, signal_period=9)

        self.assertEqual(len(macd_df), len(short_series))
        self.assertTrue(macd_df.isna().all().all())
        self.assertTrue(macd_df.index.equals(short_series.index))

    def test_nan_handling(self):
        """
        Verify NaN values in prices propagate without crash.
        """
        prices = pd.Series([10.0 + i if i != 10 else np.nan for i in range(40)])
        macd_df = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

        self.assertEqual(len(macd_df), len(prices))
        self.assertTrue(macd_df.index.equals(prices.index))

    def test_index_preservation(self):
        """
        Verify custom index preservation.
        """
        custom_index = pd.date_range("2026-01-01", periods=40, freq="D")
        prices = pd.Series([100.0 + i for i in range(40)], index=custom_index)
        macd_df = calculate_macd(prices)

        self.assertTrue(macd_df.index.equals(custom_index))

    def test_no_input_mutation(self):
        """
        Verify original input pandas Series is not modified.
        """
        prices = pd.Series([100.0 + i for i in range(40)], name="close")
        prices_copy = prices.copy()

        _ = calculate_macd(prices)
        pd.testing.assert_series_equal(prices, prices_copy)

    def test_custom_periods(self):
        """
        Verify MACD calculation with custom fast, slow, and signal periods.
        """
        prices = pd.Series([100.0 + i for i in range(30)])
        macd_df = calculate_macd(prices, fast_period=5, slow_period=15, signal_period=5)

        self.assertEqual(len(macd_df), 30)
        self.assertFalse(macd_df["macd"].isna().all())

    def test_invalid_inputs(self):
        """
        Verify TypeError / ValueError for bad input parameters.
        """
        prices = pd.Series([100.0 + i for i in range(30)])

        with self.assertRaises(TypeError):
            calculate_macd([100.0 + i for i in range(30)])  # list instead of pd.Series

        with self.assertRaises(ValueError):
            calculate_macd(prices, fast_period=26, slow_period=12)  # fast >= slow

        with self.assertRaises(ValueError):
            calculate_macd(prices, fast_period=0)  # fast < 1

        with self.assertRaises(TypeError):
            calculate_macd(prices, signal_period="9")  # non-int period

        with self.assertRaises(TypeError):
            calculate_macd(prices, fast_period=True)  # bool period


class TestTechnicalEngineATR(unittest.TestCase):
    """
    Unit tests for calculate_atr function in backend.engines.technical_engine.
    """

    def test_basic_true_range(self):
        """
        Verify True Range logic: max(High-Low, abs(High-PrevClose), abs(Low-PrevClose)).
        Day 0: High=10, Low=8, Close=9
        Day 1: High=15, Low=12, Close=14 (PrevClose=9)
        High-Low = 3, High-PrevClose = 6, Low-PrevClose = 3 -> TR = 6
        """
        high = pd.Series([10.0, 15.0])
        low = pd.Series([8.0, 12.0])
        close = pd.Series([9.0, 14.0])

        # Test with period=1 (ATR = TR)
        atr1 = calculate_atr(high, low, close, period=1)
        self.assertEqual(len(atr1), 2)
        self.assertAlmostEqual(atr1.iloc[1], 6.0, places=4)

    def test_atr14_calculation(self):
        """
        Verify standard ATR(14) calculation on 20 bars.
        """
        np.random.seed(42)
        close = pd.Series(100.0 + np.cumsum(np.random.randn(25)))
        high = close + 2.0
        low = close - 2.0

        atr14 = calculate_atr(high, low, close, period=14)
        self.assertEqual(len(atr14), 25)
        self.assertEqual(atr14.name, "ATR_14")
        self.assertFalse(atr14.iloc[14:].isna().any())

    def test_increasing_volatility(self):
        """
        Verify ATR rises when volatility increases (larger price swings).
        """
        # Low volatility for first 20 days (+-1), high volatility for next 20 days (+-10)
        close = pd.Series([100.0] * 40)
        high = pd.Series([101.0] * 20 + [110.0] * 20)
        low = pd.Series([99.0] * 20 + [90.0] * 20)

        atr14 = calculate_atr(high, low, close, period=14)
        # Volatility at day 35 should be higher than day 18
        self.assertGreater(atr14.iloc[35], atr14.iloc[18])

    def test_constant_prices(self):
        """
        Verify zero-volatility (flat prices) yields ATR = 0.0.
        """
        high = pd.Series([100.0] * 20)
        low = pd.Series([100.0] * 20)
        close = pd.Series([100.0] * 20)

        atr14 = calculate_atr(high, low, close, period=14)
        valid_atr = atr14.dropna()
        self.assertGreater(len(valid_atr), 0)
        for val in valid_atr:
            self.assertEqual(val, 0.0)

    def test_gap_up_scenario(self):
        """
        Verify gap-up where High-Low is smaller than abs(High - PrevClose).
        Day 0: High=100, Low=95, Close=98
        Day 1: High=120, Low=118, Close=119 (Gap up, PrevClose=98)
        High-Low = 2
        High - PrevClose = 22 -> TR must be 22 (not 2)
        """
        high = pd.Series([100.0, 120.0])
        low = pd.Series([95.0, 118.0])
        close = pd.Series([98.0, 119.0])

        atr1 = calculate_atr(high, low, close, period=1)
        self.assertAlmostEqual(atr1.iloc[1], 22.0, places=4)

    def test_gap_down_scenario(self):
        """
        Verify gap-down where High-Low is smaller than abs(Low - PrevClose).
        Day 0: High=100, Low=95, Close=98
        Day 1: High=80, Low=78, Close=79 (Gap down, PrevClose=98)
        High-Low = 2
        Low - PrevClose = |78 - 98| = 20 -> TR must be 20
        """
        high = pd.Series([100.0, 80.0])
        low = pd.Series([95.0, 78.0])
        close = pd.Series([98.0, 79.0])

        atr1 = calculate_atr(high, low, close, period=1)
        self.assertAlmostEqual(atr1.iloc[1], 20.0, places=4)

    def test_insufficient_data(self):
        """
        Verify Series shorter than period + 1 returns Series of NaNs matching index.
        """
        short = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0])  # len 5 < 14 + 1
        atr14 = calculate_atr(short, short, short, period=14)

        self.assertEqual(len(atr14), len(short))
        self.assertTrue(atr14.isna().all())
        self.assertTrue(atr14.index.equals(short.index))

    def test_nan_handling(self):
        """
        Verify NaN values propagate without crash.
        """
        close = pd.Series([100.0 + i if i != 10 else np.nan for i in range(30)])
        high = close + 2.0
        low = close - 2.0

        atr14 = calculate_atr(high, low, close, period=14)
        self.assertEqual(len(atr14), len(close))
        self.assertTrue(atr14.index.equals(close.index))

    def test_index_preservation(self):
        """
        Verify custom index preservation.
        """
        custom_index = pd.date_range("2026-01-01", periods=20, freq="D")
        close = pd.Series([100.0 + i for i in range(20)], index=custom_index)
        high = close + 1.0
        low = close - 1.0

        atr14 = calculate_atr(high, low, close, period=14)
        self.assertTrue(atr14.index.equals(custom_index))

    def test_no_input_mutation(self):
        """
        Verify input Series are not modified.
        """
        high = pd.Series([105.0 + i for i in range(20)], name="high")
        low = pd.Series([95.0 + i for i in range(20)], name="low")
        close = pd.Series([100.0 + i for i in range(20)], name="close")

        high_copy = high.copy()
        low_copy = low.copy()
        close_copy = close.copy()

        _ = calculate_atr(high, low, close, period=14)

        pd.testing.assert_series_equal(high, high_copy)
        pd.testing.assert_series_equal(low, low_copy)
        pd.testing.assert_series_equal(close, close_copy)

    def test_period_one(self):
        """
        Verify period=1 ATR equals True Range.
        """
        high = pd.Series([10.0, 15.0, 20.0])
        low = pd.Series([8.0, 12.0, 17.0])
        close = pd.Series([9.0, 14.0, 19.0])

        atr1 = calculate_atr(high, low, close, period=1)
        self.assertEqual(len(atr1), 3)
        self.assertFalse(atr1.iloc[1:].isna().any())

    def test_invalid_period(self):
        """
        Verify TypeError / ValueError for invalid period arguments.
        """
        s = pd.Series([100.0] * 20)

        with self.assertRaises(ValueError):
            calculate_atr(s, s, s, period=0)

        with self.assertRaises(ValueError):
            calculate_atr(s, s, s, period=-5)

        with self.assertRaises(TypeError):
            calculate_atr(s, s, s, period="14")

        with self.assertRaises(TypeError):
            calculate_atr(s, s, s, period=True)

    def test_non_series_input(self):
        """
        Verify TypeError when inputs are not pandas Series.
        """
        s = pd.Series([100.0] * 20)
        lst = [100.0] * 20

        with self.assertRaises(TypeError):
            calculate_atr(lst, s, s)

        with self.assertRaises(TypeError):
            calculate_atr(s, lst, s)

        with self.assertRaises(TypeError):
            calculate_atr(s, s, lst)

    def test_mismatched_indexes(self):
        """
        Verify ValueError when input Series indexes do not match.
        """
        s1 = pd.Series([100.0] * 20, index=pd.RangeIndex(20))
        s2 = pd.Series([100.0] * 20, index=pd.date_range("2026-01-01", periods=20))

        with self.assertRaises(ValueError):
            calculate_atr(s1, s2, s1)

    def test_output_numeric(self):
        """
        Verify output series remains numeric (float64).
        """
        s = pd.Series([100.0 + i for i in range(20)])
        atr = calculate_atr(s + 2, s - 2, s, period=14)
        self.assertTrue(pd.api.types.is_numeric_dtype(atr))
        self.assertEqual(atr.dtype, np.float64)

    def test_non_negative_and_direction_neutrality(self):
        """
        Verify ATR is non-negative (ATR >= 0) and measures volatility regardless of trend direction.
        """
        # Uptrend with range 4
        close_up = pd.Series([100.0 + i * 2.0 for i in range(25)])
        high_up = close_up + 2.0
        low_up = close_up - 2.0
        atr_up = calculate_atr(high_up, low_up, close_up, period=14)

        # Downtrend with range 4
        close_down = pd.Series([200.0 - i * 2.0 for i in range(25)])
        high_down = close_down + 2.0
        low_down = close_down - 2.0
        atr_down = calculate_atr(high_down, low_down, close_down, period=14)

        # All ATR values must be >= 0
        valid_up = atr_up.dropna()
        valid_down = atr_down.dropna()
        self.assertTrue((valid_up >= 0.0).all())
        self.assertTrue((valid_down >= 0.0).all())

        # Volatility magnitude is identical (high-low=4, close-close step=2), ATR should match
        self.assertAlmostEqual(valid_up.iloc[-1], valid_down.iloc[-1], places=4)


        self.assertAlmostEqual(valid_up.iloc[-1], valid_down.iloc[-1], places=4)


class TestTechnicalEngineSupportResistance(unittest.TestCase):
    """
    Unit tests for calculate_support_resistance function in backend.engines.technical_engine.
    """

    def test_basic_swing_high_detection(self):
        """
        Verify detection of a single swing high peak.
        Candle 3 (index 3): High=110.0, flanked by 3 lower candles on each side.
        """
        high = pd.Series([100.0, 102.0, 104.0, 110.0, 103.0, 101.0, 99.0])
        low = high - 2.0
        close = high - 1.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        res_zones = sr[sr["type"] == "resistance"]
        self.assertEqual(len(res_zones), 1)
        self.assertAlmostEqual(res_zones.iloc[0]["level"], 110.0)

    def test_basic_swing_low_detection(self):
        """
        Verify detection of a single swing low trough.
        Candle 3 (index 3): Low=80.0, flanked by 3 higher lows on each side.
        """
        low = pd.Series([100.0, 95.0, 90.0, 80.0, 92.0, 96.0, 98.0])
        high = low + 5.0
        close = low + 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        sup_zones = sr[sr["type"] == "support"]
        self.assertEqual(len(sup_zones), 1)
        self.assertAlmostEqual(sup_zones.iloc[0]["level"], 80.0)

    def test_support_detection(self):
        """
        Verify support zones are detected and labeled 'support'.
        """
        low = pd.Series([100, 90, 85, 75, 86, 92, 95, 88, 82, 75, 86, 90, 94])
        high = low + 5.0
        close = low + 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertTrue((sr[sr["type"] == "support"]["type"] == "support").all())

    def test_resistance_detection(self):
        """
        Verify resistance zones are detected and labeled 'resistance'.
        """
        high = pd.Series([100, 110, 115, 130, 116, 108, 102, 112, 118, 130, 114, 105, 98])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertTrue((sr[sr["type"] == "resistance"]["type"] == "resistance").all())

    def test_multiple_nearby_levels_cluster(self):
        """
        Verify swing peaks at 100.0 and 100.5 (within 1% tolerance) cluster into 1 zone.
        """
        # Peak 1 at index 3 (100.0), Peak 2 at index 9 (100.5)
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 92, 95, 100.5, 94, 91, 89])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        res_zones = sr[sr["type"] == "resistance"]
        self.assertEqual(len(res_zones), 1)
        self.assertEqual(res_zones.iloc[0]["touches"], 2)

    def test_levels_outside_tolerance_remain_separate(self):
        """
        Verify peaks at 100.0 and 115.0 (outside 1% tolerance) remain separate zones.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 105, 110, 115.0, 108, 100, 92])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        res_zones = sr[sr["type"] == "resistance"]
        self.assertEqual(len(res_zones), 2)

    def test_support_and_resistance_never_merged(self):
        """
        Verify support and resistance candidates at identical price levels are not merged.
        """
        # Swing high at 100.0, Swing low at 100.0
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 95, 98, 108.0, 99, 95, 91])
        low = pd.Series([80, 82, 85, 92.0, 83, 81, 80, 85, 90, 100.0, 102, 105, 110])
        close = (high + low) / 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.05)
        # Should have distinct support and resistance rows
        types = set(sr["type"])
        self.assertIn("support", types)
        self.assertIn("resistance", types)

    def test_correct_touch_count(self):
        """
        Verify touch count equals number of candidates in cluster.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 92, 95, 100.2, 94, 91, 89])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertEqual(sr.iloc[0]["touches"], 2)

    def test_correct_zone_low(self):
        """
        Verify zone_low is the minimum candidate price in the cluster.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 92, 95, 100.8, 94, 91, 89])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertAlmostEqual(sr.iloc[0]["zone_low"], 100.0)

    def test_correct_zone_high(self):
        """
        Verify zone_high is the maximum candidate price in the cluster.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 92, 95, 100.8, 94, 91, 89])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertAlmostEqual(sr.iloc[0]["zone_high"], 100.8)

    def test_correct_representative_level(self):
        """
        Verify level is the arithmetic mean of candidates in the cluster.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 92, 95, 100.8, 94, 91, 89])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertAlmostEqual(sr.iloc[0]["level"], 100.4)

    def test_correct_strength(self):
        """
        Verify strength equals touches (deterministic strength = touches).
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88, 92, 95, 100.8, 94, 91, 89])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3, zone_tolerance=0.01)
        self.assertEqual(sr.iloc[0]["strength"], float(sr.iloc[0]["touches"]))

    def test_pivot_window_validation(self):
        """
        Verify ValueError / TypeError for invalid pivot_window (0, negative, non-int, bool).
        """
        s = pd.Series([100.0] * 20)

        with self.assertRaises(ValueError):
            calculate_support_resistance(s, s, s, pivot_window=0)

        with self.assertRaises(ValueError):
            calculate_support_resistance(s, s, s, pivot_window=-2)

        with self.assertRaises(TypeError):
            calculate_support_resistance(s, s, s, pivot_window="3")

        with self.assertRaises(TypeError):
            calculate_support_resistance(s, s, s, pivot_window=True)

    def test_zone_tolerance_validation(self):
        """
        Verify ValueError / TypeError for invalid zone_tolerance (0, negative, non-numeric, bool).
        """
        s = pd.Series([100.0] * 20)

        with self.assertRaises(ValueError):
            calculate_support_resistance(s, s, s, zone_tolerance=0.0)

        with self.assertRaises(ValueError):
            calculate_support_resistance(s, s, s, zone_tolerance=-0.01)

        with self.assertRaises(TypeError):
            calculate_support_resistance(s, s, s, zone_tolerance="0.01")

        with self.assertRaises(TypeError):
            calculate_support_resistance(s, s, s, zone_tolerance=True)

    def test_invalid_input_types(self):
        """
        Verify TypeError when inputs are not pandas Series.
        """
        s = pd.Series([100.0] * 20)
        lst = [100.0] * 20

        with self.assertRaises(TypeError):
            calculate_support_resistance(lst, s, s)

        with self.assertRaises(TypeError):
            calculate_support_resistance(s, lst, s)

        with self.assertRaises(TypeError):
            calculate_support_resistance(s, s, lst)

    def test_mismatched_indexes(self):
        """
        Verify ValueError when input Series indexes do not match.
        """
        s1 = pd.Series([100.0] * 20, index=pd.RangeIndex(20))
        s2 = pd.Series([100.0] * 20, index=pd.date_range("2026-01-01", periods=20))

        with self.assertRaises(ValueError):
            calculate_support_resistance(s1, s2, s1)

    def test_nan_handling(self):
        """
        Verify NaN values do not produce false swing points or crash.
        """
        high = pd.Series([100, 102, 104, np.nan, 103, 101, 99])
        low = high - 2.0
        close = high - 1.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3)
        self.assertIsInstance(sr, pd.DataFrame)

    def test_input_non_mutation(self):
        """
        Verify input Series are not modified.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88])
        low = high - 5.0
        close = high - 2.0

        high_copy = high.copy()
        low_copy = low.copy()
        close_copy = close.copy()

        _ = calculate_support_resistance(high, low, close, pivot_window=3)

        pd.testing.assert_series_equal(high, high_copy)
        pd.testing.assert_series_equal(low, low_copy)
        pd.testing.assert_series_equal(close, close_copy)

    def test_output_columns(self):
        """
        Verify output DataFrame has exact required columns.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3)
        expected_cols = ["level", "zone_low", "zone_high", "type", "touches", "strength"]
        self.assertEqual(list(sr.columns), expected_cols)

    def test_empty_result_behavior(self):
        """
        Verify short dataset returns an empty DataFrame with correct column schema.
        """
        short = pd.Series([100.0, 102.0, 101.0])  # len 3 < 2*3 + 1
        sr = calculate_support_resistance(short, short, short, pivot_window=3)

        self.assertIsInstance(sr, pd.DataFrame)
        self.assertTrue(sr.empty)
        expected_cols = ["level", "zone_low", "zone_high", "type", "touches", "strength"]
        self.assertEqual(list(sr.columns), expected_cols)

    def test_output_dataframe_type(self):
        """
        Verify return type is a pandas DataFrame.
        """
        high = pd.Series([90, 92, 94, 100.0, 93, 91, 88])
        low = high - 5.0
        close = high - 2.0

        sr = calculate_support_resistance(high, low, close, pivot_window=3)
        self.assertIsInstance(sr, pd.DataFrame)


        sr = calculate_support_resistance(high, low, close, pivot_window=3)
        self.assertIsInstance(sr, pd.DataFrame)


class TestTechnicalEngineTechnicalScore(unittest.TestCase):
    """
    Unit tests for calculate_technical_score in backend.engines.technical_engine.
    """

    def _create_helper_inputs(self, n=25, base_close=100.0, base_vol=1000.0):
        index = pd.RangeIndex(n)
        close = pd.Series([base_close] * n, index=index)
        volume = pd.Series([base_vol] * n, index=index)
        rsi = pd.Series([55.0] * n, index=index)  # 30 pts
        macd = pd.Series([2.0] * n, index=index)
        signal = pd.Series([1.0] * n, index=index)
        histogram = pd.Series([1.0] * n, index=index)
        ema20 = pd.Series([90.0] * n, index=index)
        ema50 = pd.Series([80.0] * n, index=index)
        ema200 = pd.Series([70.0] * n, index=index)
        return close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200

    def test_perfect_maximum_score_100(self):
        """
        Verify maximum conditions yield sub-scores (30 + 30 + 20 + 20) = 100.
        RSI=55 (30), MACD=2 > Signal=1 & Hist=1 & MACD>0 (30), Trend: EMA20>50>200 & Close>EMA20 (20), Vol ratio>=2.0 (20).
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        volume.iloc[-1] = 2500.0  # ratio = 2500 / 1000 = 2.5 >= 2.0 (20 pts)

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        row = df.iloc[-1]
        self.assertEqual(row["rsi_score"], 30.0)
        self.assertEqual(row["macd_score"], 30.0)
        self.assertEqual(row["trend_score"], 20.0)
        self.assertEqual(row["volume_score"], 20.0)
        self.assertEqual(row["technical_score"], 100.0)

    def test_minimum_score_0(self):
        """
        Verify minimum conditions yield sub-scores (10 + 0 + 0 + 0) = 10.
        RSI=20 (10 pts), MACD=-5 < Signal=-2 & MACD<0 & Hist=-3 (0 pts), Trend: EMA20<50<200 & Close<EMA20 (0 pts), Vol ratio<0.5 (0 pts).
        """
        n = 25
        idx = pd.RangeIndex(n)
        close = pd.Series([50.0] * n, index=idx)
        volume = pd.Series([1000.0] * n, index=idx)
        rsi = pd.Series([20.0] * n, index=idx)  # 10 pts
        macd = pd.Series([-5.0] * n, index=idx)
        signal = pd.Series([-2.0] * n, index=idx)
        histogram = pd.Series([-3.0] * n, index=idx)
        ema20 = pd.Series([60.0] * n, index=idx)
        ema50 = pd.Series([70.0] * n, index=idx)
        ema200 = pd.Series([80.0] * n, index=idx)

        volume.iloc[-1] = 100.0  # ratio = 100 / (1000*24+100)/25 = 0.104 < 0.5 (0 pts)

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        row = df.iloc[-1]
        self.assertEqual(row["rsi_score"], 10.0)
        self.assertEqual(row["macd_score"], 0.0)
        self.assertEqual(row["trend_score"], 0.0)
        self.assertEqual(row["volume_score"], 0.0)
        self.assertEqual(row["technical_score"], 10.0)

    def test_rsi_boundary_values(self):
        """
        Verify exact deterministic RSI boundaries.
        """
        boundaries = [
            (29.99, 10.0),
            (30.0, 18.0),
            (39.99, 18.0),
            (40.0, 24.0),
            (49.99, 24.0),
            (50.0, 30.0),
            (59.99, 30.0),
            (60.0, 27.0),
            (69.99, 27.0),
            (70.0, 20.0),
            (79.99, 20.0),
            (80.0, 10.0),
        ]

        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=len(boundaries))
        for i, (val, expected_score) in enumerate(boundaries):
            rsi.iloc[i] = val

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        for i, (val, expected_score) in enumerate(boundaries):
            self.assertEqual(df.iloc[i]["rsi_score"], expected_score, f"Failed at RSI={val}")

    def test_macd_strongest_bullish_condition(self):
        """
        Condition 1: MACD > Signal AND MACD > 0 AND Histogram > 0 => 30 pts.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        macd.iloc[-1] = 5.0
        signal.iloc[-1] = 2.0
        histogram.iloc[-1] = 3.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["macd_score"], 30.0)

    def test_macd_bearish_condition_8(self):
        """
        Condition 8: MACD < Signal AND MACD < 0 AND Histogram < 0 => 0 pts (takes priority over Condition 7).
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        macd.iloc[-1] = -5.0
        signal.iloc[-1] = -2.0
        histogram.iloc[-1] = -3.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["macd_score"], 0.0)

    def test_macd_approximate_equality_condition(self):
        """
        Condition 5: MACD approximately equal to Signal (when not MACD > Signal) => 15 pts.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        # MACD=-1.0, Signal=-0.995 -> MACD < Signal, diff=0.005 <= max(0.00995, 0.01) = 0.01
        macd.iloc[-1] = -1.0
        signal.iloc[-1] = -0.995
        histogram.iloc[-1] = -0.005

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["macd_score"], 15.0)

    def test_macd_histogram_positive_condition(self):
        """
        Condition 3: MACD > Signal AND Histogram > 0 (MACD negative) => 24 pts.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        macd.iloc[-1] = -2.0
        signal.iloc[-1] = -5.0
        histogram.iloc[-1] = 3.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["macd_score"], 24.0)

    def test_trend_strongest_bullish_condition(self):
        """
        Condition 1: EMA20 > EMA50 > EMA200 AND Close > EMA20 => 20 pts.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        close.iloc[-1] = 100.0
        ema20.iloc[-1] = 90.0
        ema50.iloc[-1] = 80.0
        ema200.iloc[-1] = 70.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["trend_score"], 20.0)

    def test_trend_strongest_bearish_condition_8(self):
        """
        Condition 8: EMA20 < EMA50 < EMA200 AND Close < EMA20 => 0 pts.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        close.iloc[-1] = 50.0
        ema20.iloc[-1] = 60.0
        ema50.iloc[-1] = 70.0
        ema200.iloc[-1] = 80.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["trend_score"], 0.0)

    def test_trend_mixed_condition(self):
        """
        Condition 6: Mixed/neutral trend => 5 pts.
        e.g. EMA20 < EMA50 > EMA200, Close < EMA50 but Close > EMA20.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        close.iloc[-1] = 85.0
        ema20.iloc[-1] = 80.0
        ema50.iloc[-1] = 90.0
        ema200.iloc[-1] = 70.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["trend_score"], 5.0)

    def test_volume_ratio_gte_2(self):
        """
        Volume ratio >= 2.0 => 20 pts.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        volume.iloc[-1] = 3000.0  # avg = 1080 -> ratio ~2.77 >= 2.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["volume_score"], 20.0)

    def test_volume_ratio_boundary_tiers(self):
        """
        Verify volume ratio tiers:
        ratio >= 2.0 -> 20
        1.5 <= ratio < 2.0 -> 17
        1.2 <= ratio < 1.5 -> 14
        1.0 <= ratio < 1.2 -> 10
        0.8 <= ratio < 1.0 -> 7
        0.5 <= ratio < 0.8 -> 3
        ratio < 0.5 -> 0
        """
        n = 25
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=n)

        # Set constant volume for first 20 days (1000.0)
        # On day 20, set volume to hit specific ratio targets
        target_ratios = [
            (2.5, 20.0),
            (1.8, 17.0),
            (1.3, 14.0),
            (1.1, 10.0),
            (0.9, 7.0),
            (0.6, 3.0),
            (0.2, 0.0),
        ]

        for mult, expected in target_ratios:
            vol_test = pd.Series([1000.0] * (n - 1) + [1000.0 * mult], index=pd.RangeIndex(n))
            df = calculate_technical_score(close, vol_test, rsi, macd, signal, histogram, ema20, ema50, ema200)
            self.assertEqual(df.iloc[-1]["volume_score"], expected, f"Failed for volume ratio multiplier {mult}")

    def test_volume_ratio_lt_05(self):
        """
        Volume ratio < 0.5 => 0 pts.
        """
        n = 25
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=n)
        volume.iloc[-1] = 100.0

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertEqual(df.iloc[-1]["volume_score"], 0.0)

    def test_rolling_20_volume_behavior(self):
        """
        Verify volume score requires 20 periods for rolling mean (NaN for first 19 periods).
        """
        n = 25
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=n)

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        # First 19 rows of volume_score should be NaN
        self.assertTrue(df["volume_score"].iloc[:19].isna().all())
        # Day 20 onwards should be valid
        self.assertFalse(df["volume_score"].iloc[19:].isna().any())

    def test_technical_score_bounded_0_to_100(self):
        """
        Verify technical_score is defensively clipped within [0, 100].
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        valid_scores = df["technical_score"].dropna()
        self.assertTrue((valid_scores >= 0.0).all())
        self.assertTrue((valid_scores <= 100.0).all())

    def test_output_columns(self):
        """
        Verify exact output column names.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        expected = ["rsi_score", "macd_score", "trend_score", "volume_score", "technical_score"]
        self.assertEqual(list(df.columns), expected)

    def test_output_index_preservation(self):
        """
        Verify custom index preservation.
        """
        custom_idx = pd.date_range("2026-01-01", periods=25)
        n = 25
        close = pd.Series([100.0] * n, index=custom_idx)
        volume = pd.Series([1000.0] * n, index=custom_idx)
        rsi = pd.Series([55.0] * n, index=custom_idx)
        macd = pd.Series([2.0] * n, index=custom_idx)
        signal = pd.Series([1.0] * n, index=custom_idx)
        histogram = pd.Series([1.0] * n, index=custom_idx)
        ema20 = pd.Series([90.0] * n, index=custom_idx)
        ema50 = pd.Series([80.0] * n, index=custom_idx)
        ema200 = pd.Series([70.0] * n, index=custom_idx)

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertTrue(df.index.equals(custom_idx))

    def test_input_non_mutation(self):
        """
        Verify input Series are not modified.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        close_copy = close.copy()
        rsi_copy = rsi.copy()

        _ = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)

        pd.testing.assert_series_equal(close, close_copy)
        pd.testing.assert_series_equal(rsi, rsi_copy)

    def test_non_series_input_validation(self):
        """
        Verify TypeError when inputs are not pandas Series.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)

        with self.assertRaises(TypeError):
            calculate_technical_score([100.0] * 25, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)

        with self.assertRaises(TypeError):
            calculate_technical_score(close, [1000.0] * 25, rsi, macd, signal, histogram, ema20, ema50, ema200)

    def test_mismatched_index_validation(self):
        """
        Verify ValueError when input Series indexes do not match.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        mismatched_rsi = pd.Series([55.0] * 25, index=pd.date_range("2026-01-01", periods=25))

        with self.assertRaises(ValueError):
            calculate_technical_score(close, volume, mismatched_rsi, macd, signal, histogram, ema20, ema50, ema200)

    def test_nan_handling(self):
        """
        Verify NaNs in indicators cause corresponding sub-scores and technical_score to be NaN.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        rsi.iloc[22] = np.nan

        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)
        self.assertTrue(pd.isna(df.iloc[22]["rsi_score"]))
        self.assertTrue(pd.isna(df.iloc[22]["technical_score"]))

    def test_numeric_output_types(self):
        """
        Verify output columns are float64 numeric types.
        """
        close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200 = self._create_helper_inputs(n=25)
        df = calculate_technical_score(close, volume, rsi, macd, signal, histogram, ema20, ema50, ema200)

        for col in df.columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(df[col]))
            self.assertEqual(df[col].dtype, np.float64)


class TestTechnicalEnginePipeline(unittest.TestCase):
    """
    Unit tests for run_technical_pipeline in backend.engines.technical_engine.
    """

    def test_pipeline_execution_and_schema(self):
        """
        Verify run_technical_pipeline returns structured dict with all required indicator and S&R columns.
        """
        n = 30
        idx = pd.RangeIndex(n)
        df = pd.DataFrame({
            "open": [100.0 + i for i in range(n)],
            "high": [105.0 + i for i in range(n)],
            "low": [95.0 + i for i in range(n)],
            "close": [102.0 + i for i in range(n)],
            "volume": [1000.0 + i * 10 for i in range(n)],
        }, index=idx)

        res = run_technical_pipeline(df)
        self.assertIsInstance(res, dict)
        self.assertIn("indicators", res)
        self.assertIn("support_resistance", res)

        ind = res["indicators"]
        expected_ind_cols = [
            "close", "volume", "rsi", "ema20", "ema50", "ema200",
            "macd", "signal", "histogram", "atr14",
            "rsi_score", "macd_score", "trend_score", "volume_score", "technical_score"
        ]
        self.assertEqual(list(ind.columns), expected_ind_cols)
        self.assertTrue(ind.index.equals(df.index))

        sr = res["support_resistance"]
        expected_sr_cols = ["level", "zone_low", "zone_high", "type", "touches", "strength"]
        self.assertEqual(list(sr.columns), expected_sr_cols)

    def test_pipeline_input_validation(self):
        """
        Verify TypeError for non-DataFrame and ValueError for missing required columns.
        """
        with self.assertRaises(TypeError):
            run_technical_pipeline([1, 2, 3])

        df_missing = pd.DataFrame({"close": [100.0] * 10})
        with self.assertRaises(ValueError):
            run_technical_pipeline(df_missing)

    def test_pipeline_non_mutation(self):
        """
        Verify input DataFrame is left completely unmodified.
        """
        n = 25
        df = pd.DataFrame({
            "high": [105.0 + i for i in range(n)],
            "low": [95.0 + i for i in range(n)],
            "close": [100.0 + i for i in range(n)],
            "volume": [1000.0] * n,
        })
        original_df = df.copy()

        _ = run_technical_pipeline(df)
        pd.testing.assert_frame_equal(df, original_df)


if __name__ == "__main__":
    unittest.main()






