"""
Test Suite: Historical Financial Data Safety & Lookahead Bias Audit
===================================================================

Audits and verifies:
1. Historical dates before a quarter ends (must not use that quarter).
2. Historical dates after quarter-end but before plausible publication date
   (documents current availability assumptions and limitations).
3. Historical dates after publication (quarter is available).
4. Missing financial data behavior (returns explicit status, not crashing).
5. Invalid reporting period format resilience.
6. Lookahead leakage check guarantee.
"""

import unittest
import pandas as pd
from datetime import datetime
from backend.data_pipeline.backtesting_dataset_service import (
    build_backtesting_dataset,
    _prepare_financial_data,
)
from backend.data_pipeline.financial_service import get_latest_financial_data
from backend.data_pipeline.backtest_data_access_service import get_backtest_inputs


class TestHistoricalFinancialSafety(unittest.TestCase):
    """Rigorous audit of point-in-time financial safety and lookahead bias."""

    def test_01_dates_before_quarter_end(self):
        """
        On 2025-06-15 (Q2 ends on 2025-06-30), the pipeline must NEVER select
        2025-Q2. It must select 2025-Q1 or earlier.
        """
        # Testing synthetic financial frame
        fin_df = pd.DataFrame([
            {"quarter": "2025-Q1", "revenue": 100, "net_profit": 10},
            {"quarter": "2025-Q2", "revenue": 120, "net_profit": 15},
            {"quarter": "2025-Q3", "revenue": 130, "net_profit": 18},
        ])

        # Evaluate on 2025-06-15 (before Q2 end)
        rec, status = _prepare_financial_data(fin_df, "2025-06-15")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["quarter"], "2025-Q1", "Selected 2025-Q2 before it ended!")

    def test_02_dates_at_quarter_end(self):
        """
        On 2025-06-30 (00:00:00), 2025-Q2 period ends at 23:59:59.999999.
        Therefore, during the trading session of 2025-06-30, Q2 is not yet closed,
        so the system conservatively chooses 2025-Q1.
        Starting on 2025-07-01, 2025-Q2 is eligible.
        """
        fin_df = pd.DataFrame([
            {"quarter": "2025-Q1", "revenue": 100},
            {"quarter": "2025-Q2", "revenue": 120},
        ])
        # On 2025-06-30 (midnight), Q2 is not completed
        rec, status = _prepare_financial_data(fin_df, "2025-06-30")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["quarter"], "2025-Q1")

        # On 2025-07-01, Q2 is closed and eligible
        rec_next, status_next = _prepare_financial_data(fin_df, "2025-07-01")
        self.assertIsNotNone(rec_next)
        self.assertEqual(rec_next["quarter"], "2025-Q2")

    def test_03_publication_lag_limitation_documentation(self):
        """
        DEMONSTRATE THE EXISTING ASSUMPTION & LIMITATION:
        In Indian equities (SEBI regulations), Q1/Q2/Q3 results are typically announced
        within 45 days after quarter-end (e.g. Q2 ending June 30 is reported in July/August).
        The current platform database schema `quarterly_results` stores only `quarter`
        (e.g., '2025-Q2') without an announcement_date column.
        
        This test asserts that while period-leakage is strictly prevented,
        the system explicitly flags availability as 'PERIOD_ELIGIBLE_AVAILABILITY_UNVERIFIED'
        or 'UNVERIFIED'.
        """
        fin_df = pd.DataFrame([
            {"quarter": "2025-Q1", "revenue": 100},
            {"quarter": "2025-Q2", "revenue": 120},
        ])
        # On July 5, 2025 (5 days after quarter end, before earnings call),
        # 2025-Q2 is selected because quarter_date <= eval_date, but status warns it is unverified
        rec, status = _prepare_financial_data(fin_df, "2025-07-05")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["quarter"], "2025-Q2")
        self.assertEqual(status, "PERIOD_ELIGIBLE_AVAILABILITY_UNVERIFIED")

    def test_04_missing_financial_data_handling(self):
        """Missing or empty financial dataframe must return explicit MISSING status."""
        rec, status = _prepare_financial_data(None, "2025-07-05")
        self.assertIsNone(rec)
        self.assertEqual(status, "MISSING")

        rec, status = _prepare_financial_data(pd.DataFrame(), "2025-07-05")
        self.assertIsNone(rec)
        self.assertEqual(status, "MISSING")

    def test_05_invalid_reporting_period_resilience(self):
        """Corrupted quarter string must be skipped safely without crashing."""
        fin_df = pd.DataFrame([
            {"quarter": "INVALID_Q", "revenue": 100},
            {"quarter": "2025-Q1", "revenue": 110},
        ])
        rec, status = _prepare_financial_data(fin_df, "2025-07-05")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["quarter"], "2025-Q1")

    def test_06_real_database_backtest_inputs_leakage_check(self):
        """
        Verify across representative stocks in the real database that no record
        in get_backtest_inputs leaks future quarterly financial data.
        """
        test_stocks = ["INFY", "TCS", "WIPRO", "RELIANCE"]
        for symbol in test_stocks:
            records = get_backtest_inputs(symbol, "2025-06-01", "2025-08-31")
            for rec in records:
                eval_date = str(rec["evaluation_date"])[:10]
                reporting_period = rec.get("reporting_period")
                if reporting_period:
                    period_end = str(pd.Period(reporting_period).end_time.date())
                    self.assertLessEqual(
                        period_end,
                        eval_date,
                        f"Lookahead leak in {symbol} on {eval_date}: got {reporting_period} (ends {period_end})"
                    )
                self.assertEqual(rec.get("leakage_check"), "PASS")


if __name__ == "__main__":
    unittest.main()
