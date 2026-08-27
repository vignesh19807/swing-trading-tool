"""
Test Volatility Analyzer Module
================================

Unit & Integration tests for Volatility Logic Analyzer (backend/logic/volatility_analyzer.py).

Verifies:
1. None DataFrame
2. Empty DataFrame
3. All prices missing
4. Insufficient history (< 21 valid price observations)
5. Partial history (21 <= valid observations < 61)
6. Complete history (>= 61 valid price observations)
7. Constant prices (0 volatility)
8. High volatility classification (> 30.0%)
9. Low volatility classification (<= 15.0%)
10. Maximum drawdown math
11. Annualization scaling (sqrt(252))
12. ATR integration & ATR% calculation
13. Non-numeric prices conversion
14. Zero and negative prices filtering
15. Volatility trend expanding
16. Volatility trend contracting
17. Symbol normalization
18. Unknown symbol handling
19. Duplicate dates handling
20. Missing trading date gap handling
21. Real execution against INFY, TCS, WIPRO, RELIANCE, HDFCBANK
"""

import math
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

from backend.logic.volatility_analyzer import analyze_volatility


class TestVolatilityAnalyzer(unittest.TestCase):

    # ============================================================
    # 21. VERIFIED STOCKS EXECUTION
    # ============================================================
    def test_21_verified_stocks_execution(self):
        """21. Test that analyze_volatility runs successfully on all 5 verified stocks."""
        test_stocks = [
            "INFY",
            "TCS",
            "WIPRO",
            "RELIANCE",
            "HDFCBANK",
        ]

        allowed_statuses = {"VALID", "PARTIAL", "INSUFFICIENT"}
        allowed_trends = {"Expanding", "Contracting", "Stable", "Insufficient Data"}
        allowed_classifications = {"Low", "Moderate", "High", "Insufficient Data"}

        for symbol in test_stocks:
            res = analyze_volatility(symbol)

            # Assert return structure
            self.assertIsInstance(res, dict)
            self.assertEqual(res["symbol"], symbol)
            self.assertIn(res["status"], allowed_statuses)
            self.assertIsInstance(res["records"], int)
            self.assertIsInstance(res["valid_price_observations"], int)
            self.assertIsInstance(res["missing_price_observations"], int)

            # All 5 stocks in DB have 500 daily records and must be VALID
            self.assertEqual(res["status"], "VALID")
            self.assertEqual(res["records"], 500)
            self.assertGreaterEqual(res["valid_price_observations"], 61)

            self.assertIsInstance(res["latest_close"], float)
            self.assertIsInstance(res["volatility_20d_annualized"], float)
            self.assertIsInstance(res["volatility_60d_annualized"], float)
            self.assertIn(res["volatility_trend"], allowed_trends)
            self.assertIn(res["volatility_classification"], allowed_classifications)
            self.assertIsInstance(res["max_drawdown_60d"], float)
            self.assertLessEqual(res["max_drawdown_60d"], 0.0)
            self.assertIsInstance(res["atr_14"], float)
            self.assertIsInstance(res["atr_percent"], float)

    # ============================================================
    # 17. SYMBOL NORMALIZATION
    # ============================================================
    def test_17_symbol_normalization(self):
        """17. Test symbol normalization (uppercase & whitespace trimming)."""
        res = analyze_volatility("  infy  ")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["status"], "VALID")

    # ============================================================
    # 18. UNKNOWN SYMBOL
    # ============================================================
    def test_18_unknown_symbol(self):
        """18. Test unknown stock symbol returns INSUFFICIENT without crashing."""
        res = analyze_volatility("UNKNOWN_STOCK_XYZ")

        self.assertEqual(res["symbol"], "UNKNOWN_STOCK_XYZ")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_price_observations"], 0)
        self.assertIsNone(res["latest_close"])
        self.assertIsNone(res["volatility_20d_annualized"])
        self.assertEqual(res["volatility_trend"], "Insufficient Data")

    # ============================================================
    # SYNTHETIC EDGE CASE TESTS (MOCKED DATA SERVICE)
    # ============================================================

    # 1. None DataFrame
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_1_none_dataframe(self, mock_get_stock_data):
        """1. Test behavior when get_stock_data returns None."""
        mock_get_stock_data.return_value = None

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertIsNone(res["latest_close"])

    # 2. Empty DataFrame
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_2_empty_dataframe(self, mock_get_stock_data):
        """2. Test behavior when get_stock_data returns empty DataFrame."""
        mock_get_stock_data.return_value = pd.DataFrame()

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertIsNone(res["latest_close"])

    # 3. All prices missing
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_3_all_prices_missing(self, mock_get_stock_data):
        """3. Test stock with records but all close prices NaN/missing."""
        mock_df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-02"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [None, None],
            "volume": [1000, 1100]
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 2)
        self.assertEqual(res["valid_price_observations"], 0)
        self.assertIsNone(res["latest_close"])

    # 4. Insufficient history (< 21 valid prices)
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_4_insufficient_history(self, mock_get_stock_data):
        """4. Test that fewer than 21 valid prices returns INSUFFICIENT with all metrics None."""
        dates = [f"2025-01-{i:02d}" for i in range(1, 16)]  # 15 days
        mock_df = pd.DataFrame({
            "date": dates,
            "close": [100.0 + i for i in range(15)]
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["valid_price_observations"], 15)
        self.assertIsNone(res["volatility_20d_annualized"])
        self.assertIsNone(res["volatility_60d_annualized"])

    # 5. Partial history (21 to 60 valid prices)
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_5_partial_history(self, mock_get_stock_data):
        """5. Test that 30 valid prices yields status PARTIAL (HV20 present, HV60/MaxDD60 None)."""
        dates = pd.date_range("2025-01-01", periods=30, freq="D").strftime("%Y-%m-%d")
        np.random.seed(42)
        prices = 100.0 + np.random.randn(30).cumsum()
        highs = prices + 2.0
        lows = prices - 2.0

        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": [1000] * 30
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["valid_price_observations"], 30)
        self.assertIsNotNone(res["volatility_20d_annualized"])
        self.assertIsNone(res["volatility_60d_annualized"])
        self.assertIsNone(res["max_drawdown_60d"])
        self.assertIsNotNone(res["atr_14"])
        self.assertIsNotNone(res["atr_percent"])

    # 6. Complete history (>= 61 valid prices)
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_6_complete_history(self, mock_get_stock_data):
        """6. Test that 70 valid prices yields status VALID with all metrics computed."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        np.random.seed(42)
        prices = 100.0 + np.random.randn(70).cumsum()
        highs = prices + 2.0
        lows = prices - 2.0

        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["valid_price_observations"], 70)
        self.assertIsNotNone(res["volatility_20d_annualized"])
        self.assertIsNotNone(res["volatility_60d_annualized"])
        self.assertIsNotNone(res["max_drawdown_60d"])
        self.assertIsNotNone(res["atr_14"])
        self.assertIsNotNone(res["atr_percent"])

    # 7. Constant prices (0 volatility)
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_7_constant_prices(self, mock_get_stock_data):
        """7. Test flat price series produces 0 volatility and 0 max drawdown."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        mock_df = pd.DataFrame({
            "date": dates,
            "open": [100.0] * 70,
            "high": [100.0] * 70,
            "low": [100.0] * 70,
            "close": [100.0] * 70,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["volatility_20d_annualized"], 0.0)
        self.assertEqual(res["volatility_60d_annualized"], 0.0)
        self.assertEqual(res["max_drawdown_60d"], 0.0)
        self.assertEqual(res["volatility_classification"], "Low")
        self.assertEqual(res["volatility_trend"], "Stable")

    # 8. High volatility (> 30.0%)
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_8_high_volatility(self, mock_get_stock_data):
        """8. Test high price volatility returns classification High (> 30.0%)."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        # Alternating large swings (+-10%)
        prices = [100.0 * (1.10 if i % 2 == 0 else 0.90) for i in range(70)]
        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["volatility_classification"], "High")
        self.assertGreater(res["volatility_20d_annualized"], 30.0)

    # 9. Low volatility (<= 15.0%)
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_9_low_volatility(self, mock_get_stock_data):
        """9. Test low price volatility returns classification Low (<= 15.0%)."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        # Very tiny daily fluctuations (+-0.1%)
        prices = [100.0 * (1.001 if i % 2 == 0 else 0.999) for i in range(70)]
        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p * 1.005 for p in prices],
            "low": [p * 0.995 for p in prices],
            "close": prices,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["volatility_classification"], "Low")
        self.assertLessEqual(res["volatility_20d_annualized"], 15.0)

    # 10. Maximum drawdown math
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_10_max_drawdown_math(self, mock_get_stock_data):
        """10. Test exact maximum drawdown calculation (peak 200.0 to 100.0 = -50.0%)."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        prices = [100.0] * 10 + [200.0] + [100.0] + [150.0] * 58
        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        # Drop from 200.0 to 100.0 is exactly -50.0%
        self.assertAlmostEqual(res["max_drawdown_60d"], -50.0, places=2)

    # 11. Annualization scaling
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_11_annualization_scaling(self, mock_get_stock_data):
        """11. Test that annualization multiplies daily std by sqrt(252) * 100."""
        dates = pd.date_range("2025-01-01", periods=25, freq="D").strftime("%Y-%m-%d")
        np.random.seed(123)
        prices = 100.0 + np.random.randn(25).cumsum()
        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": prices + 1.0,
            "low": prices - 1.0,
            "close": prices,
            "volume": [1000] * 25
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        # Manual verification
        log_rets = np.log(prices[1:] / prices[:-1])[-20:]
        expected_std = pd.Series(log_rets).std(ddof=1)
        expected_hv20 = expected_std * math.sqrt(252.0) * 100.0

        self.assertAlmostEqual(res["volatility_20d_annualized"], round(expected_hv20, 4), places=4)

    # 12. ATR integration & ATR% calculation
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_12_atr_integration(self, mock_get_stock_data):
        """12. Test integration with technical_engine.calculate_atr and ATR% calculation."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        mock_df = pd.DataFrame({
            "date": dates,
            "open": [100.0] * 70,
            "high": [105.0] * 70,
            "low": [95.0] * 70,
            "close": [100.0] * 70,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        # High - Low = 10.0 every day -> ATR-14 = 10.0
        self.assertAlmostEqual(res["atr_14"], 10.0, places=2)
        # ATR% = 10.0 / 100.0 * 100 = 10.0%
        self.assertAlmostEqual(res["atr_percent"], 10.0, places=2)

    # 13. Non-numeric prices
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_13_non_numeric_prices(self, mock_get_stock_data):
        """13. Test non-numeric string prices converted via pd.to_numeric(..., errors='coerce')."""
        dates = pd.date_range("2025-01-01", periods=25, freq="D").strftime("%Y-%m-%d")
        closes = ["invalid"] + [100.0 + i for i in range(24)]
        mock_df = pd.DataFrame({
            "date": dates,
            "open": [100.0] * 25,
            "high": [102.0] * 25,
            "low": [98.0] * 25,
            "close": closes,
            "volume": [1000] * 25
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        # 24 valid prices >= 21 -> status PARTIAL
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["valid_price_observations"], 24)
        self.assertEqual(res["missing_price_observations"], 1)

    # 14. Zero and negative prices
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_14_zero_and_negative_prices(self, mock_get_stock_data):
        """14. Test that close <= 0 prices are filtered out safely."""
        dates = pd.date_range("2025-01-01", periods=25, freq="D").strftime("%Y-%m-%d")
        closes = [0.0, -10.0] + [100.0 + i for i in range(23)]
        mock_df = pd.DataFrame({
            "date": dates,
            "open": [100.0] * 25,
            "high": [102.0] * 25,
            "low": [98.0] * 25,
            "close": closes,
            "volume": [1000] * 25
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["valid_price_observations"], 23)
        self.assertEqual(res["missing_price_observations"], 2)

    # 15. Volatility trend expanding
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_15_volatility_trend_expanding(self, mock_get_stock_data):
        """15. Test HV20 - HV60 > +2.0 returns Expanding."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        # Flat for first 50 days, then huge swings for last 20 days
        np.random.seed(42)
        stable_part = [100.0] * 50
        volatile_part = [100.0 * (1.10 if i % 2 == 0 else 0.90) for i in range(20)]
        prices = stable_part + volatile_part

        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["volatility_trend"], "Expanding")

    # 16. Volatility trend contracting
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_16_volatility_trend_contracting(self, mock_get_stock_data):
        """16. Test HV20 - HV60 < -2.0 returns Contracting."""
        dates = pd.date_range("2025-01-01", periods=70, freq="D").strftime("%Y-%m-%d")
        # Huge swings for first 50 days, then completely flat for last 20 days
        volatile_part = [100.0 * (1.10 if i % 2 == 0 else 0.90) for i in range(50)]
        stable_part = [100.0] * 20
        prices = volatile_part + stable_part

        mock_df = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [1000] * 70
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["volatility_trend"], "Contracting")

    # 19. Duplicate dates
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_19_duplicate_dates(self, mock_get_stock_data):
        """19. Test duplicate dates are deduplicated keeping the last occurrence."""
        mock_df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-01", "2025-01-02"] + [f"2025-01-{i:02d}" for i in range(3, 23)],
            "open": [100.0] * 23,
            "high": [102.0] * 23,
            "low": [98.0] * 23,
            "close": [99.0, 100.0, 101.0] + [101.0 + i for i in range(20)],
            "volume": [1000] * 23
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        # 23 raw rows, 1 duplicate date removed -> 22 valid observations
        self.assertEqual(res["records"], 23)
        self.assertEqual(res["valid_price_observations"], 22)
        self.assertEqual(res["status"], "PARTIAL")

    # 20. Missing trading date gap
    @patch("backend.logic.volatility_analyzer.get_stock_data")
    def test_20_missing_trading_date_gap(self, mock_get_stock_data):
        """20. Test non-consecutive trading dates (gaps) are handled natively across available rows."""
        # Dates skipping weekends/holidays
        dates = ["2025-01-01", "2025-01-02", "2025-01-06", "2025-01-07"] + [f"2025-02-{i:02d}" for i in range(1, 20)]
        mock_df = pd.DataFrame({
            "date": dates,
            "open": [100.0] * len(dates),
            "high": [102.0] * len(dates),
            "low": [98.0] * len(dates),
            "close": [100.0 + i for i in range(len(dates))],
            "volume": [1000] * len(dates)
        })
        mock_get_stock_data.return_value = mock_df

        res = analyze_volatility("TEST")
        self.assertEqual(res["valid_price_observations"], len(dates))
        self.assertEqual(res["status"], "PARTIAL")


def main():
    """Run test suite directly."""
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("VOLATILITY ANALYZER TEST SUITE")
    print("==========================================")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestVolatilityAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nALL VOLATILITY ANALYZER TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")


if __name__ == "__main__":
    main()
