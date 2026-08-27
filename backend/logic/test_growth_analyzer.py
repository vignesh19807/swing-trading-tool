"""
Test Growth Analyzer Module
===========================

Unit & Integration tests for Growth Logic Analyzer (backend/logic/growth_analyzer.py).

Verifies:
1. None DataFrame
2. Empty DataFrame
3. All revenue/profit values missing
4. Missing prior-year quarter (returns Insufficient Data)
5. Partial quarters data
6. All valid quarters
7. Improving revenue YoY trend
8. Declining revenue YoY trend
9. Stable revenue YoY trend
10. Turnaround loss to profit
11. Deepening loss
12. Narrowing loss
13. Non-numeric values conversion
14. Unsorted quarters
15. +5.0% boundary
16. -5.0% boundary
17. Symbol normalization
18. Unknown symbol
19. Real execution against INFY, TCS, WIPRO, RELIANCE, HDFCBANK
"""

import unittest
from unittest.mock import patch
import pandas as pd

from backend.logic.growth_analyzer import analyze_growth


class TestGrowthAnalyzer(unittest.TestCase):

    # ============================================================
    # 19. VERIFIED STOCKS EXECUTION
    # ============================================================
    def test_19_verified_stocks_execution(self):
        """Test that analyze_growth runs successfully on all 5 verified stocks."""
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
            res = analyze_growth(symbol)

            # Assert return structure
            self.assertIsInstance(res, dict)
            self.assertIn("symbol", res)
            self.assertIn("status", res)
            self.assertIn("records", res)
            self.assertIn("valid_revenue_observations", res)
            self.assertIn("missing_revenue", res)
            self.assertIn("latest_revenue", res)
            self.assertIn("revenue_yoy_growth", res)
            self.assertIn("revenue_yoy_trend", res)
            self.assertIn("revenue_yoy_consistency", res)
            self.assertIn("revenue_qoq_growth", res)
            self.assertIn("revenue_qoq_trend", res)
            self.assertIn("valid_net_profit_observations", res)
            self.assertIn("missing_net_profit", res)
            self.assertIn("latest_net_profit", res)
            self.assertIn("net_profit_yoy_growth", res)
            self.assertIn("net_profit_yoy_trend", res)
            self.assertIn("net_profit_yoy_consistency", res)
            self.assertIn("net_profit_qoq_growth", res)
            self.assertIn("net_profit_qoq_trend", res)

            # Assert types & values
            self.assertEqual(res["symbol"], symbol)
            self.assertIn(res["status"], allowed_statuses)
            self.assertIsInstance(res["records"], int)
            self.assertIsInstance(res["valid_revenue_observations"], int)
            self.assertIsInstance(res["missing_revenue"], int)

            if res["latest_revenue"] is not None:
                self.assertIsInstance(res["latest_revenue"], (int, float))

            # Specific check for stock statuses per calendar completeness logic:
            if symbol in {"INFY", "TCS", "WIPRO", "RELIANCE"}:
                self.assertEqual(res["status"], "PARTIAL")
            elif symbol == "HDFCBANK":
                self.assertEqual(res["status"], "INSUFFICIENT")
                self.assertIsNone(res["revenue_yoy_growth"])
                self.assertEqual(res["revenue_yoy_trend"], "Insufficient Data")


    # ============================================================
    # 17. SYMBOL NORMALIZATION
    # ============================================================
    def test_17_symbol_normalization(self):
        """Test symbol normalization (uppercase & whitespace trimming)."""
        res = analyze_growth("  infy  ")
        self.assertEqual(res["symbol"], "INFY")
        self.assertIn(res["status"], {"VALID", "PARTIAL", "INSUFFICIENT"})

    # ============================================================
    # 18. UNKNOWN SYMBOL
    # ============================================================
    def test_18_unknown_symbol(self):
        """Test unknown stock symbol returns INSUFFICIENT without crashing."""
        res = analyze_growth("UNKNOWN_STOCK_XYZ")

        self.assertEqual(res["symbol"], "UNKNOWN_STOCK_XYZ")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_revenue_observations"], 0)
        self.assertEqual(res["missing_revenue"], 0)
        self.assertIsNone(res["latest_revenue"])
        self.assertIsNone(res["revenue_yoy_growth"])
        self.assertEqual(res["revenue_yoy_trend"], "Insufficient Data")

    # ============================================================
    # SYNTHETIC EDGE CASE TESTS (MOCKED FINANCIAL SERVICE)
    # ============================================================

    # 1. None DataFrame
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_1_none_dataframe(self, mock_get_financial_data):
        """1. Test behavior when get_financial_data returns None."""
        mock_get_financial_data.return_value = None

        res = analyze_growth("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertIsNone(res["latest_revenue"])

    # 2. Empty DataFrame
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_2_empty_dataframe(self, mock_get_financial_data):
        """2. Test behavior when get_financial_data returns empty DataFrame."""
        mock_get_financial_data.return_value = pd.DataFrame()

        res = analyze_growth("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertIsNone(res["latest_revenue"])

    # 3. All revenue/profit values missing
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_3_all_values_missing(self, mock_get_financial_data):
        """3. Test stock with records but all revenue/profit values missing/None/NaN."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [None, None],
            "net_profit": [None, None]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 2)
        self.assertEqual(res["valid_revenue_observations"], 0)
        self.assertIsNone(res["latest_revenue"])

    # 4. Missing prior-year quarter
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_4_missing_prior_year_quarter(self, mock_get_financial_data):
        """4. Test that latest quarter without exact 12-month prior quarter returns Insufficient Data."""
        mock_df = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30"],
            "revenue": [100.0, 110.0, 120.0],
            "net_profit": [10.0, 11.0, 12.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        # 2025-09-30 target prior year is 2024-09-30 (missing in DB)
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNone(res["revenue_yoy_growth"])
        self.assertEqual(res["revenue_yoy_trend"], "Insufficient Data")
        # QoQ should be available since 2025-06-30 is exact calendar predecessor
        self.assertAlmostEqual(res["revenue_qoq_growth"], 9.0909, places=3)  # (120 - 110) / 110 * 100

    # 5. Partial quarters data
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_5_partial_quarters_data(self, mock_get_financial_data):
        """5. Test partial missing quarters in history yields status PARTIAL if latest YoY exists."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2024-09-30", "2025-06-30"],
            "revenue": [100.0, None, 120.0],
            "net_profit": [10.0, None, 15.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["records"], 3)
        self.assertAlmostEqual(res["revenue_yoy_growth"], 20.0)  # (120 - 100) / 100 * 100
        self.assertEqual(res["revenue_yoy_trend"], "Improving")

    # 6. All valid quarters
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_6_all_valid_quarters(self, mock_get_financial_data):
        """6. Test complete dataset yields status VALID."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30"],
            "revenue": [100.0, 101.0, 101.5, 101.8, 102.0],
            "net_profit": [10.0, 10.1, 10.15, 10.18, 10.2]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertAlmostEqual(res["revenue_yoy_growth"], 2.0)
        self.assertEqual(res["revenue_yoy_trend"], "Stable")


    # 7. Improving revenue YoY trend
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_7_improving_revenue_yoy_trend(self, mock_get_financial_data):
        """7. Test YoY revenue growth > +5.0% returns Improving."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [100.0, 110.0],
            "net_profit": [10.0, 11.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertAlmostEqual(res["revenue_yoy_growth"], 10.0)
        self.assertEqual(res["revenue_yoy_trend"], "Improving")

    # 8. Declining revenue YoY trend
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_8_declining_revenue_yoy_trend(self, mock_get_financial_data):
        """8. Test YoY revenue growth < -5.0% returns Declining."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [100.0, 90.0],
            "net_profit": [10.0, 9.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertAlmostEqual(res["revenue_yoy_growth"], -10.0)
        self.assertEqual(res["revenue_yoy_trend"], "Declining")

    # 9. Stable revenue YoY trend
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_9_stable_revenue_yoy_trend(self, mock_get_financial_data):
        """9. Test YoY revenue growth between -5.0% and +5.0% returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [100.0, 103.0],
            "net_profit": [10.0, 10.3]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertAlmostEqual(res["revenue_yoy_growth"], 3.0)
        self.assertEqual(res["revenue_yoy_trend"], "Stable")

    # 10. Turnaround loss to profit
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_10_turnaround_loss_to_profit(self, mock_get_financial_data):
        """10. Test loss to profit transition: -50 -> +100 = +300% (Improving)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [500.0, 600.0],
            "net_profit": [-50.0, 100.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertAlmostEqual(res["net_profit_yoy_growth"], 300.0)  # (100 - (-50)) / abs(-50) * 100
        self.assertEqual(res["net_profit_yoy_trend"], "Improving")

    # 11. Deepening loss
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_11_deepening_loss(self, mock_get_financial_data):
        """11. Test loss deepening transition: -40 -> -100 = -150% (Declining)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [500.0, 450.0],
            "net_profit": [-40.0, -100.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertAlmostEqual(res["net_profit_yoy_growth"], -150.0)  # (-100 - (-40)) / abs(-40) * 100
        self.assertEqual(res["net_profit_yoy_trend"], "Declining")

    # 12. Narrowing loss
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_12_narrowing_loss(self, mock_get_financial_data):
        """12. Test loss narrowing transition: -100 -> -40 = +60% (Improving)."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [500.0, 550.0],
            "net_profit": [-100.0, -40.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertAlmostEqual(res["net_profit_yoy_growth"], 60.0)  # (-40 - (-100)) / abs(-100) * 100
        self.assertEqual(res["net_profit_yoy_trend"], "Improving")

    # 13. Non-numeric values
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_13_non_numeric_values(self, mock_get_financial_data):
        """13. Test non-numeric string values converted safely to NaN via pd.to_numeric."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": ["invalid", "110.0"],
            "net_profit": ["invalid", "11.0"]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNone(res["revenue_yoy_growth"])

    # 14. Unsorted quarters
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_14_unsorted_quarters(self, mock_get_financial_data):
        """14. Test unsorted quarters are sorted chronologically before exact date matching."""
        mock_df = pd.DataFrame({
            "quarter": ["2025-06-30", "2024-06-30"],
            "revenue": [120.0, 100.0],
            "net_profit": [12.0, 10.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["latest_revenue"], 120.0)
        self.assertAlmostEqual(res["revenue_yoy_growth"], 20.0)

    # 15. +5.0% boundary
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_15_plus_five_boundary(self, mock_get_financial_data):
        """15. Test growth == +5.0% returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [100.0, 105.0],
            "net_profit": [10.0, 10.5]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["revenue_yoy_trend"], "Stable")

    # 16. -5.0% boundary
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_16_minus_five_boundary(self, mock_get_financial_data):
        """16. Test growth == -5.0% returns Stable."""
        mock_df = pd.DataFrame({
            "quarter": ["2024-06-30", "2025-06-30"],
            "revenue": [100.0, 95.0],
            "net_profit": [10.0, 9.5]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        self.assertEqual(res["revenue_yoy_trend"], "Stable")

    # 20. Missing intermediate calendar quarter
    @patch("backend.logic.growth_analyzer.get_financial_data")
    def test_20_missing_intermediate_calendar_quarter(self, mock_get_financial_data):
        """20. Test that missing intermediate calendar quarter (2025-09-30) triggers status PARTIAL."""
        mock_df = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-12-31", "2026-03-31", "2026-06-30"],
            "revenue": [100.0, 110.0, 120.0, 130.0, 140.0],
            "net_profit": [10.0, 11.0, 12.0, 13.0, 14.0]
        })
        mock_get_financial_data.return_value = mock_df

        res = analyze_growth("TEST")
        # Latest quarter (2026-06-30) vs exact YoY quarter (2025-06-30) is valid
        self.assertAlmostEqual(res["revenue_yoy_growth"], 27.2727, places=3)
        self.assertEqual(res["revenue_yoy_trend"], "Improving")
        # Absent intermediate 2025-09-30 calendar quarter must force status PARTIAL
        self.assertEqual(res["status"], "PARTIAL")



def main():
    """Run test suite directly."""
    print("==========================================")
    print("SWING TRADING PLATFORM")
    print("GROWTH ANALYZER TEST SUITE")
    print("==========================================")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGrowthAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nALL GROWTH ANALYZER TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")


if __name__ == "__main__":
    main()
