import unittest
from unittest.mock import patch, MagicMock
from backend.logic.signal_integration import run_signal_pipeline

class TestSignalIntegration(unittest.TestCase):

    def setUp(self):
        # Default mock returns
        self.mock_decision = {
            "recommendation": "BUY",
            "opportunity_score": 85.0
        }
        self.mock_inputs = {
            "current_price": 101.0,
            "atr_14": 4.0,
            "nearest_support": {"level": 100.0, "zone_low": 100.0},
            "nearest_resistance": {"level": 112.0, "zone_low": 112.0},
            "data_quality": "VALID"
        }

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_valid_buy_setup(self, mock_decision_fn, mock_inputs_fn):
        mock_decision_fn.return_value = self.mock_decision
        mock_inputs_fn.return_value = self.mock_inputs

        res = run_signal_pipeline("INFY")

        self.assertTrue(res["signal_valid"])
        self.assertEqual(res["reason"], "VALID_SIGNAL")
        self.assertEqual(res["symbol"], "INFY")
        self.assertGreater(res["risk"], 0)
        self.assertGreater(res["reward"], 0)

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_non_buy_recommendation_rejected(self, mock_decision_fn, mock_inputs_fn):
        self.mock_decision["recommendation"] = "HOLD"
        mock_decision_fn.return_value = self.mock_decision
        mock_inputs_fn.return_value = self.mock_inputs

        res = run_signal_pipeline("INFY")

        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "NOT_A_BUY_RECOMMENDATION")

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_missing_data_engineer_inputs(self, mock_decision_fn, mock_inputs_fn):
        mock_decision_fn.return_value = self.mock_decision
        self.mock_inputs["current_price"] = None
        mock_inputs_fn.return_value = self.mock_inputs

        res = run_signal_pipeline("INFY")

        self.assertFalse(res["signal_valid"])
        self.assertIn("current_price", res["missing_inputs"])
        self.assertEqual(res["reason"], "MISSING_OR_INVALID_INPUTS")

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_insufficient_upstream_result(self, mock_decision_fn, mock_inputs_fn):
        mock_decision_fn.return_value = {"recommendation": "INSUFFICIENT_DATA"}
        mock_inputs_fn.return_value = {"data_quality": "INCOMPLETE"} # completely missing other fields

        res = run_signal_pipeline("INFY")

        self.assertFalse(res["signal_valid"])
        self.assertIn("current_price", res["missing_inputs"])

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_evaluation_date_propagation(self, mock_decision_fn, mock_inputs_fn):
        mock_decision_fn.return_value = self.mock_decision
        mock_inputs_fn.return_value = self.mock_inputs

        test_date = "2024-01-01"
        res = run_signal_pipeline("RELIANCE", evaluation_date=test_date)

        mock_decision_fn.assert_called_once_with("RELIANCE", evaluation_date=test_date)
        mock_inputs_fn.assert_called_once_with("RELIANCE", evaluation_date=test_date)
        self.assertEqual(res["evaluation_date"], test_date)

    @patch('backend.logic.signal_integration.generate_final_signal')
    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_signal_engine_receives_correct_inputs(self, mock_decision_fn, mock_inputs_fn, mock_generate_fn):
        mock_decision_fn.return_value = self.mock_decision
        mock_inputs_fn.return_value = self.mock_inputs
        mock_generate_fn.return_value = {"signal_valid": True} # dummy

        run_signal_pipeline("INFY")

        mock_generate_fn.assert_called_once_with(
            current_price=101.0,
            nearest_support=self.mock_inputs["nearest_support"],
            nearest_resistance=self.mock_inputs["nearest_resistance"],
            atr_14=4.0,
            recommendation="BUY"
        )

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_upstream_exception_isolation(self, mock_decision_fn, mock_inputs_fn):
        mock_decision_fn.side_effect = Exception("Database dead")
        mock_inputs_fn.return_value = self.mock_inputs

        # Should not crash
        res = run_signal_pipeline("INFY")

        self.assertFalse(res["signal_valid"])
        self.assertIn("recommendation", res["missing_inputs"])

    @patch('backend.logic.signal_integration.get_stop_target_inputs')
    @patch('backend.logic.signal_integration.calculate_opportunity_score')
    def test_deterministic_repeated_execution(self, mock_decision_fn, mock_inputs_fn):
        mock_decision_fn.return_value = self.mock_decision
        mock_inputs_fn.return_value = self.mock_inputs

        res1 = run_signal_pipeline("INFY")
        res2 = run_signal_pipeline("INFY")
        self.assertEqual(res1, res2)

if __name__ == "__main__":
    unittest.main()
