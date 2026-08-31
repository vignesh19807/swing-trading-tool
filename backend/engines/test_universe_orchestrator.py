"""
Tests for Universe Orchestrator
===============================
Verifies the end-to-end integration and isolation boundaries.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from backend.engines.universe_orchestrator import rank_universe


class TestUniverseOrchestrator(unittest.TestCase):

    @patch("backend.engines.universe_orchestrator.get_all_classifications")
    @patch("backend.engines.universe_orchestrator.get_stock_sector_performance_context")
    @patch("backend.engines.universe_orchestrator.calculate_opportunity_score")
    @patch("backend.engines.universe_orchestrator.generate_top_10_ranking")
    def test_empty_universe(self, mock_generate_top_10, mock_calculate, mock_sector_perf, mock_get_all):
        """Test behavior when the universe is completely empty."""
        # Setup: Data Engineer returns empty universe
        mock_get_all.return_value = pd.DataFrame(columns=["symbol"])
        mock_generate_top_10.return_value = {"top_10": [], "unranked": []}

        # Execute
        res = rank_universe()

        # Assertions
        mock_get_all.assert_called_once()
        mock_calculate.assert_not_called()
        mock_sector_perf.assert_not_called()
        mock_generate_top_10.assert_called_once_with([], evaluation_date=None)

        self.assertEqual(res["top_10"], [])

    @patch("backend.engines.universe_orchestrator.get_all_classifications")
    @patch("backend.engines.universe_orchestrator.get_stock_sector_performance_context")
    @patch("backend.engines.universe_orchestrator.calculate_opportunity_score")
    @patch("backend.engines.universe_orchestrator.generate_top_10_ranking")
    def test_single_valid_stock(self, mock_generate_top_10, mock_calculate, mock_sector_perf, mock_get_all):
        """Test standard pipeline flow for a single valid stock."""
        mock_get_all.return_value = pd.DataFrame({"symbol": ["TCS"]})
        mock_sector_perf.return_value = {"status": "VALID", "preliminary_score": {"score": 80.0}}
        mock_calculate.return_value = {"symbol": "TCS", "status": "VALID", "opportunity_score": 75.0}

        expected_top_10_res = {
            "top_10": [
                {"symbol": "TCS", "final_ranking_score": 76.5, "rank": 1}
            ],
            "unranked": []
        }
        mock_generate_top_10.return_value = expected_top_10_res

        res = rank_universe("2026-08-14")

        # Verify component calls
        mock_sector_perf.assert_called_once_with("TCS", evaluation_date="2026-08-14")
        mock_calculate.assert_called_once_with("TCS", evaluation_date="2026-08-14", sector_intelligence=mock_sector_perf.return_value)

        # Verify ranking engine call
        mock_generate_top_10.assert_called_once_with([mock_calculate.return_value], evaluation_date="2026-08-14")
        self.assertEqual(res["top_10"][0]["symbol"], "TCS")

    @patch("backend.engines.universe_orchestrator.get_all_classifications")
    @patch("backend.engines.universe_orchestrator.get_stock_sector_performance_context")
    @patch("backend.engines.universe_orchestrator.calculate_opportunity_score")
    def test_failure_isolation_missing_sector(self, mock_calculate, mock_sector_perf, mock_get_all):
        """Test failure isolation when sector intelligence crashes."""
        mock_get_all.return_value = pd.DataFrame({"symbol": ["WIPRO"]})
        # Simulate Data Pipeline crash
        mock_sector_perf.side_effect = Exception("DB Connection Lost")

        mock_calculate.return_value = {"symbol": "WIPRO", "status": "VALID", "opportunity_score": 75.0}

        res = rank_universe()

        # Calculate should still be called, but with sector_intelligence=None
        mock_calculate.assert_called_once_with("WIPRO", evaluation_date=None, sector_intelligence=None)

        # Since ranking engine processes it with neutral sector score fallback, it will rank
        self.assertEqual(res["top_10"][0]["symbol"], "WIPRO")
        self.assertEqual(res["top_10"][0]["final_ranking_score"], 75.0)

    @patch("backend.engines.universe_orchestrator.get_all_classifications")
    @patch("backend.engines.universe_orchestrator.get_stock_sector_performance_context")
    @patch("backend.engines.universe_orchestrator.calculate_opportunity_score")
    def test_failure_isolation_decision_engine_crash(self, mock_calculate, mock_sector_perf, mock_get_all):
        """Test failure isolation when Decision Engine completely crashes for one stock."""
        mock_get_all.return_value = pd.DataFrame({"symbol": ["GOOD", "CRASH"]})

        mock_sector_perf.return_value = {"status": "VALID"}

        def calculate_side_effect(symbol, *args, **kwargs):
            if symbol == "CRASH":
                raise ValueError("Unexpected Math Error")
            return {"symbol": symbol, "status": "VALID", "opportunity_score": 85.0}

        mock_calculate.side_effect = calculate_side_effect

        res = rank_universe()

        # GOOD stock is ranked
        self.assertEqual(len(res["top_10"]), 1)
        self.assertEqual(res["top_10"][0]["symbol"], "GOOD")

        # CRASH stock is safely pushed to unranked with artificial INSUFFICIENT mapping
        self.assertEqual(len(res["unranked"]), 1)
        self.assertEqual(res["unranked"][0]["symbol"], "CRASH")
        self.assertEqual(res["unranked"][0]["reason"], "MISSING_CORE_OPPORTUNITY_SCORE")

    @patch("backend.engines.universe_orchestrator.get_all_classifications")
    @patch("backend.engines.universe_orchestrator.get_stock_sector_performance_context")
    @patch("backend.engines.universe_orchestrator.calculate_opportunity_score")
    def test_mixed_valid_and_invalid_large_universe(self, mock_calculate, mock_sector_perf, mock_get_all):
        """Test large universe (15 stocks) with Top 10 truncation."""
        symbols = [f"STOCK_{i}" for i in range(15)]
        mock_get_all.return_value = pd.DataFrame({"symbol": symbols})
        mock_sector_perf.return_value = None

        def calculate_side_effect(symbol, *args, **kwargs):
            idx = int(symbol.split("_")[1])
            # Stock 14 is invalid
            if idx == 14:
                return {"symbol": symbol, "status": "INSUFFICIENT", "opportunity_score": None}
            # Score ascending from 50
            return {"symbol": symbol, "status": "VALID", "opportunity_score": 50.0 + idx}

        mock_calculate.side_effect = calculate_side_effect

        res = rank_universe()

        self.assertEqual(len(res["top_10"]), 10)
        self.assertEqual(len(res["unranked"]), 5) # 4 valid outside top 10, 1 insufficient

        # Highest score is STOCK_13 (STOCK_14 is invalid)
        self.assertEqual(res["top_10"][0]["symbol"], "STOCK_13")
        self.assertEqual(res["top_10"][0]["final_ranking_score"], 63.0)

        # Verify reasons in unranked
        unranked_reasons = {x["symbol"]: x["reason"] for x in res["unranked"]}
        self.assertEqual(unranked_reasons["STOCK_14"], "MISSING_CORE_OPPORTUNITY_SCORE")
        self.assertEqual(unranked_reasons["STOCK_3"], "OUTSIDE_TOP_10")


if __name__ == "__main__":
    unittest.main()
