"""
Unit Tests for Technical Engine (RSI)
=====================================

Completely isolated unit tests for RSI calculation.
Contains zero database or network dependencies.
"""

import unittest
import numpy as np
import pandas as pd

from backend.engines.technical_engine import calculate_rsi


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


if __name__ == "__main__":
    unittest.main()
