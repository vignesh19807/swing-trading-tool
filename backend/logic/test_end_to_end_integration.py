"""
Week 10 Step 5 - End-to-End Integration Unit Tests

Verifies end-to-end integration across Decision Engine, Signal Integration,
Trade Quality Engine, and Universe Orchestrator.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from backend.logic.signal_integration import run_signal_pipeline
from backend.engines.universe_orchestrator import rank_universe
from backend.logic.trade_quality_engine import evaluate_trade_eligibility


class TestEndToEndIntegration(unittest.TestCase):

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_1_valid_buy_signal_integration(self, mock_inputs, mock_decision):
        """1. Valid BUY signal -> trade quality attached correctly."""
        mock_decision.return_value = {"symbol": "TCS", "recommendation": "BUY", "opportunity_score": 85.0}
        mock_inputs.return_value = {
            "current_price": 100.0,
            "nearest_support": {"level": 99.0, "zone_low": 96.0},
            "nearest_resistance": {"zone_low": 115.0},
            "atr_14": 2.0
        }

        res = run_signal_pipeline("TCS", evaluation_date="2026-08-14")

        self.assertTrue(res["signal_valid"])
        self.assertEqual(res["recommendation"], "BUY")
        self.assertEqual(res["evaluation_date"], "2026-08-14")
        self.assertIn("trade_quality", res)
        self.assertTrue(res["is_eligible"])
        self.assertEqual(res["trade_quality"]["risk_status"], "ELIGIBLE")
        self.assertEqual(res["trade_quality"]["risk_flags"], [])

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_2_non_buy_recommendation_integration(self, mock_inputs, mock_decision):
        """2. Non-BUY recommendation -> recommendation preserved and marked ineligible."""
        mock_decision.return_value = {"symbol": "INFY", "recommendation": "HOLD", "opportunity_score": 60.0}
        mock_inputs.return_value = {
            "current_price": 100.0,
            "nearest_support": {"level": 99.0, "zone_low": 96.0},
            "nearest_resistance": {"zone_low": 115.0},
            "atr_14": 2.0
        }

        res = run_signal_pipeline("INFY", evaluation_date="2026-08-14")

        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["recommendation"], "HOLD")
        self.assertIn("trade_quality", res)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["trade_quality"]["risk_status"], "INELIGIBLE")
        self.assertEqual(res["trade_quality"]["risk_flags"], ["NON_BUY_RECOMMENDATION"])

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_3_invalid_signal_risk_context_preserved(self, mock_inputs, mock_decision):
        """3. Invalid signal -> risk context preserved."""
        mock_decision.return_value = {"symbol": "WIPRO", "recommendation": "BUY", "opportunity_score": 80.0}
        # Support zone low causes stop loss (105 - 3 = 102) to be above current price (100)
        mock_inputs.return_value = {
            "current_price": 100.0,
            "nearest_support": {"level": 99.0, "zone_low": 105.0},
            "nearest_resistance": {"zone_low": 115.0},
            "atr_14": 2.0
        }

        res = run_signal_pipeline("WIPRO", evaluation_date="2026-08-14")

        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "STOP_ABOVE_CURRENT_PRICE")
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["trade_quality"]["risk_status"], "INVALID")
        self.assertEqual(res["trade_quality"]["risk_flags"], ["INVALID_STOP"])

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_4_insufficient_rr_risk_context_preserved(self, mock_inputs, mock_decision):
        """4. Insufficient R:R -> risk context preserved."""
        mock_decision.return_value = {"symbol": "TATAMOTORS", "recommendation": "BUY", "opportunity_score": 80.0}
        mock_inputs.return_value = {
            "current_price": 100.0,
            "nearest_support": {"level": 99.0, "zone_low": 96.0}, # Risk = 100 - (96 - 3) = 7
            "nearest_resistance": {"zone_low": 104.0},            # Reward = 104 - 100 = 4 (R:R = 4/7 < 1.5)
            "atr_14": 2.0
        }

        res = run_signal_pipeline("TATAMOTORS", evaluation_date="2026-08-14")

        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "INSUFFICIENT_RISK_REWARD_RATIO")
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["trade_quality"]["risk_status"], "INELIGIBLE")
        self.assertEqual(res["trade_quality"]["risk_flags"], ["INSUFFICIENT_RISK_REWARD"])

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_5_missing_inputs_handling(self, mock_inputs, mock_decision):
        """5. Missing inputs -> no crash and correct context."""
        mock_decision.return_value = {"symbol": "SBIN", "recommendation": "BUY", "opportunity_score": 80.0}
        mock_inputs.return_value = {
            "current_price": None, # Missing current price
            "nearest_support": None,
            "nearest_resistance": None,
            "atr_14": None
        }

        res = run_signal_pipeline("SBIN", evaluation_date="2026-08-14")

        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "MISSING_OR_INVALID_INPUTS")
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["trade_quality"]["risk_status"], "INCOMPLETE")
        self.assertEqual(res["trade_quality"]["risk_flags"], ["MISSING_INPUTS"])
        self.assertIn("current_price", res["trade_quality"]["missing_inputs"])

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_6_evaluation_date_preservation(self, mock_inputs, mock_decision):
        """6. Evaluation date -> preserved through integration."""
        mock_decision.return_value = {"symbol": "RELIANCE", "recommendation": "BUY", "opportunity_score": 88.0}
        mock_inputs.return_value = {
            "current_price": 2500.0,
            "nearest_support": {"level": 2480.0, "zone_low": 2450.0},
            "nearest_resistance": {"zone_low": 2750.0},
            "atr_14": 30.0
        }

        eval_date = "2024-05-20"
        res = run_signal_pipeline("RELIANCE", evaluation_date=eval_date)

        self.assertEqual(res["evaluation_date"], eval_date)
        mock_decision.assert_called_once_with("RELIANCE", evaluation_date=eval_date)
        mock_inputs.assert_called_once_with("RELIANCE", evaluation_date=eval_date)

    @patch("backend.engines.universe_orchestrator.get_all_classifications")
    @patch("backend.engines.universe_orchestrator.get_stock_sector_performance_context")
    @patch("backend.engines.universe_orchestrator.calculate_opportunity_score")
    def test_7_8_9_opportunity_score_ranking_top10_preservation(self, mock_calc, mock_sec, mock_get_all):
        """7, 8, 9. Scores, ranking order, and Top 10 membership remain unchanged."""
        symbols = [f"STOCK_{i:02d}" for i in range(15)]
        mock_get_all.return_value = pd.DataFrame({"symbol": symbols})
        mock_sec.return_value = None

        # Scores descending from 95 to 67
        def calc_side_effect(sym, *args, **kwargs):
            idx = int(sym.split("_")[1])
            return {
                "symbol": sym,
                "status": "VALID",
                "opportunity_score": 95.0 - (idx * 2),
                "recommendation": "BUY" if idx % 2 == 0 else "HOLD"
            }

        mock_calc.side_effect = calc_side_effect

        res = rank_universe(evaluation_date="2026-08-14")

        top_10 = res["top_10"]
        self.assertEqual(len(top_10), 10)

        # Top 10 membership & ranking order check:
        # Highest opp scores are STOCK_00 (95), STOCK_01 (93), ... STOCK_09 (77)
        expected_order = [f"STOCK_{i:02d}" for i in range(10)]
        actual_order = [s["symbol"] for s in top_10]
        self.assertEqual(actual_order, expected_order)

        # Confirm scores match exactly
        for i, stock in enumerate(top_10):
            expected_score = 95.0 - (i * 2)
            self.assertEqual(stock["opportunity_score"], expected_score)
            self.assertEqual(stock["final_ranking_score"], expected_score) # Sector fallback = opp score
            self.assertEqual(stock["rank"], i + 1)
            self.assertIn("trade_quality", stock)
            self.assertIn("is_eligible", stock)

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_10_no_internal_context_leakage(self, mock_inputs, mock_decision):
        """10. No internal DataFrames or internal calculation objects leak into final output."""
        mock_decision.return_value = {
            "symbol": "HDFCBANK",
            "recommendation": "BUY",
            "opportunity_score": 82.0,
            "_explanation_context": {"internal_df": pd.DataFrame()} # Transient context
        }
        mock_inputs.return_value = {
            "current_price": 1500.0,
            "nearest_support": {"level": 1490.0, "zone_low": 1470.0},
            "nearest_resistance": {"zone_low": 1650.0},
            "atr_14": 20.0
        }

        res = run_signal_pipeline("HDFCBANK")

        self.assertNotIn("_explanation_context", res)
        self.assertNotIn("indicators_df", res)
        for key, val in res.items():
            self.assertNotIsInstance(val, pd.DataFrame)

    @patch("backend.logic.signal_integration.calculate_opportunity_score")
    @patch("backend.logic.signal_integration.get_stop_target_inputs")
    def test_11_repeated_execution_determinism(self, mock_inputs, mock_decision):
        """11. Repeated execution with identical inputs produces identical integrated output."""
        mock_decision.return_value = {"symbol": "ICICIBANK", "recommendation": "BUY", "opportunity_score": 85.0}
        mock_inputs.return_value = {
            "current_price": 1000.0,
            "nearest_support": {"level": 990.0, "zone_low": 970.0},
            "nearest_resistance": {"zone_low": 1100.0},
            "atr_14": 15.0
        }

        res1 = run_signal_pipeline("ICICIBANK", evaluation_date="2026-08-14")
        res2 = run_signal_pipeline("ICICIBANK", evaluation_date="2026-08-14")

        self.assertEqual(res1, res2)


if __name__ == "__main__":
    unittest.main()
