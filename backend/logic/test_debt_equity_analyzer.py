"""
Test Debt/Equity Analyzer Module
================================

Unit & Integration tests for Debt/Equity Logic Analyzer (backend/logic/debt_equity_analyzer.py).

Verifies:
1. None DataFrame
2. Empty DataFrame
3. All debt_equity values missing
4. Single valid observation
5. Partial debt_equity values
6. All valid debt_equity values
7. Improving trend
8. Declining trend
9. Stable trend
10. High consistency
11. Moderate consistency
12. Low consistency
13. Non-numeric debt_equity conversion
14. Unsorted quarters
15. +2.0 trend boundary
16. -2.0 trend boundary
17. Symbol normalization
18. Unknown symbol
19. Verified-stock execution (INFY, TCS, WIPRO, RELIANCE, HDFCBANK)
"""

import unittest
from unittest.mock import patch
import pandas as pd

from backend.logic.debt_equity_analyzer import analyze_debt_equity


class TestDebtEquityAnalyzer(unittest.TestCase):

    # ============================================================
    # 19. VERIFIED STOCKS EXECUTION
    # ============================================================
    def test_19_verified_stocks_execution(self):
        """Test that analyze_debt_equity runs successfully on all 5 verified stocks."""
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
            res = analyze_debt_equity(symbol)

            # Assert return structure
            self.assertIsInstance(res, dict)
            self.assertIn("symbol", res)
            self.assertIn("status", res)
            self.assertIn("records", res)
            self.assertIn("valid_debt_equity_observations", res)
            self.assertIn("missing_debt_equity", res)
            self.assertIn("latest_debt_equity", res)
            self.assertIn("debt_equity_trend", res)
            self.assertIn("debt_equity_consistency", res)

            # Assert types & values
            self.assertEqual(res["symbol"], symbol)
            self.assertIn(res["status"], allowed_statuses)
            self.assertIsInstance(res["records"], int)
            self.assertIsInstance(res["valid_debt_equity_observations"], int)
            self.assertIsInstance(res["missing_debt_equity"], int)

            if res["latest_debt_equity"] is not None:
                self.assertIsInstance(res["latest_debt_equity"], (int, float))

            self.assertIn(res["debt_equity_trend"], allowed_trends)
            self.assertIn(res["debt_equity_consistency"], allowed_consistencies)

    # ============================================================
    # 17. SYMBOL NORMALIZATION
    # ============================================================
    def test_17_symbol_normalization(self):
        """Test symbol normalization (uppercase & whitespace trimming)."""
        res = analyze_debt_equity("  infy  ")
        self.assertEqual(res["symbol"], "INFY")
        self.assertIn(res["status"], {"VALID", "PARTIAL", "INSUFFICIENT"})

    # ============================================================
    # 18. UNKNOWN SYMBOL
    # ============================================================
    def test_18_unknown_symbol(self):
        """Test unknown stock symbol returns INSUFFICIENT without crashing."""
        res = analyze_debt_equity("UNKNOWN_STOCK_XYZ")

        self.assertEqual(res["symbol"], "UNKNOWN_STOCK_XYZ")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_debt_equity_observations"], 0)
        self.assertEqual(res["missing_debt_equity"], 0)
        self.assertIsNone(res["latest_debt_equity"])
        self.assertEqual(res["debt_equity_trend"], "Insufficient Data")
        self.assertEqual(res["debt_equity_consistency"], "Insufficient Data")

    # ============================================================
    # SYNTHETIC EDGE CASE TESTS (MOCKED FINANCIAL SERVICE)
    # ============================================================

    # 1. None DataFrame
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_1_none_dataframe(self, mock_get_financial_data):
        """1. Test behavior when get_financial_data returns None."""
        mock_get_financial_data.return_value = None

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_debt_equity_observations"], 0)
        self.assertIsNone(res["latest_debt_equity"])

    # 2. Empty DataFrame
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_2_empty_dataframe(self, mock_get_financial_data):
        """2. Test behavior when get_financial_data returns empty DataFrame."""
        mock_get_financial_data.return_value = pd.DataFrame()

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_debt_equity_observations"], 0)
        self.assertIsNone(res["latest_debt_equity"])

    # 3. All debt_equity values missing
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_3_all_debt_equity_missing(self, mock_get_financial_data):
        """3. Test stock with records but all debt_equity values missing/None/NaN."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [None, None, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_debt_equity_observations"], 0)
        self.assertEqual(res["missing_debt_equity"], 3)
        self.assertIsNone(res["latest_debt_equity"])
        self.assertEqual(res["debt_equity_trend"], "Insufficient Data")
        self.assertEqual(res["debt_equity_consistency"], "Insufficient Data")

    # 4. Single valid observation
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_4_single_valid_observation(self, mock_get_financial_data):
        """4. Test stock with only 1 valid debt_equity observation."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [None, 1.5, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_debt_equity_observations"], 1)
        self.assertEqual(res["missing_debt_equity"], 2)
        self.assertEqual(res["latest_debt_equity"], 1.5)
        self.assertEqual(res["debt_equity_trend"], "Insufficient Data")
        self.assertEqual(res["debt_equity_consistency"], "Insufficient Data")

    # 5. Partial debt_equity values
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_5_partial_debt_equity_values(self, mock_get_financial_data):
        """5. Test partial debt_equity values: [3.0, None, 0.5]."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [3.0, None, 0.5]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_debt_equity_observations"], 2)
        self.assertEqual(res["missing_debt_equity"], 1)
        self.assertEqual(res["latest_debt_equity"], 0.5)
        self.assertEqual(res["debt_equity_trend"], "Improving")  # 0.5 - 3.0 = -2.5 (< -2.0)

    # 6. All valid debt_equity values
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_6_all_valid_debt_equity_values(self, mock_get_financial_data):
        """6. Test every record contains a valid debt_equity value."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [1.0, 1.2, 1.1]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_debt_equity_observations"], 3)
        self.assertEqual(res["missing_debt_equity"], 0)
        self.assertEqual(res["latest_debt_equity"], 1.1)

    # 7. Improving trend
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_7_improving_trend(self, mock_get_financial_data):
        """7. Test Debt/Equity trend classified as Improving (change < -2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [5.0, 3.5, 2.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["latest_debt_equity"], 2.0)
        self.assertEqual(res["debt_equity_trend"], "Improving")  # 2.0 - 5.0 = -3.0

    # 8. Declining trend
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_8_declining_trend(self, mock_get_financial_data):
        """8. Test Debt/Equity trend classified as Declining (change > +2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [1.0, 2.5, 4.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["latest_debt_equity"], 4.0)
        self.assertEqual(res["debt_equity_trend"], "Declining")  # 4.0 - 1.0 = +3.0

    # 9. Stable trend
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_9_stable_trend(self, mock_get_financial_data):
        """9. Test Debt/Equity trend classified as Stable (-2.0 <= change <= 2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [1.0, 1.5, 2.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["debt_equity_trend"], "Stable")  # 2.0 - 1.0 = +1.0

    # 10. High consistency
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_10_high_consistency(self, mock_get_financial_data):
        """10. Test High consistency classification (std <= 2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [1.0, 1.5, 2.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["debt_equity_consistency"], "High")

    # 11. Moderate consistency
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_11_moderate_consistency(self, mock_get_financial_data):
        """11. Test Moderate consistency classification (2.0 < std <= 5.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [1.0, 5.0, 8.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["debt_equity_consistency"], "Moderate")

    # 12. Low consistency
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_12_low_consistency(self, mock_get_financial_data):
        """12. Test Low consistency classification (std > 5.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": [1.0, 15.0, 2.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["debt_equity_consistency"], "Low")

    # 13. Non-numeric debt_equity conversion
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_13_non_numeric_debt_equity_conversion(self, mock_get_financial_data):
        """13. Test that non-numeric debt_equity strings are converted to NaN safely."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "debt_equity": ["invalid", "2.0", "1.5"]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_debt_equity_observations"], 2)
        self.assertEqual(res["missing_debt_equity"], 1)
        self.assertEqual(res["latest_debt_equity"], 1.5)

    # 14. Unsorted quarters
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_14_unsorted_quarters(self, mock_get_financial_data):
        """14. Test that data is sorted chronologically before identifying latest D/E and trend."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-09-30", "2024-03-31", "2024-06-30"],
            "debt_equity": [1.0, 5.0, 3.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        # Earliest (2024-03-31) = 5.0, Latest (2024-09-30) = 1.0
        # Change = 1.0 - 5.0 = -4.0 (< -2.0) -> Improving
        self.assertEqual(res["latest_debt_equity"], 1.0)
        self.assertEqual(res["debt_equity_trend"], "Improving")

    # 15. +2.0 trend boundary
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_15_plus_two_boundary(self, mock_get_financial_data):
        """15. Test +2.0 boundary: change == +2.0 returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "debt_equity": [1.0, 3.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        # Change = 3.0 - 1.0 = +2.0
        self.assertEqual(res["debt_equity_trend"], "Stable")

    # 16. -2.0 trend boundary
    @patch("backend.logic.debt_equity_analyzer.get_financial_data")
    def test_16_minus_two_boundary(self, mock_get_financial_data):
        """16. Test -2.0 boundary: change == -2.0 returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "debt_equity": [3.0, 1.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_debt_equity("TEST")
        # Change = 1.0 - 3.0 = -2.0
        self.assertEqual(res["debt_equity_trend"], "Stable")


def main():
    """Run test suite directly."""
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("DEBT/EQUITY ANALYZER TEST SUITE")
    print("==========================================")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDebtEquityAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nALL DEBT/EQUITY ANALYZER TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")


if __name__ == "__main__":
    main()
