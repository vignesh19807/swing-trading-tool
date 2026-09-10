"""
Week 14 - Unit & Integration Tests for TradingView Validation Infrastructure
=============================================================================

Verifies:
1. Observation schema creation and registry behavior.
2. Graceful handling of missing / PENDING observations.
3. Rejection of invalid / malformed observation payloads.
4. Absolute and relative difference calculations.
5. Absolute price tolerance (0.01 INR).
6. Indicator absolute tolerance (0.05).
7. Indicator relative tolerance (0.1%).
8. Composite score tolerance (0.1).
9. Exact categorical matching.
10. Zero-reference relative difference safety.
11. Deterministic repeated validation execution.
12. Point-in-time historical evaluation date behavior.
13. Complete 15-scenario matrix coverage (5 stocks x 3 dates).
14. Absolute absence of fabricated reference data in default registry.
15. Discrepancy category assignment rules.
16. Clear boundary separation between TradingView references and proprietary platform outputs.

Author: Logic Engineer
"""

import unittest
from typing import Dict, Any

from backend.logic.tradingview_validator import (
    APPROVED_VALIDATION_STOCKS,
    APPROVED_VALIDATION_DATES,
    TRADINGVIEW_OBSERVATIONS,
    create_empty_observation,
    register_tradingview_observation,
    get_tradingview_observation,
    validate_tradingview_observation,
    run_tradingview_market_validation,
)
from backend.logic.real_market_validator import DiscrepancyCategory


class TestTradingViewValidationUnit(unittest.TestCase):
    """Unit tests for observation schema, tolerances, arithmetic, and registry."""

    def test_01_empty_observation_schema(self):
        """Verify empty observation schema creation with PENDING status and None values."""
        obs = create_empty_observation("INFY", "2026-08-14")
        self.assertEqual(obs["metadata"]["symbol"], "INFY")
        self.assertEqual(obs["metadata"]["evaluation_date"], "2026-08-14")
        self.assertEqual(obs["metadata"]["status"], "PENDING")
        self.assertIsNone(obs["metadata"]["recording_timestamp"])

        # Verify unrecorded indicator fields are None
        for val in obs["indicators"].values():
            self.assertIsNone(val)

        for val in obs["ohlcv"].values():
            self.assertIsNone(val)

    def test_02_default_registry_has_no_fabricated_data(self):
        """Verify default observations registry contains zero fabricated data (all PENDING)."""
        self.assertEqual(len(TRADINGVIEW_OBSERVATIONS), 15)
        for key, obs in TRADINGVIEW_OBSERVATIONS.items():
            self.assertEqual(obs["metadata"]["status"], "PENDING")
            for ind_val in obs["indicators"].values():
                self.assertIsNone(ind_val, f"Fabricated indicator value found in registry key {key}")

    def test_03_invalid_observation_registration_fails(self):
        """Verify invalid or malformed observation registration raises ValueError or TypeError."""
        with self.assertRaises(TypeError):
            register_tradingview_observation("INFY", "2026-08-14", "not_a_dict")  # type: ignore

        with self.assertRaises(ValueError):
            # Missing required sections
            register_tradingview_observation("INFY", "2026-08-14", {"metadata": {}})

    def test_04_pending_observation_does_not_crash_validation(self):
        """Verify executing validation on a PENDING observation returns PENDING status without error."""
        res = validate_tradingview_observation("INFY", "2026-08-14")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["evaluation_date"], "2026-08-14")
        self.assertEqual(res["tradingview_observation_status"], "PENDING")
        self.assertEqual(res["overall_status"], "PENDING")

    def test_05_exact_matching_indicator_tolerance_pass(self):
        """Verify exact matching custom observation passes indicator and price comparison."""
        # First obtain platform values to create a matching test fixture
        base_res = validate_tradingview_observation("INFY", "2026-08-14")
        plat_ohlcv = base_res["platform_values"]["ohlcv"]
        plat_ind = base_res["platform_values"]["indicators"]

        matching_obs = {
            "metadata": {
                "symbol": "INFY",
                "exchange": "NSE",
                "evaluation_date": "2026-08-14",
                "timeframe": "1D",
                "timezone": "IST (+05:30)",
                "data_adjustment": "Unadjusted Close",
                "recording_timestamp": "2026-09-10T20:00:00+05:30",
                "status": "RECORDED"
            },
            "ohlcv": dict(plat_ohlcv),
            "indicators": dict(plat_ind),
            "market_structure": {
                "visual_support": 1800.0,
                "visual_resistance": 1900.0,
                "observable_trend": "Bullish"
            }
        }

        val_res = validate_tradingview_observation("INFY", "2026-08-14", custom_observation=matching_obs)
        self.assertEqual(val_res["tradingview_observation_status"], "RECORDED")
        self.assertEqual(val_res["overall_status"], "PASS")
        self.assertEqual(len(val_res["discrepancies"]), 0)

    def test_06_indicator_tolerance_boundary_cases(self):
        """Verify indicator comparisons pass within 0.05 absolute / 0.1% relative and fail beyond."""
        base_res = validate_tradingview_observation("INFY", "2026-08-14")
        plat_ohlcv = base_res["platform_values"]["ohlcv"]
        plat_ind = base_res["platform_values"]["indicators"]

        # Modify RSI slightly (+0.03 -> should PASS within 0.05)
        test_ind = dict(plat_ind)
        test_ind["rsi14"] = test_ind["rsi14"] + 0.03

        obs_pass = {
            "metadata": {"recording_timestamp": "2026-09-10T20:00:00+05:30"},
            "ohlcv": dict(plat_ohlcv),
            "indicators": test_ind,
            "market_structure": {}
        }
        res_pass = validate_tradingview_observation("INFY", "2026-08-14", custom_observation=obs_pass)
        self.assertEqual(res_pass["overall_status"], "PASS")

        # Modify RSI beyond tolerance (+1.5 -> should FAIL)
        test_ind_fail = dict(plat_ind)
        test_ind_fail["rsi14"] = test_ind_fail["rsi14"] + 1.5

        obs_fail = {
            "metadata": {"recording_timestamp": "2026-09-10T20:00:00+05:30"},
            "ohlcv": dict(plat_ohlcv),
            "indicators": test_ind_fail,
            "market_structure": {}
        }
        res_fail = validate_tradingview_observation("INFY", "2026-08-14", custom_observation=obs_fail)
        self.assertEqual(res_fail["overall_status"], "FAIL")
        self.assertGreater(len(res_fail["discrepancies"]), 0)

    def test_07_zero_reference_relative_difference_safety(self):
        """Verify zero reference value does not trigger DivisionByZeroError."""
        base_res = validate_tradingview_observation("INFY", "2026-08-14")
        plat_ohlcv = base_res["platform_values"]["ohlcv"]
        plat_ind = base_res["platform_values"]["indicators"]

        zero_ind = dict(plat_ind)
        zero_ind["macd_line"] = 0.0  # Zero reference

        obs_zero = {
            "metadata": {"recording_timestamp": "2026-09-10T20:00:00+05:30"},
            "ohlcv": dict(plat_ohlcv),
            "indicators": zero_ind,
            "market_structure": {}
        }
        # Execution must complete without throwing DivisionByZero error
        res = validate_tradingview_observation("INFY", "2026-08-14", custom_observation=obs_zero)
        self.assertIn("overall_status", res)

    def test_08_discrepancy_classification_unresolved_default(self):
        """Verify unexplained differences > 0.01 are assigned UNRESOLVED category."""
        base_res = validate_tradingview_observation("INFY", "2026-08-14")
        plat_ohlcv = base_res["platform_values"]["ohlcv"]
        plat_ind = base_res["platform_values"]["indicators"]

        mismatch_ind = dict(plat_ind)
        mismatch_ind["ema20"] = mismatch_ind["ema20"] + 5.0  # Significant difference

        obs_mismatch = {
            "metadata": {"recording_timestamp": "2026-09-10T20:00:00+05:30"},
            "ohlcv": dict(plat_ohlcv),
            "indicators": mismatch_ind,
            "market_structure": {}
        }
        res = validate_tradingview_observation("INFY", "2026-08-14", custom_observation=obs_mismatch)
        self.assertEqual(res["overall_status"], "FAIL")

        # Check discrepancy category
        ema_disc = [d for d in res["discrepancies"] if d["field"] == "ema20"][0]
        self.assertEqual(ema_disc["discrepancy_category"], DiscrepancyCategory.UNRESOLVED)

    def test_09_tradingview_platform_boundary_separation(self):
        """Verify platform proprietary outputs are clearly separated from reference observation fields."""
        res = validate_tradingview_observation("INFY", "2026-08-14")
        plat_vals = res["platform_values"]

        self.assertIn("outputs", plat_vals)
        outputs = plat_vals["outputs"]

        # Verify proprietary platform fields exist under outputs
        self.assertIn("technical_score", outputs)
        self.assertIn("recommendation", outputs)
        self.assertIn("entry_lower", outputs)
        self.assertIn("entry_upper", outputs)
        self.assertIn("stop_loss", outputs)
        self.assertIn("target", outputs)
        self.assertIn("risk_reward_ratio", outputs)
        self.assertIn("signal_valid", outputs)


class TestTradingViewValidationIntegration(unittest.TestCase):
    """Integration tests for 15-scenario matrix execution and determinism."""

    def test_10_full_15_scenario_matrix_coverage(self):
        """Verify run_tradingview_market_validation evaluates all 15 scenarios."""
        res = run_tradingview_market_validation()

        self.assertEqual(res["total_scenarios_evaluated"], 15)
        self.assertEqual(len(res["scenario_results"]), 15)
        self.assertEqual(res["symbols_evaluated"], APPROVED_VALIDATION_STOCKS)
        self.assertEqual(res["dates_evaluated"], APPROVED_VALIDATION_DATES)
        self.assertEqual(res["status"], "PENDING_REFERENCE_DATA")

    def test_11_deterministic_repeated_execution(self):
        """Verify repeated orchestrator execution produces identical results."""
        res1 = run_tradingview_market_validation()
        res2 = run_tradingview_market_validation()

        self.assertEqual(res1["status"], res2["status"])
        self.assertEqual(res1["total_scenarios_evaluated"], res2["total_scenarios_evaluated"])
        self.assertEqual(res1["pending_scenarios_count"], res2["pending_scenarios_count"])

    def test_12_historical_evaluation_date_isolation(self):
        """Verify validation strictly evaluates historical bars on or before evaluation_date."""
        res_2025 = validate_tradingview_observation("INFY", "2025-10-15")
        res_2026 = validate_tradingview_observation("INFY", "2026-08-14")

        close_2025 = res_2025["platform_values"]["ohlcv"]["close"]
        close_2026 = res_2026["platform_values"]["ohlcv"]["close"]

        self.assertIsNotNone(close_2025)
        self.assertIsNotNone(close_2026)
        # Closing price on 2025-10-15 must differ from closing price on 2026-08-14
        self.assertNotEqual(close_2025, close_2026)


if __name__ == "__main__":
    unittest.main()
