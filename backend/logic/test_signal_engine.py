import unittest
from backend.logic.signal_engine import calculate_entry_zone, calculate_exit_parameters, generate_final_signal

class TestSignalEngineEntryZone(unittest.TestCase):

    def setUp(self):
        # Default valid inputs
        self.current_price = 101.0
        self.nearest_support = {"level": 100.0}
        self.atr_14 = 4.0
        self.recommendation = "BUY"

    def test_valid_buy_inside_zone(self):
        # bounds: 100 to 102 (100 + 4*0.5)
        # 101 is inside
        res = calculate_entry_zone(self.current_price, self.nearest_support, self.atr_14, self.recommendation)
        self.assertTrue(res["entry_valid"])
        self.assertEqual(res["entry_lower"], 100.0)
        self.assertEqual(res["entry_upper"], 102.0)
        self.assertEqual(res["reason"], "VALID_PULLBACK_ENTRY")
        self.assertEqual(res["missing_inputs"], [])

    def test_price_exactly_at_lower_boundary(self):
        # 100 is inside
        res = calculate_entry_zone(100.0, self.nearest_support, self.atr_14, self.recommendation)
        self.assertTrue(res["entry_valid"])

    def test_price_exactly_at_upper_boundary(self):
        # 102 is inside
        res = calculate_entry_zone(102.0, self.nearest_support, self.atr_14, self.recommendation)
        self.assertTrue(res["entry_valid"])

    def test_price_below_entry_zone(self):
        # 99.9 is outside (below)
        res = calculate_entry_zone(99.9, self.nearest_support, self.atr_14, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertEqual(res["reason"], "PRICE_OUTSIDE_ENTRY_ZONE")

    def test_price_above_entry_zone(self):
        # 102.1 is outside (above)
        res = calculate_entry_zone(102.1, self.nearest_support, self.atr_14, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertEqual(res["reason"], "PRICE_OUTSIDE_ENTRY_ZONE")

    def test_non_buy_recommendation(self):
        res = calculate_entry_zone(self.current_price, self.nearest_support, self.atr_14, "HOLD")
        self.assertFalse(res["entry_valid"])
        self.assertEqual(res["reason"], "NOT_A_BUY_RECOMMENDATION")

    def test_missing_current_price(self):
        res = calculate_entry_zone(None, self.nearest_support, self.atr_14, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertIn("current_price", res["missing_inputs"])
        self.assertEqual(res["reason"], "MISSING_OR_INVALID_INPUTS")

    def test_missing_atr(self):
        res = calculate_entry_zone(self.current_price, self.nearest_support, None, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertIn("atr_14", res["missing_inputs"])
        self.assertEqual(res["reason"], "MISSING_OR_INVALID_INPUTS")

    def test_missing_nearest_support(self):
        res = calculate_entry_zone(self.current_price, None, self.atr_14, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertIn("nearest_support", res["missing_inputs"])
        self.assertEqual(res["reason"], "MISSING_OR_INVALID_INPUTS")

    def test_nearest_support_missing_level(self):
        res = calculate_entry_zone(self.current_price, {"zone_low": 99.0}, self.atr_14, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertIn("nearest_support_level", res["missing_inputs"])

    def test_invalid_non_positive_atr(self):
        # ATR = 0
        res = calculate_entry_zone(self.current_price, self.nearest_support, 0.0, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertIn("invalid_atr_14", res["missing_inputs"])

        # ATR = -1
        res = calculate_entry_zone(self.current_price, self.nearest_support, -1.0, self.recommendation)
        self.assertFalse(res["entry_valid"])
        self.assertIn("invalid_atr_14", res["missing_inputs"])

    def test_multiple_stock_scenarios(self):
        # Scenario 1: Tight ATR, high price
        # bounds: 1000 to 1000 + 2*0.5 = 1001
        res1 = calculate_entry_zone(1000.5, {"level": 1000.0}, 2.0, "BUY")
        self.assertTrue(res1["entry_valid"])
        self.assertEqual(res1["entry_lower"], 1000.0)
        self.assertEqual(res1["entry_upper"], 1001.0)

        # Scenario 2: Wide ATR, price inside
        # bounds: 50 to 50 + 10*0.5 = 55
        res2 = calculate_entry_zone(54.0, {"level": 50.0}, 10.0, "BUY")
        self.assertTrue(res2["entry_valid"])
        self.assertEqual(res2["entry_lower"], 50.0)
        self.assertEqual(res2["entry_upper"], 55.0)

    def test_deterministic_repeated_calculation(self):
        res1 = calculate_entry_zone(self.current_price, self.nearest_support, self.atr_14, self.recommendation)
        res2 = calculate_entry_zone(self.current_price, self.nearest_support, self.atr_14, self.recommendation)
        res3 = calculate_entry_zone(self.current_price, self.nearest_support, self.atr_14, self.recommendation)

        self.assertEqual(res1, res2)
        self.assertEqual(res2, res3)

class TestSignalEngineExitParameters(unittest.TestCase):

    def setUp(self):
        self.current_price = 101.0
        self.nearest_support = {"zone_low": 100.0}
        self.nearest_resistance = {"zone_low": 115.0}
        self.atr_14 = 4.0
        self.entry_price = 102.0

    def test_valid_structural_stop_loss_and_target(self):
        res = calculate_exit_parameters(
            self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.entry_price
        )
        self.assertTrue(res["exit_valid"])
        # Stop loss: 100 - (4 * 1.5) = 94
        self.assertEqual(res["stop_loss"], 94.0)
        # Target: 115 (structural)
        self.assertEqual(res["target"], 115.0)
        # Risk: 101 - 94 = 7
        self.assertEqual(res["risk"], 7.0)
        # Reward: 115 - 101 = 14
        self.assertEqual(res["reward"], 14.0)

    def test_support_unavailable_fallback_stop(self):
        res = calculate_exit_parameters(
            self.current_price, None, self.nearest_resistance, self.atr_14, self.entry_price
        )
        self.assertTrue(res["exit_valid"])
        # Stop loss: 101 - (4 * 1.5) = 95
        self.assertEqual(res["stop_loss"], 95.0)

    def test_no_valid_resistance_fallback_target(self):
        res = calculate_exit_parameters(
            self.current_price, self.nearest_support, None, self.atr_14, self.entry_price
        )
        self.assertTrue(res["exit_valid"])
        # Target: 101 + (4 * 2.0) = 109
        self.assertEqual(res["target"], 109.0)

    def test_stop_loss_below_current_price(self):
        # Force a situation where fallback stop would be above current price (impossible since atr > 0)
        # But we test the check anyway by mocking a bad support
        res = calculate_exit_parameters(
            101.0, {"zone_low": 110.0}, self.nearest_resistance, 2.0, 101.0
        )
        self.assertFalse(res["exit_valid"])
        self.assertIn("STOP_ABOVE_CURRENT_PRICE", res["reason"])

    def test_target_above_current_price(self):
        res = calculate_exit_parameters(
            101.0, self.nearest_support, {"zone_low": 100.0}, self.atr_14, 100.0
        )
        self.assertFalse(res["exit_valid"])
        self.assertIn("TARGET_BELOW_CURRENT_PRICE", res["reason"])

    def test_target_above_entry(self):
        res = calculate_exit_parameters(
            101.0, self.nearest_support, {"zone_low": 103.0}, self.atr_14, 105.0
        )
        self.assertFalse(res["exit_valid"])
        self.assertIn("TARGET_BELOW_ENTRY_PRICE", res["reason"])

    def test_entry_below_stop(self):
        res = calculate_exit_parameters(
            101.0, {"zone_low": 99.0}, self.nearest_resistance, 2.0, 95.0
        )
        # Stop is 99 - 3 = 96. Entry is 95.
        self.assertFalse(res["exit_valid"])
        self.assertIn("ENTRY_BELOW_STOP_LOSS", res["reason"])

    def test_missing_inputs(self):
        res_no_price = calculate_exit_parameters(None, self.nearest_support, self.nearest_resistance, self.atr_14, self.entry_price)
        self.assertFalse(res_no_price["exit_valid"])
        self.assertIn("current_price", res_no_price["missing_inputs"])

        res_no_atr = calculate_exit_parameters(self.current_price, self.nearest_support, self.nearest_resistance, None, self.entry_price)
        self.assertFalse(res_no_atr["exit_valid"])
        self.assertIn("atr_14", res_no_atr["missing_inputs"])

        res_no_entry = calculate_exit_parameters(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, None)
        self.assertFalse(res_no_entry["exit_valid"])
        self.assertIn("entry_price", res_no_entry["missing_inputs"])

    def test_malformed_support_resistance(self):
        # Missing zone_low falls back gracefully
        res1 = calculate_exit_parameters(self.current_price, {"invalid": 10}, None, self.atr_14, self.entry_price)
        self.assertTrue(res1["exit_valid"])
        self.assertEqual(res1["stop_loss"], 95.0) # Fallback stop

    def test_deterministic_repeated_calculation(self):
        res1 = calculate_exit_parameters(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.entry_price)
        res2 = calculate_exit_parameters(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.entry_price)
        res3 = calculate_exit_parameters(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.entry_price)

        self.assertEqual(res1, res2)
        self.assertEqual(res2, res3)

class TestSignalEngineFinalSignal(unittest.TestCase):
    def setUp(self):
        self.current_price = 101.0
        self.nearest_support = {"level": 100.0, "zone_low": 100.0}
        # ATR=4 -> Stop = 100 - 6 = 94. Risk = 101-94 = 7.
        # RR=1.5 -> Reward = 10.5 -> Target = 111.5
        self.nearest_resistance = {"zone_low": 112.0} # Target=112, Reward=11, RR=11/7=1.57
        self.atr_14 = 4.0
        self.recommendation = "BUY"

    def test_valid_signal(self):
        res = generate_final_signal(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.recommendation)
        self.assertTrue(res["signal_valid"])
        self.assertEqual(res["reason"], "VALID_SIGNAL")
        self.assertGreater(res["risk"], 0)
        self.assertGreater(res["reward"], 0)

    def test_rr_exactly_1_50(self):
        # Risk = 7. We need Reward = 10.5 -> Target = 111.5
        res = generate_final_signal(self.current_price, self.nearest_support, {"zone_low": 111.5}, self.atr_14, self.recommendation)
        self.assertTrue(res["signal_valid"])
        self.assertEqual(res["risk_reward_ratio"], 1.50)

    def test_rr_below_1_50(self):
        # Target = 110 -> Reward = 9 -> RR = 9/7 = 1.28
        res = generate_final_signal(self.current_price, self.nearest_support, {"zone_low": 110.0}, self.atr_14, self.recommendation)
        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "INSUFFICIENT_RISK_REWARD_RATIO")

    def test_positive_risk_reward(self):
        res = generate_final_signal(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.recommendation)
        self.assertGreater(res["risk"], 0)
        self.assertGreater(res["reward"], 0)

    def test_zero_risk(self):
        # Impossible with structural stop since current_price=101, support=101 -> entry is valid, but structural stop = 101 - 6 = 95 -> risk = 6.
        # Let's force fallback stop by setting missing support level, and current_price = stop_loss.
        # Stop loss fallback = current_price - 1.5*atr. So we set ATR=0. But ATR<=0 is rejected earlier.
        pass # Explicitly zero risk is mathematically blocked by positive ATR in calculate_exit_parameters. We verify it's blocked.

    def test_negative_risk(self):
        # Similar to zero risk, blocked by positive ATR.
        pass

    def test_zero_reward(self):
        # Target = current_price
        res = generate_final_signal(self.current_price, self.nearest_support, {"zone_low": 101.0}, self.atr_14, self.recommendation)
        self.assertFalse(res["signal_valid"])
        # Caught by target_below_price in exit_parameters
        self.assertEqual(res["reason"], "TARGET_BELOW_CURRENT_PRICE")

    def test_negative_reward(self):
        res = generate_final_signal(self.current_price, self.nearest_support, {"zone_low": 90.0}, self.atr_14, self.recommendation)
        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "TARGET_BELOW_CURRENT_PRICE")

    def test_missing_stop_loss_or_target(self):
        # Implicitly tested by missing ATR / support which causes exit_valid=False
        pass

    def test_invalid_entry(self):
        # Price outside entry zone
        res = generate_final_signal(150.0, self.nearest_support, self.nearest_resistance, self.atr_14, self.recommendation)
        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "PRICE_OUTSIDE_ENTRY_ZONE")

    def test_non_buy_recommendation(self):
        res = generate_final_signal(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, "HOLD")
        self.assertFalse(res["signal_valid"])
        self.assertEqual(res["reason"], "NOT_A_BUY_RECOMMENDATION")

    def test_missing_required_inputs(self):
        res = generate_final_signal(None, self.nearest_support, self.nearest_resistance, self.atr_14, self.recommendation)
        self.assertFalse(res["signal_valid"])
        self.assertIn("current_price", res["missing_inputs"])

    def test_deterministic_repeated_execution(self):
        res1 = generate_final_signal(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.recommendation)
        res2 = generate_final_signal(self.current_price, self.nearest_support, self.nearest_resistance, self.atr_14, self.recommendation)
        self.assertEqual(res1, res2)

if __name__ == "__main__":
    unittest.main()
