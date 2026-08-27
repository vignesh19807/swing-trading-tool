"""
Decision Engine V1 Test Suite
=============================

Unit and integration tests for Engine 7 (Decision Engine / Opportunity Score V1).

Coverage:
1. Momentum Score derivation & boundaries (0 - 100)
2. Opportunity Score 40/35/25 weighting & 4-decimal precision
3. Missing momentum dynamic re-weighting fallback
4. Missing core component blocking (Financial or Technical is None)
5. Recommendation threshold boundaries (BUY, WATCH, HOLD, AVOID, INSUFFICIENT_DATA)
6. Aggregate Status propagation (VALID, PARTIAL, INSUFFICIENT)
7. Symbol normalization & Exception safety
8. Live reference stock integration tests (TCS, WIPRO, RELIANCE, INFY, HDFCBANK)

Author: Logic Engineer
"""

import unittest
from unittest.mock import patch
import pandas as pd

from backend.engines.decision_engine import calculate_opportunity_score


class TestDecisionEngineUnit(unittest.TestCase):
    """Unit tests for pure Decision Engine calculation logic."""

    # -------------------------------------------------------------------------
    # 1. MOMENTUM SCORE DERIVATION TESTS
    # -------------------------------------------------------------------------
    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_momentum_derivation_max_boundary(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Verify momentum score is 100.0 when RSI=30 and MACD=30."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [30.0],
                "macd_score": [30.0],
                "trend_score": [20.0],
                "volume_score": [20.0],
                "technical_score": [100.0]
            })
        }
        mock_fin.return_value = {"overall_score": 100.0, "status": "VALID"}

        res = calculate_opportunity_score("TEST")
        self.assertEqual(res["momentum_score"], 100.0)
        self.assertEqual(res["opportunity_score"], 100.0)
        self.assertEqual(res["recommendation"], "BUY")
        self.assertEqual(res["status"], "VALID")

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_momentum_derivation_min_boundary(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Verify momentum score is 0.0 when RSI=0 and MACD=0."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [0.0],
                "macd_score": [0.0],
                "trend_score": [0.0],
                "volume_score": [0.0],
                "technical_score": [0.0]
            })
        }
        mock_fin.return_value = {"overall_score": 0.0, "status": "VALID"}

        res = calculate_opportunity_score("TEST")
        self.assertEqual(res["momentum_score"], 0.0)
        self.assertEqual(res["opportunity_score"], 0.0)
        self.assertEqual(res["recommendation"], "AVOID")
        self.assertEqual(res["status"], "VALID")

    # -------------------------------------------------------------------------
    # 2. OPPORTUNITY FORMULA & DYNAMIC RE-WEIGHTING TESTS
    # -------------------------------------------------------------------------
    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_opportunity_score_formula_precision(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Verify 40/35/25 weighting formula and 4-decimal precision."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [30.0],
                "macd_score": [8.0],
                "trend_score": [15.0],
                "volume_score": [3.0],
                "technical_score": [56.0]
            })
        }
        mock_fin.return_value = {"overall_score": 82.0358, "status": "VALID"}

        # Tech = 56.0 * 0.40 = 22.40
        # Fin  = 82.0358 * 0.35 = 28.71253
        # Mom  = ((38/60)*100 = 63.333333...) * 0.25 = 15.833333...
        # Sum  = 66.945863... -> round(4) = 66.9459
        res = calculate_opportunity_score("TEST")
        self.assertEqual(res["momentum_score"], 63.3333)
        self.assertEqual(res["opportunity_score"], 66.9459)
        self.assertEqual(res["recommendation"], "WATCH")

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_momentum_missing_fallback_reweighting(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Verify dynamic re-weighting when momentum is missing (Tech 53.33%, Fin 46.67%)."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        # Missing RSI/MACD sub-scores
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [None],
                "macd_score": [None],
                "trend_score": [20.0],
                "volume_score": [20.0],
                "technical_score": [40.0]
            })
        }
        mock_fin.return_value = {"overall_score": 80.0, "status": "VALID"}

        # Effective Tech Wt = 0.40 / 0.75 = 0.5333333333333333
        # Effective Fin Wt  = 0.35 / 0.75 = 0.4666666666666667
        # Opp = 40.0 * 0.5333333333 + 80.0 * 0.4666666667 = 21.333333 + 37.333333 = 58.6667
        res = calculate_opportunity_score("TEST")
        self.assertIsNone(res["momentum_score"])
        self.assertEqual(res["opportunity_score"], 58.6667)
        self.assertEqual(res["recommendation"], "HOLD")
        self.assertEqual(res["status"], "PARTIAL")

    # -------------------------------------------------------------------------
    # 3. RECOMMENDATION BOUNDARY TESTS
    # -------------------------------------------------------------------------
    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_recommendation_boundaries(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Test exact recommendation boundary cutoffs (BUY >= 75, WATCH >= 60, HOLD >= 45, AVOID < 45)."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})

        # 1. Boundary 75.0000 -> BUY
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [30.0], "macd_score": [15.0], "trend_score": [15.0], "volume_score": [15.0],
                "technical_score": [75.0]
            })
        }
        mock_fin.return_value = {"overall_score": 75.0, "status": "VALID"}
        res = calculate_opportunity_score("TEST")
        self.assertEqual(res["opportunity_score"], 75.0)
        self.assertEqual(res["recommendation"], "BUY")

        # 2. Boundary 60.0000 -> WATCH
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [18.0], "macd_score": [18.0], "trend_score": [12.0], "volume_score": [12.0],
                "technical_score": [60.0]
            })
        }
        mock_fin.return_value = {"overall_score": 60.0, "status": "VALID"}
        res = calculate_opportunity_score("TEST")
        self.assertEqual(res["opportunity_score"], 60.0)
        self.assertEqual(res["recommendation"], "WATCH")

        # 3. Boundary 45.0000 -> HOLD
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [13.5], "macd_score": [13.5], "trend_score": [9.0], "volume_score": [9.0],
                "technical_score": [45.0]
            })
        }
        mock_fin.return_value = {"overall_score": 45.0, "status": "VALID"}
        res = calculate_opportunity_score("TEST")
        self.assertEqual(res["opportunity_score"], 45.0)
        self.assertEqual(res["recommendation"], "HOLD")

        # 4. Boundary 44.9999 -> AVOID
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [13.5], "macd_score": [13.4997], "trend_score": [9.0], "volume_score": [9.0],
                "technical_score": [44.9997]
            })
        }
        mock_fin.return_value = {"overall_score": 44.9999, "status": "VALID"}
        res = calculate_opportunity_score("TEST")
        self.assertLess(res["opportunity_score"], 45.0)
        self.assertEqual(res["recommendation"], "AVOID")

    # -------------------------------------------------------------------------
    # 4. MISSING CORE COMPONENT TESTS
    # -------------------------------------------------------------------------
    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_missing_financial_score_blocks_calculation(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Verify missing financial score blocks Opportunity Score calculation."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech_pipe.return_value = {
            "indicators": pd.DataFrame({
                "rsi_score": [18.0], "macd_score": [0.0], "trend_score": [0.0], "volume_score": [3.0],
                "technical_score": [21.0]
            })
        }
        mock_fin.return_value = {"overall_score": None, "status": "INSUFFICIENT"}

        res = calculate_opportunity_score("HDFCBANK")
        self.assertIsNone(res["financial_score"])
        self.assertIsNone(res["opportunity_score"])
        self.assertEqual(res["recommendation"], "INSUFFICIENT_DATA")
        self.assertEqual(res["status"], "INSUFFICIENT")

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_missing_technical_score_blocks_calculation(self, mock_fin, mock_tech_pipe, mock_get_data):
        """Verify missing technical score blocks Opportunity Score calculation."""
        mock_get_data.return_value = pd.DataFrame()  # Empty market data
        mock_fin.return_value = {"overall_score": 80.0, "status": "VALID"}

        res = calculate_opportunity_score("TEST")
        self.assertIsNone(res["technical_score"])
        self.assertIsNone(res["opportunity_score"])
        self.assertEqual(res["recommendation"], "INSUFFICIENT_DATA")
        self.assertEqual(res["status"], "INSUFFICIENT")

    # -------------------------------------------------------------------------
    # 5. INPUT NORMALIZATION & EXCEPTION SAFETY
    # -------------------------------------------------------------------------
    def test_symbol_normalization(self):
        """Verify whitespaces and lowercases are normalized."""
        res = calculate_opportunity_score("   tcs   ")
        self.assertEqual(res["symbol"], "TCS")

    def test_empty_symbol_handling(self):
        """Verify empty string or None symbols return INSUFFICIENT gracefully."""
        res1 = calculate_opportunity_score("")
        self.assertEqual(res1["status"], "INSUFFICIENT")
        self.assertEqual(res1["recommendation"], "INSUFFICIENT_DATA")
        self.assertIsNone(res1["opportunity_score"])

        res2 = calculate_opportunity_score(None)
        self.assertEqual(res2["status"], "INSUFFICIENT")
        self.assertEqual(res2["recommendation"], "INSUFFICIENT_DATA")
        self.assertIsNone(res2["opportunity_score"])

    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_underlying_exception_safety(self, mock_fin):
        """Verify exception in underlying analyzer is safely caught."""
        mock_fin.side_effect = RuntimeError("Database connection reset")

        res = calculate_opportunity_score("TCS")
        self.assertEqual(res["symbol"], "TCS")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNone(res["opportunity_score"])
        self.assertEqual(res["recommendation"], "INSUFFICIENT_DATA")


class TestDecisionEngineIntegration(unittest.TestCase):
    """Integration tests running against the live SQLite project database."""

    def test_real_stock_tcs(self):
        """Live DB Integration Test for TCS."""
        res = calculate_opportunity_score("TCS")
        self.assertEqual(res["symbol"], "TCS")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 56.0)
        self.assertEqual(res["financial_score"], 82.0358)
        self.assertEqual(res["momentum_score"], 63.3333)
        self.assertEqual(res["opportunity_score"], 66.9459)
        self.assertEqual(res["recommendation"], "WATCH")

    def test_real_stock_wipro(self):
        """Live DB Integration Test for WIPRO."""
        res = calculate_opportunity_score("WIPRO")
        self.assertEqual(res["symbol"], "WIPRO")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 56.0)
        self.assertEqual(res["financial_score"], 71.3916)
        self.assertEqual(res["momentum_score"], 75.0)
        self.assertEqual(res["opportunity_score"], 66.1371)
        self.assertEqual(res["recommendation"], "WATCH")

    def test_real_stock_reliance(self):
        """Live DB Integration Test for RELIANCE."""
        res = calculate_opportunity_score("RELIANCE")
        self.assertEqual(res["symbol"], "RELIANCE")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 72.0)
        self.assertEqual(res["financial_score"], 51.9755)
        self.assertEqual(res["momentum_score"], 100.0)
        self.assertEqual(res["opportunity_score"], 71.9914)
        self.assertEqual(res["recommendation"], "WATCH")

    def test_real_stock_infy(self):
        """Live DB Integration Test for INFY."""
        res = calculate_opportunity_score("INFY")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 75.0)
        self.assertEqual(res["financial_score"], 70.8268)
        self.assertEqual(res["momentum_score"], 100.0)
        self.assertEqual(res["opportunity_score"], 79.7894)
        self.assertEqual(res["recommendation"], "BUY")

    def test_real_stock_hdfcbank(self):
        """Live DB Integration Test for HDFCBANK (Insufficient Data)."""
        res = calculate_opportunity_score("HDFCBANK")
        self.assertEqual(res["symbol"], "HDFCBANK")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["technical_score"], 21.0)
        self.assertIsNone(res["financial_score"])
        self.assertEqual(res["momentum_score"], 30.0)
        self.assertIsNone(res["opportunity_score"])
        self.assertEqual(res["recommendation"], "INSUFFICIENT_DATA")


if __name__ == "__main__":
    unittest.main()
