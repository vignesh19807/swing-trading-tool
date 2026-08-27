"""
Test ROE Analyzer Module
========================

Unit & Integration tests for ROE Logic Analyzer (backend/logic/roe_analyzer.py).

Verifies:
- Execution on verified stocks (INFY, TCS, WIPRO, RELIANCE, HDFCBANK)
- Return dictionary structure and type safety
- Status classification (VALID, PARTIAL, INSUFFICIENT)
- Edge cases: unknown symbols, missing values, synthetic test DataFrames
- Trend and consistency classifications
"""

import unittest
from unittest.mock import patch
import pandas as pd

from backend.logic.roe_analyzer import analyze_roe


class TestROEAnalyzer(unittest.TestCase):

    # ============================================================
    # REAL DATA TESTS (5 VERIFIED STOCKS)
    # ============================================================

    def test_verified_stocks_execution(self):
        """Test that analyze_roe runs successfully on all 5 verified stocks."""
        test_stocks = [
            "INFY",
            "TCS",
            "WIPRO",
            "RELIANCE",
            "HDFCBANK",
        ]

        allowed_statuses = {"VALID", "PARTIAL", "INSUFFICIENT"}
        allowed_trends = {"Improving", "Stable", "Declining", "Insufficient Data"}
        allowed_consistencies = {"High", "Moderate", "Low", "Insufficient Data"}

        for symbol in test_stocks:
            res = analyze_roe(symbol)

            # Assert return structure
            self.assertIsInstance(res, dict)
            self.assertIn("symbol", res)
            self.assertIn("status", res)
            self.assertIn("records", res)
            self.assertIn("data_points", res)
            self.assertIn("valid_roe_observations", res)
            self.assertIn("missing_roe_observations", res)
            self.assertIn("latest_roe", res)
            self.assertIn("roe_trend", res)
            self.assertIn("roe_consistency", res)

            # Assert types & values
            self.assertEqual(res["symbol"], symbol)
            self.assertIn(res["status"], allowed_statuses)
            self.assertIsInstance(res["records"], int)
            self.assertIsInstance(res["data_points"], int)
            self.assertIsInstance(res["valid_roe_observations"], int)
            self.assertIsInstance(res["missing_roe_observations"], int)

            if res["latest_roe"] is not None:
                self.assertIsInstance(res["latest_roe"], (int, float))

            self.assertIn(res["roe_trend"], allowed_trends)
            self.assertIn(res["roe_consistency"], allowed_consistencies)

    def test_symbol_normalization(self):
        """Test symbol normalization (uppercase & whitespace trimming)."""
        res1 = analyze_roe("  infy  ")
        self.assertEqual(res1["symbol"], "INFY")
        self.assertEqual(res1["status"], "VALID")

    def test_unknown_symbol(self):
        """Test unknown stock symbol returns INSUFFICIENT without crashing."""
        res = analyze_roe("UNKNOWN_STOCK_XYZ")

        self.assertEqual(res["symbol"], "UNKNOWN_STOCK_XYZ")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_roe_observations"], 0)
        self.assertIsNone(res["latest_roe"])
        self.assertEqual(res["roe_trend"], "Insufficient Data")
        self.assertEqual(res["roe_consistency"], "Insufficient Data")

    # ============================================================
    # SYNTHETIC EDGE CASE TESTS (MOCKED FINANCIAL SERVICE)
    # ============================================================

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_none_dataframe(self, mock_get_financial_data):
        """Test behavior when financial service returns None."""
        mock_get_financial_data.return_value = None

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["valid_roe_observations"], 0)
        self.assertIsNone(res["latest_roe"])

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_empty_dataframe(self, mock_get_financial_data):
        """Test behavior when financial service returns empty DataFrame."""
        mock_get_financial_data.return_value = pd.DataFrame()

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_all_roe_missing(self, mock_get_financial_data):
        """Test stock with records but all ROE values missing/None/NaN."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [None, None, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_roe_observations"], 0)
        self.assertEqual(res["missing_roe_observations"], 3)
        self.assertIsNone(res["latest_roe"])
        self.assertEqual(res["roe_trend"], "Insufficient Data")
        self.assertEqual(res["roe_consistency"], "Insufficient Data")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_single_valid_roe_observation(self, mock_get_financial_data):
        """Test stock with only 1 valid ROE observation."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [None, 15.5, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_roe_observations"], 1)
        self.assertEqual(res["missing_roe_observations"], 2)
        self.assertEqual(res["latest_roe"], 15.5)
        self.assertEqual(res["roe_trend"], "Insufficient Data")
        self.assertEqual(res["roe_consistency"], "Insufficient Data")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_trend_improving(self, mock_get_financial_data):
        """Test ROE trend classified as Improving (change > +2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [10.0, 12.0, 13.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["latest_roe"], 13.0)
        self.assertEqual(res["roe_trend"], "Improving")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_trend_declining(self, mock_get_financial_data):
        """Test ROE trend classified as Declining (change < -2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [20.0, 17.0, 15.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["latest_roe"], 15.0)
        self.assertEqual(res["roe_trend"], "Declining")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_trend_stable(self, mock_get_financial_data):
        """Test ROE trend classified as Stable (-2.0 <= change <= 2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [15.0, 16.0, 16.5]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["roe_trend"], "Stable")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_consistency_classifications(self, mock_get_financial_data):
        """Test High, Moderate, Low ROE consistency classifications."""
        # High consistency (std <= 2.0)
        mock_df_high = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [15.0, 15.5, 16.0]
        })
        mock_get_financial_data.return_value = mock_df_high
        self.assertEqual(analyze_roe("TEST")["roe_consistency"], "High")

        # Moderate consistency (2.0 < std <= 5.0)
        mock_df_mod = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [10.0, 15.0, 18.0]
        })
        mock_get_financial_data.return_value = mock_df_mod
        self.assertEqual(analyze_roe("TEST")["roe_consistency"], "Moderate")

        # Low consistency (std > 5.0)
        mock_df_low = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": [5.0, 25.0, 12.0]
        })
        mock_get_financial_data.return_value = mock_df_low
        self.assertEqual(analyze_roe("TEST")["roe_consistency"], "Low")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_unsorted_quarters_handling(self, mock_get_financial_data):
        """Test that data is sorted chronologically before identifying latest ROE and trend."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-09-30", "2024-03-31", "2024-06-30"],
            "roe": [25.0, 15.0, 20.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        # Earliest (2024-03-31) = 15.0, Latest (2024-09-30) = 25.0
        self.assertEqual(res["latest_roe"], 25.0)
        self.assertEqual(res["roe_trend"], "Improving")

    @patch("backend.logic.roe_analyzer.get_financial_data")
    def test_non_numeric_roe_conversion(self, mock_get_financial_data):
        """Test that non-numeric ROE strings are converted to NaN safely."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roe": ["invalid", "20.0", "22.5"]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roe("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_roe_observations"], 2)
        self.assertEqual(res["missing_roe_observations"], 1)
        self.assertEqual(res["latest_roe"], 22.5)
        self.assertEqual(res["roe_trend"], "Improving")


def main():
    """Run test suite directly."""
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("ROE ANALYZER TEST SUITE")
    print("==========================================")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestROEAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n🎉 ALL ROE ANALYZER TESTS PASSED")
    else:
        print("\n❌ SOME TESTS FAILED")


if __name__ == "__main__":
    main()
