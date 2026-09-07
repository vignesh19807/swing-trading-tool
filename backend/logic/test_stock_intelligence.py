"""
Unit & Integration Tests for Stock Intelligence Service (Week 11 Step 4)
========================================================================

Verifies:
1. Explicit historical evaluation_date propagation across all component services
2. Missing market, financial, sector, snapshot, technical, or signal component failures
3. Payload isolation (no pandas DataFrames, SQL, or internal transient objects)
4. Determinism of repeated calls
5. Live integration test against real project database
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from backend.logic.stock_intelligence import get_stock_intelligence


class TestStockIntelligenceUnit(unittest.TestCase):
    """Unit tests for stock intelligence assembly with mocks."""

    @patch("backend.logic.stock_intelligence.get_stock_snapshot")
    @patch("backend.logic.stock_intelligence.get_stock_sector_performance_context")
    @patch("backend.logic.stock_intelligence.calculate_opportunity_score")
    @patch("backend.logic.stock_intelligence.explain_opportunity")
    @patch("backend.logic.stock_intelligence.run_signal_pipeline")
    def test_1_evaluation_date_propagation_all_services(
        self, mock_signal, mock_explain, mock_calc, mock_sector, mock_snapshot
    ):
        """Verify explicit evaluation_date propagates to all underlying services."""
        eval_date = "2025-10-10"
        mock_snapshot.return_value = {"symbol": "INFY", "status": "VALID", "identity": {"sector": "IT"}}
        mock_sector.return_value = {"status": "VALID"}
        mock_calc.return_value = {"symbol": "INFY", "status": "VALID", "opportunity_score": 80.0, "recommendation": "BUY"}
        mock_explain.return_value = {"summary": "Strong factors."}
        mock_signal.return_value = {"signal_valid": True, "trade_quality": {"is_eligible": True}}

        res = get_stock_intelligence("INFY", evaluation_date=eval_date)

        mock_snapshot.assert_called_once_with("INFY", evaluation_date=eval_date)
        mock_sector.assert_called_once_with("INFY", evaluation_date=eval_date)
        mock_calc.assert_called_once_with("INFY", evaluation_date=eval_date, sector_intelligence=mock_sector.return_value)
        mock_explain.assert_called_once_with(
            decision_payload=mock_calc.return_value,
            indicators_df=None,
            financial_result=None,
            evaluation_date=eval_date
        )
        mock_signal.assert_called_once_with("INFY", evaluation_date=eval_date)

        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["evaluation_date"], eval_date)

    @patch("backend.logic.stock_intelligence.get_stock_snapshot")
    @patch("backend.logic.stock_intelligence.get_stock_sector_performance_context")
    @patch("backend.logic.stock_intelligence.calculate_opportunity_score")
    @patch("backend.logic.stock_intelligence.run_signal_pipeline")
    def test_2_missing_snapshot_service_failure(
        self, mock_signal, mock_calc, mock_sector, mock_snapshot
    ):
        """Verify graceful fallback when snapshot service raises exception."""
        mock_snapshot.side_effect = RuntimeError("Snapshot DB unavailable")
        mock_sector.return_value = None
        mock_calc.return_value = {"symbol": "TCS", "status": "VALID", "opportunity_score": 70.0, "recommendation": "WATCH"}
        mock_signal.return_value = {"signal_valid": False}

        res = get_stock_intelligence("TCS", evaluation_date="2026-08-14")

        self.assertEqual(res["symbol"], "TCS")
        self.assertIsNone(res["identity"])
        self.assertIsNone(res["data_quality"])
        self.assertEqual(res["decision_result"]["opportunity_score"], 70.0)

    @patch("backend.logic.stock_intelligence.get_stock_snapshot")
    @patch("backend.logic.stock_intelligence.get_stock_sector_performance_context")
    @patch("backend.logic.stock_intelligence.calculate_opportunity_score")
    def test_3_missing_financial_or_technical_data(
        self, mock_calc, mock_sector, mock_snapshot
    ):
        """Verify INSUFFICIENT status when technical or financial core component is missing."""
        mock_snapshot.return_value = {"symbol": "HDFCBANK", "status": "PARTIAL"}
        mock_sector.return_value = None
        mock_calc.return_value = {
            "symbol": "HDFCBANK",
            "status": "INSUFFICIENT",
            "technical_score": 21.0,
            "financial_score": None,
            "opportunity_score": None,
            "recommendation": "INSUFFICIENT_DATA"
        }

        res = get_stock_intelligence("HDFCBANK")

        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertEqual(res["decision_result"]["recommendation"], "INSUFFICIENT_DATA")

    def assert_no_pandas_objects(self, obj, path="root"):
        """Recursively assert that no pandas DataFrame or pandas Series exists anywhere inside obj."""
        self.assertNotIsInstance(
            obj,
            (pd.DataFrame, pd.Series),
            msg=f"Pandas object ({type(obj).__name__}) leaked at {path}"
        )
        if isinstance(obj, dict):
            for k, v in obj.items():
                self.assert_no_pandas_objects(v, path=f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                self.assert_no_pandas_objects(v, path=f"{path}[{i}]")

    @patch("backend.logic.stock_intelligence.get_stock_snapshot")
    @patch("backend.logic.stock_intelligence.get_stock_sector_performance_context")
    @patch("backend.logic.stock_intelligence.calculate_opportunity_score")
    @patch("backend.logic.stock_intelligence.explain_opportunity")
    @patch("backend.logic.stock_intelligence.run_signal_pipeline")
    def test_4_no_dataframes_or_internal_context_leaked(
        self, mock_signal, mock_explain, mock_calc, mock_sector, mock_snapshot
    ):
        """Verify no pandas DataFrames or transient objects leak into final public payload."""
        mock_snapshot.return_value = {"symbol": "WIPRO"}
        mock_sector.return_value = None
        mock_calc.return_value = {
            "symbol": "WIPRO",
            "status": "VALID",
            "opportunity_score": 65.0,
            "_explanation_context": {
                "indicators_df": pd.DataFrame({"dummy": range(10)}),
                "financial_result": {"status": "VALID"}
            }
        }
        mock_explain.return_value = {"summary": "Valid explanation."}
        mock_signal.return_value = {"signal_valid": False}

        res = get_stock_intelligence("WIPRO")

        self.assertNotIn("_explanation_context", res)
        self.assertNotIn("indicators_df", res)
        self.assert_no_pandas_objects(res)

    def test_5_empty_symbol_handling(self):
        """Verify empty symbol returns INVALID structure without throwing error."""
        res = get_stock_intelligence("")
        self.assertEqual(res["status"], "INVALID")
        self.assertEqual(res["symbol"], "")
        self.assertIsNone(res["identity"])

    @patch("backend.logic.stock_intelligence.get_stock_snapshot")
    @patch("backend.logic.stock_intelligence.get_stock_sector_performance_context")
    @patch("backend.logic.stock_intelligence.calculate_opportunity_score")
    @patch("backend.logic.stock_intelligence.run_signal_pipeline")
    def test_6_repeated_execution_determinism(
        self, mock_signal, mock_calc, mock_sector, mock_snapshot
    ):
        """Verify repeated calls with same inputs yield identical payload."""
        mock_snapshot.return_value = {"symbol": "RELIANCE", "status": "VALID"}
        mock_sector.return_value = {"status": "VALID"}
        mock_calc.return_value = {"symbol": "RELIANCE", "status": "VALID", "opportunity_score": 75.0}
        mock_signal.return_value = {"signal_valid": True}

        res1 = get_stock_intelligence("RELIANCE", evaluation_date="2026-08-14")
        res2 = get_stock_intelligence("RELIANCE", evaluation_date="2026-08-14")

        self.assertEqual(res1, res2)


class TestStockIntelligenceLiveIntegration(unittest.TestCase):
    """Integration test executing against live project database."""

    def test_live_tcs_intelligence(self):
        """Live DB integration test for TCS."""
        res = get_stock_intelligence("TCS", evaluation_date="2026-08-14")

        self.assertEqual(res["symbol"], "TCS")
        self.assertEqual(res["evaluation_date"], "2026-08-14")
        self.assertIn("identity", res)
        self.assertEqual(res["identity"]["company_name"], "Tata Consultancy Services Limited")
        self.assertIn("decision_result", res)
        self.assertEqual(res["decision_result"]["opportunity_score"], 66.9459)
        self.assertIn("structured_explanation", res)
        self.assertIn("signal_result", res)
        self.assertIn("trade_quality", res)


if __name__ == "__main__":
    unittest.main()
