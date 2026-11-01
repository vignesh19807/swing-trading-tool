"""
Audit-048 Targeted Regression Test Suite:
Validates Research Filter Integration, Corporate Action Diagnostics,
Transaction Cost Model Verification, and Complete Market Data Classification.
"""

import unittest
import pandas as pd
import numpy as np

from backend.data_pipeline.research_market_data_filter import (
    KNOWN_EXCHANGE_HOLIDAYS,
    detect_market_data_anomalies,
    filter_research_market_data,
)
from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.backtesting_dataset_service import build_backtesting_dataset
from backend.data_pipeline.backtest_data_access_service import get_backtest_input, get_backtest_inputs
from backend.logic.cost_model import calculate_trade_costs, CostModelConfig
from backend.data_pipeline.universe_metadata import (
    CorporateActionRecord,
    UniverseConstituentRecord,
    ResearchUniverseMetadata,
)


class TestAudit048ResearchPipelineAndVerification(unittest.TestCase):
    """
    Dedicated tests for AUDIT-048:
    1. Research filter integration through get_historical_data, build_backtesting_dataset, and get_backtest_inputs
    2. Corporate action discontinuity detection and verification status
    3. Transaction cost model tariff alignment and fee breakdown
    4. False-positive checks for normal low-volatility vs synthetic holiday sessions
    """

    # =========================================================================
    # PHASE 2: Research Filter Integration
    # =========================================================================

    def test_01_historical_data_service_filter_integration(self):
        """Verify get_historical_data excludes synthetic holiday bars when filter_synthetic_holidays=True."""
        # 2025-03-18 is Holi (51 flat bars in raw data)
        raw_res = get_historical_data("INFY", start_date="2025-03-17", end_date="2025-03-19", filter_synthetic_holidays=False)
        raw_dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in raw_res["data"]["date"].tolist()]
        self.assertIn("2025-03-18", raw_dates)

        filtered_res = get_historical_data("INFY", start_date="2025-03-17", end_date="2025-03-19", filter_synthetic_holidays=True)
        filtered_dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in filtered_res["data"]["date"].tolist()]
        self.assertNotIn("2025-03-18", filtered_dates)
        self.assertEqual(len(filtered_dates), len(raw_dates) - 1)

    def test_02_build_backtesting_dataset_filter_integration(self):
        """Verify build_backtesting_dataset propagates filter_synthetic_holidays to dataset generation."""
        raw_ds = build_backtesting_dataset("TCS", start_date="2025-03-17", end_date="2025-03-19", filter_synthetic_holidays=False)
        self.assertIn("2025-03-18", raw_ds["evaluation_date"].tolist())

        filtered_ds = build_backtesting_dataset("TCS", start_date="2025-03-17", end_date="2025-03-19", filter_synthetic_holidays=True)
        self.assertNotIn("2025-03-18", filtered_ds["evaluation_date"].tolist())

    def test_03_backtest_data_access_service_filter_integration(self):
        """Verify get_backtest_inputs excludes synthetic holiday dates when filter_synthetic_holidays=True."""
        raw_inputs = get_backtest_inputs("WIPRO", start_date="2025-03-17", end_date="2025-03-19", filter_synthetic_holidays=False)
        raw_dates = [r["evaluation_date"] for r in raw_inputs]
        self.assertIn("2025-03-18", raw_dates)

        filtered_inputs = get_backtest_inputs("WIPRO", start_date="2025-03-17", end_date="2025-03-19", filter_synthetic_holidays=True)
        filtered_dates = [r["evaluation_date"] for r in filtered_inputs]
        self.assertNotIn("2025-03-18", filtered_dates)

    # =========================================================================
    # PHASE 3: Corporate-Action Anomalies & Verification
    # =========================================================================

    def test_04_tmpv_demerger_anomaly_detected(self):
        """Verify TMPV price drop on 2025-10-14 is flagged as LARGE_PRICE_DISCONTINUITY."""
        tmpv_sample = pd.DataFrame([
            {"symbol": "TMPV", "date": "2025-10-13", "open": 679.0, "high": 685.0, "low": 655.0, "close": 660.75, "volume": 33288645},
            {"symbol": "TMPV", "date": "2025-10-14", "open": 400.0, "high": 415.0, "low": 390.0, "close": 395.45, "volume": 52267874},
        ])
        annotated = detect_market_data_anomalies(tmpv_sample)
        self.assertTrue(annotated.iloc[1]["is_large_discontinuity"])
        self.assertEqual(annotated.iloc[1]["anomaly_classification"], "LARGE_PRICE_DISCONTINUITY")

    def test_05_trent_unadjusted_movement_detected(self):
        """Verify TRENT price drop on 2026-01-01 is flagged as LARGE_PRICE_DISCONTINUITY."""
        trent_sample = pd.DataFrame([
            {"symbol": "TRENT", "date": "2025-12-31", "open": 4225.0, "high": 4290.0, "low": 4210.0, "close": 4279.0, "volume": 426359},
            {"symbol": "TRENT", "date": "2026-01-01", "open": 2852.67, "high": 2890.0, "low": 2840.0, "close": 2864.93, "volume": 561898},
        ])
        annotated = detect_market_data_anomalies(trent_sample)
        self.assertTrue(annotated.iloc[1]["is_large_discontinuity"])
        self.assertEqual(annotated.iloc[1]["anomaly_classification"], "LARGE_PRICE_DISCONTINUITY")

    # =========================================================================
    # PHASE 4: Transaction Cost Model Verification
    # =========================================================================

    def test_06_cost_model_buy_side_statutory_charges(self):
        """Verify buy-side costs include STT (0.1%), NSE (0.00297%), SEBI (₹10/cr), Stamp Duty (0.015%), GST (18%)."""
        costs = calculate_trade_costs(price=1000.0, quantity=100, is_buy=True)
        turnover = 100000.0
        self.assertEqual(costs["turnover"], turnover)
        self.assertAlmostEqual(costs["stt"], 100.0, places=2)           # 0.1%
        self.assertAlmostEqual(costs["exchange_charges"], 2.97, places=2) # 0.00297%
        self.assertAlmostEqual(costs["sebi_charges"], 0.10, places=2)    # 0.0001%
        self.assertAlmostEqual(costs["stamp_duty"], 15.00, places=2)     # 0.015%
        # GST = 18% on (Brokerage + Exchange + SEBI) = 0.18 * 3.07 = 0.5526
        self.assertAlmostEqual(costs["gst"], 0.5526, places=2)

    def test_07_cost_model_sell_side_zero_stamp_duty(self):
        """Verify sell-side costs include STT and turnover fees but ZERO stamp duty."""
        costs = calculate_trade_costs(price=1000.0, quantity=100, is_buy=False)
        self.assertEqual(costs["stamp_duty"], 0.0)
        self.assertAlmostEqual(costs["stt"], 100.0, places=2)

    # =========================================================================
    # PHASE 5: False-Positive & Anomaly Detection Sanity
    # =========================================================================

    def test_08_legitimate_low_volatility_session_not_flagged_as_synthetic(self):
        """Verify that a legitimate low-volatility session with non-zero volume is classified as NORMAL_SESSION."""
        normal_bar = pd.DataFrame([
            {"symbol": "STABLE", "date": "2025-06-10", "open": 500.0, "high": 501.0, "low": 499.5, "close": 500.2, "volume": 25000}
        ])
        annotated = detect_market_data_anomalies(normal_bar)
        self.assertEqual(annotated.iloc[0]["anomaly_classification"], "NORMAL_SESSION")
        self.assertFalse(annotated.iloc[0]["is_synthetic_holiday"])

    def test_09_flat_bar_on_normal_session_classified_as_stale_not_holiday(self):
        """Verify flat bar on non-holiday is classified as STALE_FLAT_BAR, not SYNTHETIC_HOLIDAY_BAR."""
        stale_bar = pd.DataFrame([
            {"symbol": "ETERNAL", "date": "2025-04-11", "open": 211.39, "high": 211.39, "low": 211.39, "close": 211.39, "volume": 0}
        ])
        annotated = detect_market_data_anomalies(stale_bar)
        self.assertTrue(annotated.iloc[0]["is_stale_flat_bar"])
        self.assertFalse(annotated.iloc[0]["is_synthetic_holiday"])
        self.assertEqual(annotated.iloc[0]["anomaly_classification"], "STALE_FLAT_BAR")


if __name__ == "__main__":
    unittest.main()
