"""
Test Profit Margin Analyzer Module
===================================

Unit & Integration tests for Profit Margin Logic Analyzer (backend/logic/profit_margin_analyzer.py).

Verifies:
1. None DataFrame
2. Empty DataFrame
3. All margin values missing
4. Single valid observation
5. Partial values
6. All valid values
7. Improving trend
8. Declining trend
9. Stable trend
10. High consistency
11. Moderate consistency
12. Low consistency
13. Non-numeric values
14. Unsorted quarters
15. +2.0 boundary
16. -2.0 boundary
17. Symbol normalization
18. Unknown symbol
19. Real execution against INFY, TCS, WIPRO, RELIANCE, HDFCBANK
"""

import unittest
from unittest.mock import patch
import pandas as pd

from backend.logic.profit_margin_analyzer import analyze_profit_margin


class TestProfitMarginAnalyzer(unittest.TestCase):

    # ============================================================
    # 19. VERIFIED STOCKS EXECUTION
    # ============================================================
    def test_19_verified_stocks_execution(self):
        """Test that analyze_profit_margin runs successfully on all 5 verified stocks."""
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
            res = analyze_profit_margin(symbol)

            # Assert return structure
            self.assertIsInstance(res, dict)
            self.assertIn("symbol", res)
            self.assertIn("status", res)
            self.assertIn("records", res)
            self.assertIn("valid_profit_margin_observations", res)
            self.assertIn("missing_profit_margin", res)
            self.assertIn("latest_profit_margin", res)
            self.assertIn("profit_margin_trend", res)
            self.assertIn("profit_margin_consistency", res)
            self.assertIn("latest_operating_margin", res)
            self.assertIn("operating_margin_trend", res)
            self.assertIn("operating_margin_consistency", res)
            self.assertIn("latest_net_margin", res)
            self.assertIn("net_margin_trend", res)
            self.assertIn("net_margin_consistency", res)

            # Assert types & values
            self.assertEqual(res["symbol"], symbol)
            self.assertIn(res["status"], allowed_statuses)
            self.assertIsInstance(res["records"], int)
            self.assertIsInstance(res["valid_profit_margin_observations"], int)
            self.assertIsInstance(res["missing_profit_margin"], int)

            if res["latest_profit_margin"] is not None:
                self.assertIsInstance(res["latest_profit_margin"], (int, float))

            self.assertIn(res["profit_margin_trend"], allowed_trends)
            self.assertIn(res["profit_margin_consistency"], allowed_consistencies)

    # ============================================================
    # 17. SYMBOL NORMALIZATION
    # ============================================================
    def test_17_symbol_normalization(self):
        """Test symbol normalization (uppercase & whitespace trimming)."""
        res = analyze_profit_margin("  infy  ")
        self.assertEqual(res["symbol"], "INFY")
        self.assertIn(res["status"], {"VALID", "PARTIAL", "INSUFFICIENT"})

    # ============================================================
    # 18. UNKNOWN SYMBOL
    # ============================================================
    def test_18_unknown_symbol(self):
        """Test unknown stock symbol returns INSUFFICIENT without crashing."""
        res = analyze_profit_margin("UNKNOWN_STOCK_XYZ")

        self.assertEqual(res["symbol"], "UNKNOWN_STOCK_XYZ")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_profit_margin_observations"], 0)
        self.assertEqual(res["missing_profit_margin"], 0)
        self.assertIsNone(res["latest_profit_margin"])
        self.assertEqual(res["profit_margin_trend"], "Insufficient Data")
        self.assertEqual(res["profit_margin_consistency"], "Insufficient Data")

    # ============================================================
    # SYNTHETIC EDGE CASE TESTS (MOCKED FINANCIAL SERVICE)
    # ============================================================

    # 1. None DataFrame
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_1_none_dataframe(self, mock_get_financial_data):
        """1. Test behavior when get_financial_data returns None."""
        mock_get_financial_data.return_value = None

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_profit_margin_observations"], 0)
        self.assertIsNone(res["latest_profit_margin"])

    # 2. Empty DataFrame
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_2_empty_dataframe(self, mock_get_financial_data):
        """2. Test behavior when get_financial_data returns empty DataFrame."""
        mock_get_financial_data.return_value = pd.DataFrame()

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_profit_margin_observations"], 0)
        self.assertIsNone(res["latest_profit_margin"])

    # 3. All margin values missing
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_3_all_margin_missing(self, mock_get_financial_data):
        """3. Test stock with records but all margin values missing/None/NaN."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [None, None, None],
            "net_margin": [None, None, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_profit_margin_observations"], 0)
        self.assertEqual(res["missing_profit_margin"], 3)
        self.assertIsNone(res["latest_profit_margin"])
        self.assertEqual(res["profit_margin_trend"], "Insufficient Data")
        self.assertEqual(res["profit_margin_consistency"], "Insufficient Data")

    # 4. Single valid observation
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_4_single_valid_observation(self, mock_get_financial_data):
        """4. Test stock with only 1 valid margin observation."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [None, 20.0, None],
            "net_margin": [None, 15.0, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_profit_margin_observations"], 1)
        self.assertEqual(res["missing_profit_margin"], 2)
        self.assertEqual(res["latest_profit_margin"], 20.0)
        self.assertEqual(res["profit_margin_trend"], "Insufficient Data")
        self.assertEqual(res["profit_margin_consistency"], "Insufficient Data")

    # 5. Partial values
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_5_partial_values(self, mock_get_financial_data):
        """5. Test partial margin values: [15.0, None, 20.0]."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [15.0, None, 20.0],
            "net_margin": [10.0, None, 14.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_profit_margin_observations"], 2)
        self.assertEqual(res["missing_profit_margin"], 1)
        self.assertEqual(res["latest_profit_margin"], 20.0)
        self.assertEqual(res["profit_margin_trend"], "Improving")  # 20.0 - 15.0 = +5.0 (> +2.0)

    # 6. All valid values
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_6_all_valid_values(self, mock_get_financial_data):
        """6. Test every record contains a valid margin value."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [21.0, 22.0, 21.5],
            "net_margin": [16.0, 16.5, 16.2]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_profit_margin_observations"], 3)
        self.assertEqual(res["missing_profit_margin"], 0)
        self.assertEqual(res["latest_profit_margin"], 21.5)

    # 7. Improving trend
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_7_improving_trend(self, mock_get_financial_data):
        """7. Test margin trend classified as Improving (change > +2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [10.0, 12.5, 14.0],
            "net_margin": [8.0, 10.0, 11.5]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["latest_profit_margin"], 14.0)
        self.assertEqual(res["profit_margin_trend"], "Improving")  # 14.0 - 10.0 = +4.0

    # 8. Declining trend
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_8_declining_trend(self, mock_get_financial_data):
        """8. Test margin trend classified as Declining (change < -2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [20.0, 17.5, 15.0],
            "net_margin": [15.0, 12.5, 10.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["latest_profit_margin"], 15.0)
        self.assertEqual(res["profit_margin_trend"], "Declining")  # 15.0 - 20.0 = -5.0

    # 9. Stable trend
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_9_stable_trend(self, mock_get_financial_data):
        """9. Test margin trend classified as Stable (-2.0 <= change <= 2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [20.0, 20.5, 21.0],
            "net_margin": [15.0, 15.2, 15.5]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["profit_margin_trend"], "Stable")  # 21.0 - 20.0 = +1.0

    # 10. High consistency
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_10_high_consistency(self, mock_get_financial_data):
        """10. Test High consistency classification (std <= 2.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [20.0, 20.5, 21.0],
            "net_margin": [15.0, 15.5, 16.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["profit_margin_consistency"], "High")

    # 11. Moderate consistency
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_11_moderate_consistency(self, mock_get_financial_data):
        """11. Test Moderate consistency classification (2.0 < std <= 5.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [15.0, 20.0, 23.0],
            "net_margin": [10.0, 14.0, 17.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["profit_margin_consistency"], "Moderate")

    # 12. Low consistency
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_12_low_consistency(self, mock_get_financial_data):
        """12. Test Low consistency classification (std > 5.0)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": [10.0, 30.0, 15.0],
            "net_margin": [5.0, 25.0, 10.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["profit_margin_consistency"], "Low")

    # 13. Non-numeric values
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_13_non_numeric_values(self, mock_get_financial_data):
        """13. Test that non-numeric margin strings are converted to NaN safely."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30"],
            "operating_margin": ["invalid", "20.0", "22.5"],
            "net_margin": ["invalid", "15.0", "17.0"]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertEqual(res["valid_profit_margin_observations"], 2)
        self.assertEqual(res["missing_profit_margin"], 1)
        self.assertEqual(res["latest_profit_margin"], 22.5)

    # 14. Unsorted quarters
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_14_unsorted_quarters(self, mock_get_financial_data):
        """14. Test that data is sorted chronologically before identifying latest margin and trend."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-09-30", "2024-03-31", "2024-06-30"],
            "operating_margin": [25.0, 15.0, 20.0],
            "net_margin": [20.0, 10.0, 15.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        # Earliest (2024-03-31) = 15.0, Latest (2024-09-30) = 25.0
        # Change = 25.0 - 15.0 = +10.0 (> +2.0) -> Improving
        self.assertEqual(res["latest_profit_margin"], 25.0)
        self.assertEqual(res["profit_margin_trend"], "Improving")

    # 15. +2.0 boundary
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_15_plus_two_boundary(self, mock_get_financial_data):
        """15. Test +2.0 boundary: change == +2.0 returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "operating_margin": [20.0, 22.0],
            "net_margin": [15.0, 17.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        # Change = 22.0 - 20.0 = +2.0
        self.assertEqual(res["profit_margin_trend"], "Stable")

    # 16. -2.0 boundary
    @patch("backend.logic.profit_margin_analyzer.get_financial_data")
    def test_16_minus_two_boundary(self, mock_get_financial_data):
        """16. Test -2.0 boundary: change == -2.0 returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30"],
            "operating_margin": [22.0, 20.0],
            "net_margin": [17.0, 15.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_profit_margin("TEST")
        # Change = 20.0 - 22.0 = -2.0
        self.assertEqual(res["profit_margin_trend"], "Stable")


def main():
    """Run test suite directly."""
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("PROFIT MARGIN ANALYZER TEST SUITE")
    print("==========================================")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestProfitMarginAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nALL PROFIT MARGIN ANALYZER TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")


if __name__ == "__main__":
    main()
