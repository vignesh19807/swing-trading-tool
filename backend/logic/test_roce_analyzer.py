"""
Test ROCE Analyzer Module
=========================

Unit & Integration tests for ROCE Logic Analyzer (backend/logic/roce_analyzer.py).

Verifies:
- Execution on verified stocks (INFY, TCS, WIPRO, RELIANCE, HDFCBANK)
- Return dictionary structure and type safety
- Status classification (VALID, PARTIAL, INSUFFICIENT)
- Edge cases 1-16 specified in task requirements
- Boundary conditions (+2.0, -2.0)
"""

import unittest
from unittest.mock import patch
import pandas as pd

from backend.logic.roce_analyzer import analyze_roce


class TestROCEAnalyzer(unittest.TestCase):

    # ============================================================
    # REAL DATA TESTS (5 VERIFIED STOCKS)
    # ============================================================

    def test_verified_stocks_execution(self):
        """Test that analyze_roce runs successfully on all 5 verified stocks."""
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
            res = analyze_roce(symbol)

            # Assert return structure
            self.assertIsInstance(res, dict)
            self.assertIn("symbol", res)
            self.assertIn("status", res)
            self.assertIn("records", res)
            self.assertIn("data_points", res)
            self.assertIn("valid_roce_observations", res)
            self.assertIn("missing_roce", res)
            self.assertIn("missing_roce_observations", res)
            self.assertIn("latest_roce", res)
            self.assertIn("roce_trend", res)
            self.assertIn("roce_consistency", res)

            # Assert types & values
            self.assertEqual(res["symbol"], symbol)
            self.assertIn(res["status"], allowed_statuses)
            self.assertIsInstance(res["records"], int)
            self.assertIsInstance(res["data_points"], int)
            self.assertIsInstance(res["valid_roce_observations"], int)
            self.assertIsInstance(res["missing_roce"], int)
            self.assertIsInstance(res["missing_roce_observations"], int)

            if res["latest_roce"] is not None:
                self.assertIsInstance(res["latest_roce"], (int, float))

            self.assertIn(res["roce_trend"], allowed_trends)
            self.assertIn(res["roce_consistency"], allowed_consistencies)

    def test_symbol_normalization(self):
        """Test symbol normalization (uppercase & whitespace trimming)."""
        res = analyze_roce("  infy  ")
        self.assertEqual(res["symbol"], "INFY")
        self.assertIn(res["status"], {"VALID", "PARTIAL"})

    # ============================================================
    # SYNTHETIC EDGE CASE TESTS 1 - 16
    # ============================================================

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_1_none_dataframe(self, mock_get_financial_data):
        """1. get_financial_data() returns None."""
        mock_get_financial_data.return_value = None

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["valid_roce_observations"], 0)
        self.assertIsNone(res["latest_roce"])

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_2_empty_dataframe(self, mock_get_financial_data):
        """2. Empty DataFrame."""
        mock_get_financial_data.return_value = pd.DataFrame()

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_3_all_roce_missing(self, mock_get_financial_data):
        """3. All ROCE values missing."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [None, None, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_roce_observations"], 0)
        self.assertEqual(res["missing_roce"], 3)
        self.assertIsNone(res["latest_roce"])
        self.assertEqual(res["roce_trend"], "Insufficient Data")
        self.assertEqual(res["roce_consistency"], "Insufficient Data")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_4_single_valid_roce_observation(self, mock_get_financial_data):
        """4. Single valid ROCE observation."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [None, 15.5, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_roce_observations"], 1)
        self.assertEqual(res["missing_roce"], 2)
        self.assertEqual(res["latest_roce"], 15.5)
        self.assertEqual(res["roce_trend"], "Insufficient Data")
        self.assertEqual(res["roce_consistency"], "Insufficient Data")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_5_partial_roce_values(self, mock_get_financial_data):
        """5. Partial ROCE values: [10.0, NaN, 11.0]."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [10.0, None, 11.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["valid_roce_observations"], 2)
        self.assertEqual(res["missing_roce"], 1)
        self.assertEqual(res["latest_roce"], 11.0)

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_6_all_valid_roce_values(self, mock_get_financial_data):
        """6. All valid ROCE values."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [10.0, 11.0, 12.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["valid_roce_observations"], 3)
        self.assertEqual(res["missing_roce"], 0)

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_7_increasing_roce(self, mock_get_financial_data):
        """7. Increasing ROCE: [10.0, 15.0] -> Improving."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "roce": [10.0, 15.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_trend"], "Improving")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_8_decreasing_roce(self, mock_get_financial_data):
        """8. Decreasing ROCE: [15.0, 10.0] -> Declining."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "roce": [15.0, 10.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_trend"], "Declining")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_9_stable_roce(self, mock_get_financial_data):
        """9. Stable ROCE: [10.0, 11.0] -> Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "roce": [10.0, 11.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_trend"], "Stable")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_10_high_consistency(self, mock_get_financial_data):
        """10. High consistency (sample std <= 2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [10.0, 10.5, 11.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_consistency"], "High")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_11_moderate_consistency(self, mock_get_financial_data):
        """11. Moderate consistency (2.0 < sample std <= 5.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [10.0, 14.0, 17.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_consistency"], "Moderate")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_12_low_consistency(self, mock_get_financial_data):
        """12. Low consistency (sample std > 5.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": [5.0, 25.0, 10.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_consistency"], "Low")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_13_non_numeric_roce(self, mock_get_financial_data):
        """13. Non-numeric ROCE values: ['10.5', 'invalid', '11.0']."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "roce": ["10.5", "invalid", "11.0"]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["valid_roce_observations"], 2)
        self.assertEqual(res["missing_roce"], 1)
        self.assertEqual(res["latest_roce"], 11.0)

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_14_unsorted_quarters(self, mock_get_financial_data):
        """14. Unsorted quarters: verify trend uses chronological order."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-09-30", "2024-03-31", "2024-06-30"],
            "roce": [25.0, 10.0, 15.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        # Chronological order: 2024-03-31 (10.0) -> 2024-06-30 (15.0) -> 2024-09-30 (25.0)
        # Change = 25.0 - 10.0 = +15.0 -> Improving
        self.assertEqual(res["latest_roce"], 25.0)
        self.assertEqual(res["roce_trend"], "Improving")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_15_plus_two_boundary(self, mock_get_financial_data):
        """15. +2.0 boundary: change == +2.0 returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "roce": [10.0, 12.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_trend"], "Stable")

    @patch("backend.logic.roce_analyzer.get_financial_data")
    def test_16_minus_two_boundary(self, mock_get_financial_data):
        """16. -2.0 boundary: change == -2.0 returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "roce": [12.0, 10.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_roce("TEST")
        self.assertEqual(res["roce_trend"], "Stable")


def main():
    """Run test suite directly."""
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("ROCE ANALYZER TEST SUITE")
    print("==========================================")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestROCEAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n🎉 ALL ROCE ANALYZER TESTS PASSED")
    else:
        print("\n❌ SOME TESTS FAILED")


if __name__ == "__main__":
    main()
