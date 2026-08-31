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
        res = calculate_opportunity_score("TCS", evaluation_date="2026-08-14")
        self.assertEqual(res["symbol"], "TCS")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 56.0)
        self.assertEqual(res["financial_score"], 82.0547)
        self.assertEqual(res["momentum_score"], 63.3333)
        self.assertEqual(res["opportunity_score"], 66.9525)
        self.assertEqual(res["recommendation"], "WATCH")

    def test_real_stock_wipro(self):
        """Live DB Integration Test for WIPRO."""
        res = calculate_opportunity_score("WIPRO", evaluation_date="2026-08-14")
        self.assertEqual(res["symbol"], "WIPRO")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 56.0)
        self.assertEqual(res["financial_score"], 71.3914)
        self.assertEqual(res["momentum_score"], 75.0)
        self.assertEqual(res["opportunity_score"], 66.137)
        self.assertEqual(res["recommendation"], "WATCH")

    def test_real_stock_reliance(self):
        """Live DB Integration Test for RELIANCE."""
        res = calculate_opportunity_score("RELIANCE", evaluation_date="2026-08-14")
        self.assertEqual(res["symbol"], "RELIANCE")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 72.0)
        self.assertEqual(res["financial_score"], 51.9792)
        self.assertEqual(res["momentum_score"], 100.0)
        self.assertEqual(res["opportunity_score"], 71.9927)
        self.assertEqual(res["recommendation"], "WATCH")

    def test_real_stock_infy(self):
        """Live DB Integration Test for INFY."""
        res = calculate_opportunity_score("INFY", evaluation_date="2026-08-14")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertEqual(res["technical_score"], 75.0)
        self.assertEqual(res["financial_score"], 70.8268)
        self.assertEqual(res["momentum_score"], 100.0)
        self.assertEqual(res["opportunity_score"], 79.7894)
        self.assertEqual(res["recommendation"], "BUY")

    def test_real_stock_hdfcbank(self):
        """Live DB Integration Test for HDFCBANK (Insufficient Data)."""
        res = calculate_opportunity_score("HDFCBANK", evaluation_date="2026-08-14")
        self.assertEqual(res["symbol"], "HDFCBANK")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["technical_score"], 21.0)
        self.assertIsNone(res["financial_score"])
        self.assertEqual(res["momentum_score"], 30.0)
        self.assertIsNone(res["opportunity_score"])
        self.assertEqual(res["recommendation"], "INSUFFICIENT_DATA")


class TestSectorIntelligenceIntegration(unittest.TestCase):
    """Tests for Sector Intelligence dependency injection (Week 6 Thursday)."""

    def setUp(self):
        self.mock_context = {
            "status": "VALID",
            "classification": {
                "sector": "Information Technology",
                "industry": "IT Services"
            },
            "stock_performance": {"21D": 0.05},
            "sector_performance": {"data_quality": "VALID"}
        }

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_A_backward_compatible_call(self, mock_fin, mock_tech, mock_get_data):
        """A. Calling without the kwarg calculates std Opportunity Score with sector_intelligence: None."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech.return_value = {"indicators": pd.DataFrame({"rsi_score": [30.0], "macd_score": [30.0], "technical_score": [100.0]})}
        mock_fin.return_value = {"overall_score": 100.0, "status": "VALID"}

        res = calculate_opportunity_score("INFY")
        self.assertIsNone(res["sector_intelligence"])
        self.assertEqual(res["opportunity_score"], 100.0)

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_B_new_injected_context_and_F_structure(self, mock_fin, mock_tech, mock_get_data):
        """B & F. Calling with precomputed context successfully attaches it unchanged."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech.return_value = {"indicators": pd.DataFrame({"rsi_score": [30.0], "macd_score": [30.0], "technical_score": [100.0]})}
        mock_fin.return_value = {"overall_score": 100.0, "status": "VALID"}

        res = calculate_opportunity_score("INFY", sector_intelligence=self.mock_context)
        self.assertIsNotNone(res["sector_intelligence"])
        self.assertEqual(res["sector_intelligence"]["classification"]["sector"], "Information Technology")
        self.assertEqual(res["sector_intelligence"]["stock_performance"]["21D"], 0.05)

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_C_evaluation_date_propagation(self, mock_fin, mock_tech, mock_get_data):
        """C. Passing evaluation_date still restricts underlying Technical/Financial Historical data appropriately."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech.return_value = {"indicators": pd.DataFrame({"rsi_score": [30.0], "macd_score": [30.0], "technical_score": [100.0]})}
        mock_fin.return_value = {"overall_score": 100.0, "status": "VALID"}

        calculate_opportunity_score("INFY", evaluation_date="2025-10-10", sector_intelligence=self.mock_context)

        # Verify the date was forwarded to sub-engines
        mock_get_data.assert_called_once_with("INFY", end_date="2025-10-10")
        mock_fin.assert_called_once_with("INFY", evaluation_date="2025-10-10")

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_D_sector_intelligence_absence(self, mock_fin, mock_tech, mock_get_data):
        """D. Explicitly passing None does not degrade status or recommendation."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech.return_value = {"indicators": pd.DataFrame({"rsi_score": [30.0], "macd_score": [30.0], "technical_score": [100.0]})}
        mock_fin.return_value = {"overall_score": 100.0, "status": "VALID"}

        res = calculate_opportunity_score("INFY", sector_intelligence=None)
        self.assertIsNone(res["sector_intelligence"])
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["recommendation"], "BUY")

    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_E_score_overlay_verification(self, mock_fin, mock_tech, mock_get_data):
        """E. Asserting that the Opportunity Score is mathematically identical in scenarios A and B."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech.return_value = {"indicators": pd.DataFrame({"rsi_score": [15.0], "macd_score": [15.0], "technical_score": [50.0]})}
        mock_fin.return_value = {"overall_score": 60.0, "status": "VALID"}

        res_a = calculate_opportunity_score("INFY")
        res_b = calculate_opportunity_score("INFY", sector_intelligence=self.mock_context)

        self.assertEqual(res_a["opportunity_score"], res_b["opportunity_score"])
        self.assertEqual(res_a["recommendation"], res_b["recommendation"])
        self.assertEqual(res_a["status"], res_b["status"])

    @patch("backend.logic.stock_context_analyzer.get_stock_sector_performance_context")
    @patch("backend.engines.decision_engine.get_stock_data")
    @patch("backend.engines.decision_engine.run_technical_pipeline")
    @patch("backend.engines.financial_engine.analyze_financial_health")
    def test_G_no_sector_recalculation(self, mock_fin, mock_tech, mock_get_data, mock_sector):
        """G. Verifying the Decision Engine does not invoke Data Pipeline for Sector logic."""
        mock_get_data.return_value = pd.DataFrame({"dummy": range(25)})
        mock_tech.return_value = {"indicators": pd.DataFrame({"rsi_score": [30.0], "macd_score": [30.0], "technical_score": [100.0]})}
        mock_fin.return_value = {"overall_score": 100.0, "status": "VALID"}

        calculate_opportunity_score("INFY", sector_intelligence=self.mock_context)
        mock_sector.assert_not_called()


if __name__ == "__main__":
    unittest.main()
