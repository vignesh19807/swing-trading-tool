import unittest
from backend.logic.trade_quality_engine import evaluate_trade_eligibility

class TestTradeQualityEngine(unittest.TestCase):
    def test_1_eligible_valid_buy_setup(self):
        signal = {
            "signal_valid": True,
            "recommendation": "BUY",
            "reason": "VALID_SIGNAL"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertTrue(res["is_eligible"])
        self.assertEqual(res["risk_status"], "ELIGIBLE")
        self.assertEqual(res["eligibility_reason"], "ELIGIBLE")
        self.assertEqual(res["risk_flags"], [])
        self.assertEqual(res["signal_reason"], "VALID_SIGNAL")
        self.assertEqual(res["missing_inputs"], [])

    def test_2_ineligible_non_buy_setup(self):
        signal = {
            "signal_valid": True,
            "recommendation": "HOLD",
            "reason": "NOT_A_BUY_RECOMMENDATION"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INELIGIBLE")
        self.assertEqual(res["eligibility_reason"], "NOT_A_BUY_RECOMMENDATION")
        self.assertEqual(res["risk_flags"], ["NON_BUY_RECOMMENDATION"])

    def test_3_ineligible_signal_valid_false_setup(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "SIGNAL_INVALID"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INVALID")
        self.assertEqual(res["eligibility_reason"], "SIGNAL_INVALID")
        self.assertEqual(res["risk_flags"], ["SIGNAL_INVALID"])

    def test_4_ineligible_insufficient_rr(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "INSUFFICIENT_RISK_REWARD_RATIO"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INELIGIBLE")
        self.assertEqual(res["eligibility_reason"], "INSUFFICIENT_RISK_REWARD_RATIO")
        self.assertEqual(res["risk_flags"], ["INSUFFICIENT_RISK_REWARD"])

    def test_5_ineligible_invalid_risk(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "NON_POSITIVE_RISK"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INVALID")
        self.assertEqual(res["eligibility_reason"], "NON_POSITIVE_RISK")
        self.assertEqual(res["risk_flags"], ["INVALID_RISK"])

    def test_6_ineligible_invalid_reward(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "NON_POSITIVE_REWARD"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INVALID")
        self.assertEqual(res["eligibility_reason"], "NON_POSITIVE_REWARD")
        self.assertEqual(res["risk_flags"], ["INVALID_REWARD"])

    def test_7_ineligible_invalid_stop(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "STOP_ABOVE_CURRENT_PRICE"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INVALID")
        self.assertEqual(res["eligibility_reason"], "STOP_ABOVE_CURRENT_PRICE")
        self.assertEqual(res["risk_flags"], ["INVALID_STOP"])

    def test_8_ineligible_invalid_target(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "TARGET_BELOW_CURRENT_PRICE"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INVALID")
        self.assertEqual(res["eligibility_reason"], "TARGET_BELOW_CURRENT_PRICE")
        self.assertEqual(res["risk_flags"], ["INVALID_TARGET"])

    def test_9_ineligible_invalid_entry_relationship(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "ENTRY_BELOW_STOP_LOSS"
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INVALID")
        self.assertEqual(res["eligibility_reason"], "ENTRY_BELOW_STOP_LOSS")
        self.assertEqual(res["risk_flags"], ["INVALID_ENTRY"])

    def test_10_missing_required_signal_information(self):
        signal = {
            "signal_valid": False,
            "recommendation": "BUY",
            "reason": "MISSING_OR_INVALID_INPUTS",
            "missing_inputs": ["current_price"]
        }
        res = evaluate_trade_eligibility(signal)
        self.assertFalse(res["is_eligible"])
        self.assertEqual(res["risk_status"], "INCOMPLETE")
        self.assertEqual(res["eligibility_reason"], "MISSING_OR_INVALID_INPUTS")
        self.assertEqual(res["risk_flags"], ["MISSING_INPUTS"])
        self.assertEqual(res["missing_inputs"], ["current_price"])

    def test_11_invalid_missing_payload(self):
        res1 = evaluate_trade_eligibility(None)
        self.assertFalse(res1["is_eligible"])
        self.assertEqual(res1["risk_status"], "INVALID")
        self.assertEqual(res1["eligibility_reason"], "INVALID_PAYLOAD")
        self.assertEqual(res1["risk_flags"], ["INVALID_PAYLOAD"])

        res2 = evaluate_trade_eligibility("not_a_dict")
        self.assertFalse(res2["is_eligible"])
        self.assertEqual(res2["risk_status"], "INVALID")

    def test_12_deterministic_repeated_execution(self):
        signal = {
            "signal_valid": True,
            "recommendation": "BUY",
            "reason": "VALID_SIGNAL"
        }
        res1 = evaluate_trade_eligibility(signal)
        res2 = evaluate_trade_eligibility(signal)
        self.assertEqual(res1, res2)

    def test_score_preservation(self):
        # Pass a dictionary that contains scores, verify they are untouched
        signal = {
            "signal_valid": True,
            "recommendation": "BUY",
            "reason": "VALID_SIGNAL",
            "technical_score": 90.0,
            "financial_score": 80.0,
            "momentum_score": 70.0,
            "opportunity_score": 85.0
        }
        res = evaluate_trade_eligibility(signal)

        # Original should be untouched
        self.assertEqual(signal["technical_score"], 90.0)
        self.assertEqual(signal["opportunity_score"], 85.0)

        # Result should only contain eligibility/risk keys
        self.assertTrue(res["is_eligible"])
        self.assertNotIn("technical_score", res)
        self.assertNotIn("financial_score", res)
        self.assertNotIn("momentum_score", res)
        self.assertNotIn("opportunity_score", res)

if __name__ == "__main__":
    unittest.main()
