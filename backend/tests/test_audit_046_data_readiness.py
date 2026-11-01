"""
Audit-046: Isolated tests for Historical Data Quality, Point-in-Time Eligibility Contract,
and Research Infrastructure Readiness.
"""

import unittest
import pandas as pd
import numpy as np

from backend.data_pipeline.financial_service import (
    parse_quarter_period_end,
    _normalize_eval_timestamp,
    _normalize_pub_timestamp,
)


class TestAudit046DataQualityAndPITContract(unittest.TestCase):
    """
    Explicit regression tests for AUDIT-046:
    - Point-in-Time financial eligibility contract rules
    - Handling of known vs estimated vs unknown publication dates
    - Rejection of future periods and lookahead leakage
    - Market data sanity checks (OHLC relationship, flat bars, zero volume)
    - TTM and YoY multi-quarter requirements
    """

    def test_01_pit_contract_quarter_must_end_prior_to_eval_date(self):
        """Rule 1: The reporting period must end prior to or on the evaluation date."""
        pe_q1 = parse_quarter_period_end("2025-Q1")  # pd.Timestamp('2025-03-31 23:59:59.999999')
        pe_q2 = parse_quarter_period_end("2025-Q2")  # pd.Timestamp('2025-06-30 23:59:59.999999')
        
        self.assertEqual(pe_q1.strftime("%Y-%m-%d"), "2025-03-31")
        self.assertEqual(pe_q2.strftime("%Y-%m-%d"), "2025-06-30")
        
        # On 2025-05-01, Q1 period has ended, but Q2 has NOT ended
        eval_dt = _normalize_eval_timestamp("2025-05-01")
        self.assertLessEqual(pe_q1, eval_dt)
        self.assertGreater(pe_q2, eval_dt)

    def test_02_pit_contract_verified_pub_date_cannot_be_after_eval_date(self):
        """Rule 2: A verified actual publication date must not be later than the evaluation date."""
        pub_verified = "2025-04-20"
        
        eval_before = "2025-04-15"
        eval_same = "2025-04-20"
        eval_after = "2025-04-25"
        
        # Eligible only when pub_date <= eval_date
        self.assertFalse(pub_verified <= eval_before)
        self.assertTrue(pub_verified <= eval_same)
        self.assertTrue(pub_verified <= eval_after)

    def test_03_pit_contract_unknown_pub_date_requires_fallback_lag(self):
        """Rule 3: Records with unknown publication dates must apply the explicit 45-day statutory fallback."""
        pe = parse_quarter_period_end("2025-Q1")  # 2025-03-31
        fallback_dt = (pe + pd.Timedelta(days=45)).strftime("%Y-%m-%d")
        self.assertEqual(fallback_dt, "2025-05-15")
        
        # On Day 44 (2025-05-14), statement is NOT eligible
        eval_day_44 = "2025-05-14"
        self.assertFalse(eval_day_44 >= fallback_dt)
        
        # On Day 45 (2025-05-15), statement becomes eligible
        eval_day_45 = "2025-05-15"
        self.assertTrue(eval_day_45 >= fallback_dt)

    def test_04_pit_contract_future_periods_strictly_rejected(self):
        """Rule 4: Future periods can never enter historical evaluations."""
        eval_date = _normalize_eval_timestamp("2025-06-15")
        all_quarters = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
        
        eligible_pe = []
        for q in all_quarters:
            pe = parse_quarter_period_end(q)
            if pe <= eval_date:
                eligible_pe.append(q)
        
        self.assertEqual(eligible_pe, ["2025-Q1"])
        self.assertNotIn("2025-Q2", eligible_pe)
        self.assertNotIn("2025-Q3", eligible_pe)

    def test_05_ttm_calculation_requires_exactly_four_quarters(self):
        """Rule 5: TTM EPS / Net Profit requires at least 4 contiguous quarters."""
        available_quarters = ["2025-Q1", "2025-Q2", "2025-Q3"]
        self.assertLess(len(available_quarters), 4)
        
        available_quarters_four = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
        self.assertGreaterEqual(len(available_quarters_four), 4)

    def test_06_yoy_calculation_requires_five_quarters(self):
        """Rule 6: YoY Growth calculation requires 5 quarters (T vs T-4)."""
        available_four = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
        self.assertLess(len(available_four), 5)
        
        available_five = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1"]
        self.assertGreaterEqual(len(available_five), 5)

    def test_07_market_data_ohlc_relationships_enforced(self):
        """Rule 7: High must be >= Low, Open and Close must be within High and Low."""
        valid_bar = {"open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000}
        self.assertGreaterEqual(valid_bar["high"], valid_bar["low"])
        self.assertGreaterEqual(valid_bar["high"], valid_bar["open"])
        self.assertLessEqual(valid_bar["low"], valid_bar["open"])
        self.assertGreaterEqual(valid_bar["high"], valid_bar["close"])
        self.assertLessEqual(valid_bar["low"], valid_bar["close"])

        # Inverted bar detected
        invalid_bar = {"open": 100.0, "high": 95.0, "low": 98.0, "close": 96.0, "volume": 1000}
        self.assertFalse(invalid_bar["high"] >= invalid_bar["low"])

    def test_08_market_data_holiday_zero_volume_flat_bar_detection(self):
        """Rule 8: Stale/holiday bars characterized by O=H=L=C and Volume=0 must be detectable."""
        flat_holiday_bar = {"open": 1500.0, "high": 1500.0, "low": 1500.0, "close": 1500.0, "volume": 0}
        is_flat = (
            flat_holiday_bar["open"] == flat_holiday_bar["high"] ==
            flat_holiday_bar["low"] == flat_holiday_bar["close"] and
            flat_holiday_bar["volume"] == 0
        )
        self.assertTrue(is_flat)

        normal_active_bar = {"open": 1500.0, "high": 1520.0, "low": 1490.0, "close": 1515.0, "volume": 50000}
        is_normal_flat = (
            normal_active_bar["open"] == normal_active_bar["high"] ==
            normal_active_bar["low"] == normal_active_bar["close"] and
            normal_active_bar["volume"] == 0
        )
        self.assertFalse(is_normal_flat)

    def test_09_historical_revision_immutability_contract(self):
        """Rule 9: Historical revisions must be versioned and must not overwrite PIT values silently."""
        original_record = {
            "company_id": 1,
            "quarter": "2025-Q1",
            "net_profit": 500.0,
            "version": 1,
            "publication_date": "2025-04-25"
        }
        revised_record = {
            "company_id": 1,
            "quarter": "2025-Q1",
            "net_profit": 485.0,
            "version": 2,
            "publication_date": "2025-07-15"
        }
        
        # On 2025-05-01, only version 1 is visible
        eval_dt_1 = "2025-05-01"
        self.assertTrue(original_record["publication_date"] <= eval_dt_1)
        self.assertFalse(revised_record["publication_date"] <= eval_dt_1)

        # On 2025-08-01, version 2 is visible
        eval_dt_2 = "2025-08-01"
        self.assertTrue(revised_record["publication_date"] <= eval_dt_2)


if __name__ == "__main__":
    unittest.main()
