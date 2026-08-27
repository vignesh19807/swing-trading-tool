"""
Test Valuation Analyzer Module
==============================

Unit & Integration tests for Valuation Logic Analyzer (backend/logic/valuation_analyzer.py).

Verifies:
1. None financial DataFrame
2. Empty financial DataFrame
3. Fewer than 4 valid EPS observations
4. Exactly 4 valid EPS observations
5. More than 4 quarters
6. Missing EPS values (NaN EPS)
7. Non-numeric EPS coercion
8. Duplicate quarters handling
9. Unsorted quarters handling
10. Symbol normalization
11. Invalid/missing market data
12. Zero/negative market price
13. Positive TTM EPS & P/E calculation
14. Earnings yield calculation
15. Negative TTM EPS handling
16. Zero TTM EPS handling
17. Undervalued threshold (< 15.0)
18. Fairly Valued lower boundary (== 15.0)
19. Fairly Valued upper boundary (== 25.0)
20. Overvalued threshold (> 25.0)
21. INFY unit mismatch handling (mocked)
22. TCS real-data integration
23. WIPRO real-data integration
24. RELIANCE real-data integration
25. INFY real-data integration
26. HDFCBANK real-data integration
"""

import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np

from backend.logic.valuation_analyzer import analyze_valuation


class TestValuationAnalyzer(unittest.TestCase):

    # Helper mock market DataFrame
    def _create_mock_market_df(self, close_price=100.0):
        return pd.DataFrame({
            "date": ["2026-08-14"],
            "open": [99.0],
            "high": [101.0],
            "low": [98.5],
            "close": [close_price],
            "volume": [1000000]
        })

    # ============================================================
    # TEST 1 — NONE FINANCIAL DATAFRAME
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_01_none_financial_dataframe(self, mock_stock, mock_fin):
        mock_fin.return_value = None
        mock_stock.return_value = self._create_mock_market_df(100.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["symbol"], "TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertEqual(res["valid_eps_observations"], 0)
        self.assertEqual(res["missing_eps_observations"], 0)
        self.assertIsNone(res["latest_close"])
        self.assertIsNone(res["ttm_eps"])
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # TEST 2 — EMPTY FINANCIAL DATAFRAME
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_02_empty_financial_dataframe(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame()
        mock_stock.return_value = self._create_mock_market_df(100.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 0)
        self.assertIsNone(res["ttm_eps"])
        self.assertIsNone(res["pe_ratio"])

    # ============================================================
    # TEST 3 — FEWER THAN 4 VALID EPS OBSERVATIONS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_03_fewer_than_4_valid_eps_observations(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30"],
            "eps": [5.0, 6.0, 7.0]
        })
        mock_stock.return_value = self._create_mock_market_df(100.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["valid_eps_observations"], 3)
        self.assertIsNone(res["ttm_eps"])
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # TEST 4 — EXACTLY 4 VALID EPS OBSERVATIONS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_04_exactly_4_valid_eps_observations(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [10.0, 10.0, 10.0, 10.0]
        })
        mock_stock.return_value = self._create_mock_market_df(400.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["records"], 4)
        self.assertEqual(res["valid_eps_observations"], 4)
        self.assertEqual(res["ttm_eps"], 40.0)
        self.assertEqual(res["pe_ratio"], 10.0)
        self.assertEqual(res["earnings_yield"], 10.0)
        self.assertEqual(res["valuation_classification"], "Undervalued")

    # ============================================================
    # TEST 5 — MORE THAN 4 QUARTERS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_05_more_than_4_quarters(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30"],
            "eps": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        })
        mock_stock.return_value = self._create_mock_market_df(360.0)

        res = analyze_valuation("TEST")
        # Sum of latest 4 quarters (3.0 + 4.0 + 5.0 + 6.0 = 18.0)
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["records"], 6)
        self.assertEqual(res["valid_eps_observations"], 6)
        self.assertEqual(res["ttm_eps"], 18.0)
        self.assertEqual(res["pe_ratio"], 20.0)
        self.assertEqual(res["valuation_classification"], "Fairly Valued")

    # ============================================================
    # TEST 6 — MISSING EPS VALUES (NaN EPS)
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_06_missing_eps_values(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [np.nan, 10.0, 10.0, np.nan, 10.0]
        })
        mock_stock.return_value = self._create_mock_market_df(300.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["records"], 5)
        self.assertEqual(res["valid_eps_observations"], 3)
        self.assertEqual(res["missing_eps_observations"], 2)
        self.assertIsNone(res["ttm_eps"])

    # ============================================================
    # TEST 7 — NON-NUMERIC EPS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_07_non_numeric_eps(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [10.0, "invalid", 10.0, 10.0]
        })
        mock_stock.return_value = self._create_mock_market_df(200.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["valid_eps_observations"], 3)
        self.assertEqual(res["missing_eps_observations"], 1)
        self.assertIsNone(res["ttm_eps"])

    # ============================================================
    # TEST 8 — DUPLICATE QUARTERS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_08_duplicate_quarters(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [5.0, 1.0, 5.0, 5.0, 5.0]
        })
        mock_stock.return_value = self._create_mock_market_df(200.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["valid_eps_observations"], 4)
        self.assertEqual(res["ttm_eps"], 20.0)

    # ============================================================
    # TEST 9 — UNSORTED QUARTERS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_09_unsorted_quarters(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-12-31", "2025-03-31", "2025-09-30", "2025-06-30"],
            "eps": [4.0, 1.0, 3.0, 2.0]
        })
        mock_stock.return_value = self._create_mock_market_df(100.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["ttm_eps"], 10.0)
        self.assertEqual(res["pe_ratio"], 10.0)

    # ============================================================
    # TEST 10 — SYMBOL NORMALIZATION
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_10_symbol_normalization(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [5.0, 5.0, 5.0, 5.0]
        })
        mock_stock.return_value = self._create_mock_market_df(300.0)

        res = analyze_valuation("  tcs  ")
        self.assertEqual(res["symbol"], "TCS")

    # ============================================================
    # TEST 11 — INVALID / MISSING MARKET DATA
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_11_invalid_missing_market_data(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [5.0, 5.0, 5.0, 5.0]
        })
        mock_stock.return_value = None

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["ttm_eps"], 20.0)
        self.assertIsNone(res["latest_close"])
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # TEST 12 — ZERO / NEGATIVE MARKET PRICE
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_12_zero_market_price(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [5.0, 5.0, 5.0, 5.0]
        })
        mock_stock.return_value = pd.DataFrame({
            "date": ["2026-08-14"],
            "close": [0.0]
        })

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNone(res["latest_close"])
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])

    # ============================================================
    # TEST 13 — POSITIVE TTM EPS & P/E CALCULATION
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_13_positive_ttm_eps_pe_calculation(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [2.5, 2.5, 2.5, 2.5]
        })
        mock_stock.return_value = self._create_mock_market_df(150.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["ttm_eps"], 10.0)
        self.assertEqual(res["latest_close"], 150.0)
        self.assertEqual(res["pe_ratio"], 15.0)
        self.assertEqual(res["earnings_yield"], 6.6667)
        self.assertEqual(res["valuation_classification"], "Fairly Valued")

    # ============================================================
    # TEST 14 — EARNINGS YIELD CALCULATION
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_14_earnings_yield_calculation(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [2.5, 2.5, 2.5, 2.5]
        })
        mock_stock.return_value = self._create_mock_market_df(200.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["ttm_eps"], 10.0)
        self.assertEqual(res["latest_close"], 200.0)
        self.assertEqual(res["pe_ratio"], 20.0)
        self.assertEqual(res["earnings_yield"], 5.0)

    # ============================================================
    # TEST 15 — NEGATIVE TTM EPS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_15_negative_ttm_eps(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [-1.0, -2.0, -1.0, -1.0]
        })
        mock_stock.return_value = self._create_mock_market_df(100.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["ttm_eps"], -5.0)
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Unprofitable")

    # ============================================================
    # TEST 16 — ZERO TTM EPS
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_16_zero_ttm_eps(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [0.0, 0.0, 0.0, 0.0]
        })
        mock_stock.return_value = self._create_mock_market_df(100.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["ttm_eps"], 0.0)
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # TEST 17 — UNDERVALUED THRESHOLD (< 15.0)
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_17_undervalued_threshold(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [2.5, 2.5, 2.5, 2.5]
        })
        mock_stock.return_value = self._create_mock_market_df(140.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["pe_ratio"], 14.0)
        self.assertEqual(res["valuation_classification"], "Undervalued")

    # ============================================================
    # TEST 18 — FAIRLY VALUED LOWER BOUNDARY (== 15.0)
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_18_fairly_valued_lower_boundary(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [2.5, 2.5, 2.5, 2.5]
        })
        mock_stock.return_value = self._create_mock_market_df(150.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["pe_ratio"], 15.0)
        self.assertEqual(res["valuation_classification"], "Fairly Valued")

    # ============================================================
    # TEST 19 — FAIRLY VALUED UPPER BOUNDARY (== 25.0)
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_19_fairly_valued_upper_boundary(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [2.5, 2.5, 2.5, 2.5]
        })
        mock_stock.return_value = self._create_mock_market_df(250.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["pe_ratio"], 25.0)
        self.assertEqual(res["valuation_classification"], "Fairly Valued")

    # ============================================================
    # TEST 20 — OVERVALUED THRESHOLD (> 25.0)
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_20_overvalued_threshold(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"],
            "eps": [2.5, 2.5, 2.5, 2.5]
        })
        mock_stock.return_value = self._create_mock_market_df(260.0)

        res = analyze_valuation("TEST")
        self.assertEqual(res["pe_ratio"], 26.0)
        self.assertEqual(res["valuation_classification"], "Overvalued")

    # ============================================================
    # TEST 21 — INFY UNIT MISMATCH (MOCKED)
    # ============================================================
    @patch("backend.logic.valuation_analyzer.get_financial_data")
    @patch("backend.logic.valuation_analyzer.get_stock_data")
    def test_21_infy_unit_mismatch(self, mock_stock, mock_fin):
        mock_fin.return_value = pd.DataFrame({
            "quarter": ["2025-06-30", "2025-12-31", "2026-03-31", "2026-06-30"],
            "eps": [0.19, 0.18, 0.23, 0.20]
        })
        mock_stock.return_value = self._create_mock_market_df(1169.20)

        res = analyze_valuation("INFY")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["ttm_eps"], 0.80)
        self.assertEqual(res["latest_close"], 1169.20)
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # TEST 22 — TCS REAL-DATA INTEGRATION
    # ============================================================
    def test_22_tcs_real_data_integration(self):
        res = analyze_valuation("TCS")
        self.assertEqual(res["symbol"], "TCS")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["ttm_eps"], 139.56)
        self.assertEqual(res["pe_ratio"], 16.9175)
        self.assertEqual(res["earnings_yield"], 5.9111)
        self.assertEqual(res["valuation_classification"], "Fairly Valued")

    # ============================================================
    # TEST 23 — WIPRO REAL-DATA INTEGRATION
    # ============================================================
    def test_23_wipro_real_data_integration(self):
        res = analyze_valuation("WIPRO")
        self.assertEqual(res["symbol"], "WIPRO")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["ttm_eps"], 12.67)
        self.assertEqual(res["pe_ratio"], 14.5225)
        self.assertEqual(res["earnings_yield"], 6.8859)
        self.assertEqual(res["valuation_classification"], "Undervalued")

    # ============================================================
    # TEST 24 — RELIANCE REAL-DATA INTEGRATION
    # ============================================================
    def test_24_reliance_real_data_integration(self):
        res = analyze_valuation("RELIANCE")
        self.assertEqual(res["symbol"], "RELIANCE")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["ttm_eps"], 61.75)
        self.assertEqual(res["pe_ratio"], 21.2146)
        self.assertEqual(res["earnings_yield"], 4.7137)
        self.assertEqual(res["valuation_classification"], "Fairly Valued")

    # ============================================================
    # TEST 25 — INFY REAL-DATA INTEGRATION
    # ============================================================
    def test_25_infy_real_data_integration(self):
        res = analyze_valuation("INFY")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["ttm_eps"], 0.80)
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # TEST 26 — HDFCBANK REAL-DATA INTEGRATION
    # ============================================================
    def test_26_hdfcbank_real_data_integration(self):
        res = analyze_valuation("HDFCBANK")
        self.assertEqual(res["symbol"], "HDFCBANK")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["valid_eps_observations"], 2)
        self.assertIsNone(res["ttm_eps"])
        self.assertIsNone(res["pe_ratio"])
        self.assertIsNone(res["earnings_yield"])
        self.assertEqual(res["valuation_classification"], "Insufficient Data")

    # ============================================================
    # OUTPUT CONTRACT & PRECISION TEST
    # ============================================================
    def test_output_contract_and_types(self):
        res = analyze_valuation("TCS")
        expected_keys = {
            "symbol",
            "status",
            "records",
            "valid_eps_observations",
            "missing_eps_observations",
            "latest_close",
            "ttm_eps",
            "pe_ratio",
            "earnings_yield",
            "valuation_classification"
        }
        self.assertEqual(set(res.keys()), expected_keys)
        self.assertIsInstance(res["symbol"], str)
        self.assertIsInstance(res["status"], str)
        self.assertIsInstance(res["records"], int)
        self.assertIsInstance(res["valid_eps_observations"], int)
        self.assertIsInstance(res["missing_eps_observations"], int)
        self.assertIsInstance(res["valuation_classification"], str)


if __name__ == "__main__":
    unittest.main()
