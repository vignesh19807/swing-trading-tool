"""
Week 13 - Unit & Integration Tests for Real-Market Validation
=============================================================

Verifies:
1. Reference mathematical calculations (RSI, EMA, MACD, ATR, Opportunity Score)
2. Market regime assessment logic (Bullish, Bearish, Sideways)
3. Signal behavior classification logic
4. Single stock & date validation execution
5. Full multi-stock / multi-period market validation
6. Deterministic repeated execution

Author: Logic Engineer
"""

import unittest
import pandas as pd
import numpy as np

from backend.logic.real_market_validator import (
    ref_calculate_rsi,
    ref_calculate_ema,
    ref_calculate_macd,
    ref_calculate_atr,
    ref_calculate_opportunity_score,
    assess_market_regime,
    assess_signal_behavior,
    validate_stock_date,
    run_full_market_validation,
    BehaviorClassification,
)


class TestRealMarketValidatorUnit(unittest.TestCase):
    """Unit tests for mathematical reference calculations and regime/behavior assessors."""

    def test_ref_calculate_rsi(self):
        """Test independent Wilder's RSI calculation."""
        prices = pd.Series([10.0 + i * 0.5 for i in range(20)])  # Monotonically increasing prices
        rsi = ref_calculate_rsi(prices, period=14)
        self.assertEqual(len(rsi), 20)
        self.assertTrue(pd.isna(rsi.iloc[13]))  # Warm-up period NaN
        self.assertEqual(rsi.iloc[-1], 100.0)    # Constant positive gains -> 100.0

    def test_ref_calculate_ema(self):
        """Test independent EMA calculation."""
        prices = pd.Series([100.0] * 25)
        ema20 = ref_calculate_ema(prices, period=20)
        self.assertEqual(len(ema20), 25)
        self.assertAlmostEqual(ema20.iloc[-1], 100.0, places=4)

    def test_ref_calculate_macd(self):
        """Test independent MACD calculation."""
        prices = pd.Series([10.0 + i for i in range(30)])
        macd_df = ref_calculate_macd(prices, fast=12, slow=26, signal=9)
        self.assertIn("macd", macd_df.columns)
        self.assertIn("signal", macd_df.columns)
        self.assertIn("histogram", macd_df.columns)

    def test_ref_calculate_atr(self):
        """Test independent ATR calculation."""
        high = pd.Series([105.0] * 20)
        low = pd.Series([95.0] * 20)
        close = pd.Series([100.0] * 20)
        atr14 = ref_calculate_atr(high, low, close, period=14)
        self.assertEqual(len(atr14), 20)
        self.assertAlmostEqual(atr14.iloc[-1], 10.0, places=4)

    def test_ref_opportunity_score(self):
        """Test Opportunity Score weighted calculation formula."""
        # 40% Tech (80), 35% Fin (70), 25% Mom (60) = 32 + 24.5 + 15 = 71.5
        score = ref_calculate_opportunity_score(80.0, 70.0, 60.0)
        self.assertEqual(score, 71.5)

    def test_assess_market_regime(self):
        """Test objective market regime categorization."""
        # Bullish prices
        bull_df = pd.DataFrame({
            "close": [100.0 + i * 2.0 for i in range(250)]
        })
        regime = assess_market_regime(bull_df)
        self.assertEqual(regime, "BULLISH")

    def test_assess_signal_behavior(self):
        """Test signal behavior classification mapping."""
        b1 = assess_signal_behavior("BULLISH", "BUY", True, True, "VALID")
        self.assertEqual(b1, BehaviorClassification.STRONG_SIGNAL)

        b2 = assess_signal_behavior("BEARISH", "AVOID", False, False, "VALID")
        self.assertEqual(b2, BehaviorClassification.APPROPRIATE_AVOIDANCE)

        b3 = assess_signal_behavior("BULLISH", "INSUFFICIENT_DATA", False, False, "INSUFFICIENT")
        self.assertEqual(b3, BehaviorClassification.INSUFFICIENT_DATA)


class TestRealMarketValidatorIntegration(unittest.TestCase):
    """Live DB Integration tests for Real-Market Validation."""

    def test_live_infy_validation(self):
        """Test validation execution for INFY on 2026-08-14."""
        res = validate_stock_date("INFY", "2026-08-14")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["evaluation_date"], "2026-08-14")
        self.assertIn("regime", res)
        self.assertIn("behavior", res)
        self.assertIn("technical_summary", res)
        self.assertIn("decision_summary", res)

    def test_full_market_validation_determinism(self):
        """Test deterministic execution of full multi-stock market validation."""
        res1 = run_full_market_validation(["INFY", "TCS"], ["2026-08-14"])
        res2 = run_full_market_validation(["INFY", "TCS"], ["2026-08-14"])

        self.assertEqual(res1["total_cases_evaluated"], 2)
        self.assertEqual(res1["status"], res2["status"])
        self.assertEqual(res1["regime_distribution"], res2["regime_distribution"])
        self.assertEqual(res1["behavior_distribution"], res2["behavior_distribution"])


if __name__ == "__main__":
    unittest.main()
