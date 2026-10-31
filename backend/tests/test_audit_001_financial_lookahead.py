"""
Test Suite: AUDIT-001 Historical Financial Data Lookahead Bias
=============================================================

Comprehensive regression tests for AUDIT-001:
Verifies that historical stock evaluations use only financial information
that was publicly available on or before the evaluation date/time.

Covers all 9 required audit test specifications:
1. Exclude future reporting quarter
2. Exclude result published after evaluation
3. Include result published before evaluation
4. Respect publication-time boundaries (intraday timestamps & EOD date semantics)
5. Handle missing publication dates (honest unverified fallback tagging via statutory lag)
6. Preserve latest-data behavior when evaluation_date is None
7. Verify year and quarter transition boundaries (Dec/Jan, Mar/Apr, Jun/Jul, Sep/Oct)
8. Verify evaluation-date propagation through downstream services
9. Point-in-time stability: adding later-published data cannot alter earlier evaluations
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from backend.data_pipeline.financial_service import (
    get_latest_financial_data,
    parse_quarter_period_end,
)
from backend.data_pipeline.stock_snapshot_service import get_stock_snapshot


class TestAudit001FinancialLookahead(unittest.TestCase):
    """Rigorous point-in-time financial data availability tests."""

    def setUp(self):
        """Create an isolated temporary SQLite database for each test."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)

        self.conn = sqlite3.connect(self.temp_db_path)
        cur = self.conn.cursor()

        # Create companies table
        cur.execute(
            """
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                sector TEXT,
                industry TEXT,
                exchange TEXT,
                sector_id INTEGER,
                industry_id INTEGER
            )
            """
        )

        # Create quarterly_results table with publication_date
        cur.execute(
            """
            CREATE TABLE quarterly_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                quarter TEXT NOT NULL,
                revenue REAL,
                net_profit REAL,
                eps REAL,
                roe REAL,
                roce REAL,
                debt_equity REAL,
                operating_margin REAL,
                net_margin REAL,
                publication_date TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, quarter)
            )
            """
        )

        # Seed sample company: TEST_CORP
        cur.execute(
            """
            INSERT INTO companies (id, symbol, company_name, sector, industry, exchange)
            VALUES (1, 'TESTCORP', 'Test Corporation Ltd', 'Technology', 'IT', 'NSE')
            """
        )
        self.conn.commit()

        # Patch DATABASE_PATH in financial_service to point to our isolated DB
        self.db_patcher = patch(
            "backend.data_pipeline.financial_service.DATABASE_PATH",
            self.temp_db_path,
        )
        self.db_patcher.start()

    def tearDown(self):
        """Tear down isolated test database."""
        self.db_patcher.stop()
        self.conn.close()
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def _insert_quarter(
        self,
        quarter,
        revenue=100.0,
        net_profit=15.0,
        publication_date=None,
        company_id=1,
    ):
        """Helper to insert a quarterly record into isolated test database."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (?, ?, ?, ?, 10.0, 0.18, 0.22, 0.1, 0.20, 0.15, ?)
            """,
            (company_id, quarter, revenue, net_profit, publication_date),
        )
        self.conn.commit()

    # =========================================================================
    # Test 1: Exclude a future reporting quarter
    # =========================================================================
    def test_01_exclude_future_reporting_quarter(self):
        """
        Given evaluation date: 2025-01-15 and a record for Q1 2025 (period ending 2025-03-31),
        Q1 2025 must NOT be selected on 2025-01-15 because the quarter has not even ended.
        """
        self._insert_quarter("2025-Q1", revenue=1000.0)

        result = get_latest_financial_data("TESTCORP", evaluation_date="2025-01-15")
        self.assertIsNone(
            result,
            "Future quarter 2025-Q1 was erroneously returned on evaluation date 2025-01-15!",
        )

    # =========================================================================
    # Test 2: Exclude a result published after evaluation
    # =========================================================================
    def test_02_exclude_result_published_after_evaluation(self):
        """
        Given evaluation date: 2025-02-15
        And Q3 2024 result (ended 2024-09-30) published on 2025-02-20
        Expected: The result must NOT be selected as available on 15 February 2025.
        """
        self._insert_quarter("2024-Q3", revenue=800.0, publication_date="2025-02-20")

        result = get_latest_financial_data("TESTCORP", evaluation_date="2025-02-15")
        self.assertIsNone(
            result,
            "Result published on 2025-02-20 leaked into evaluation on 2025-02-15!",
        )

    # =========================================================================
    # Test 3: Include a result published before evaluation
    # =========================================================================
    def test_03_include_result_published_before_evaluation(self):
        """
        Given evaluation date: 2025-02-15
        And Q3 2024 result published on 2025-02-10
        Expected: The result is eligible and selected as latest point-in-time data.
        """
        self._insert_quarter("2024-Q3", revenue=850.0, publication_date="2025-02-10")

        result = get_latest_financial_data("TESTCORP", evaluation_date="2025-02-15")
        self.assertIsNotNone(result)
        self.assertEqual(result["quarter"], "2024-Q3")
        self.assertEqual(result["revenue"], 850.0)
        self.assertEqual(result["publication_date"], "2025-02-10")
        self.assertTrue(result["is_publication_date_verified"])
        self.assertEqual(result["availability_status"], "VERIFIED_POINT_IN_TIME")

    # =========================================================================
    # Test 4: Respect publication-time boundaries (intraday timestamps & EOD)
    # =========================================================================
    def test_04_respect_publication_time_boundaries(self):
        """
        When timestamps are provided:
        Result published at 2025-02-15 09:00:00.
        - Evaluation at 2025-02-15 08:30:00 -> NOT eligible (before publication).
        - Evaluation at 2025-02-15 15:30:00 -> Eligible (after publication).
        - Evaluation with date-only '2025-02-15' -> EOD semantics (23:59:59.999999) -> Eligible.
        """
        self._insert_quarter(
            "2024-Q3",
            revenue=900.0,
            publication_date="2025-02-15 09:00:00",
        )

        # Before earnings release on the same day
        res_before = get_latest_financial_data(
            "TESTCORP", evaluation_date="2025-02-15 08:30:00"
        )
        self.assertIsNone(
            res_before,
            "Earnings released at 09:00 leaked into 08:30 pre-market evaluation!",
        )

        # After earnings release on the same day
        res_after = get_latest_financial_data(
            "TESTCORP", evaluation_date="2025-02-15 15:30:00"
        )
        self.assertIsNotNone(res_after)
        self.assertEqual(res_after["quarter"], "2024-Q3")
        self.assertEqual(res_after["availability_status"], "VERIFIED_POINT_IN_TIME")

        # Date-only evaluation defaults to end-of-day
        res_eod = get_latest_financial_data("TESTCORP", evaluation_date="2025-02-15")
        self.assertIsNotNone(res_eod)
        self.assertEqual(res_eod["quarter"], "2024-Q3")

    # =========================================================================
    # Test 5: Handle missing publication dates honestly
    # =========================================================================
    def test_05_handle_missing_publication_dates_honestly(self):
        """
        When publication_date is NULL/missing:
        1. It must NOT be silently classified as proven available.
        2. It requires period_end + reporting_lag_days (default 45 days) <= evaluation_date.
        3. Returns availability_status='PERIOD_ELIGIBLE_FALLBACK_LAG' and
           is_publication_date_verified=False.
        """
        # 2024-Q4 ends on 2024-12-31.
        # 45 days after 2024-12-31 is 2025-02-14.
        self._insert_quarter("2024-Q4", revenue=950.0, publication_date=None)

        # On 2025-01-20 (only 20 days after quarter end): NOT eligible under 45-day lag
        res_early = get_latest_financial_data("TESTCORP", evaluation_date="2025-01-20")
        self.assertIsNone(
            res_early,
            "Unverified record was prematurely selected before statutory 45-day lag elapsed!",
        )

        # On 2025-02-16 (47 days after quarter end): eligible under conservative fallback
        res_lag = get_latest_financial_data("TESTCORP", evaluation_date="2025-02-16")
        self.assertIsNotNone(res_lag)
        self.assertEqual(res_lag["quarter"], "2024-Q4")
        self.assertIsNone(res_lag["publication_date"])
        self.assertFalse(res_lag["is_publication_date_verified"])
        self.assertEqual(
            res_lag["availability_status"], "PERIOD_ELIGIBLE_FALLBACK_LAG"
        )

    # =========================================================================
    # Test 6: Preserve latest-data behavior
    # =========================================================================
    def test_06_preserve_latest_data_behavior(self):
        """
        When evaluation_date is None:
        Returns the absolute latest record in the database for current live scanning.
        """
        self._insert_quarter("2024-Q3", revenue=800.0)
        self._insert_quarter("2024-Q4", revenue=850.0)
        self._insert_quarter("2025-Q1", revenue=900.0)

        latest = get_latest_financial_data("TESTCORP", evaluation_date=None)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["quarter"], "2025-Q1")
        self.assertEqual(latest["revenue"], 900.0)
        self.assertEqual(latest["availability_status"], "LATEST_CURRENT")

    # =========================================================================
    # Test 7: Verify year and quarter transitions
    # =========================================================================
    def test_07_verify_year_and_quarter_transitions(self):
        """
        Verify transition boundaries:
        - Dec 2024 / Jan 2025 (Q3 vs Q4)
        - Mar / Apr 2025 (Q4 vs Q1)
        - Jun / Jul 2025 (Q1 vs Q2)
        - Sep / Oct 2025 (Q2 vs Q3)
        """
        # Q3 2024 ends 2024-09-30, published 2024-11-10
        self._insert_quarter("2024-Q3", revenue=300.0, publication_date="2024-11-10")
        # Q4 2024 ends 2024-12-31, published 2025-02-10
        self._insert_quarter("2024-Q4", revenue=400.0, publication_date="2025-02-10")
        # Q1 2025 ends 2025-03-31, published 2025-05-12
        self._insert_quarter("2025-Q1", revenue=500.0, publication_date="2025-05-12")
        # Q2 2025 ends 2025-06-30, published 2025-08-11
        self._insert_quarter("2025-Q2", revenue=600.0, publication_date="2025-08-11")

        # 1. On 2024-12-31 and 2025-01-15: Q4 is not yet published (only Q3 is available)
        res_dec = get_latest_financial_data("TESTCORP", evaluation_date="2024-12-31")
        self.assertEqual(res_dec["quarter"], "2024-Q3")
        res_jan = get_latest_financial_data("TESTCORP", evaluation_date="2025-01-15")
        self.assertEqual(res_jan["quarter"], "2024-Q3")

        # 2. On 2025-03-31 and 2025-04-15: Q4 is published, Q1 is not yet published
        res_mar = get_latest_financial_data("TESTCORP", evaluation_date="2025-03-31")
        self.assertEqual(res_mar["quarter"], "2024-Q4")
        res_apr = get_latest_financial_data("TESTCORP", evaluation_date="2025-04-15")
        self.assertEqual(res_apr["quarter"], "2024-Q4")

        # 3. On 2025-06-30 and 2025-07-15: Q1 is published, Q2 is not yet published
        res_jun = get_latest_financial_data("TESTCORP", evaluation_date="2025-06-30")
        self.assertEqual(res_jun["quarter"], "2025-Q1")
        res_jul = get_latest_financial_data("TESTCORP", evaluation_date="2025-07-15")
        self.assertEqual(res_jul["quarter"], "2025-Q1")

        # 4. On 2025-09-30 and 2025-10-15: Q2 is published
        res_sep = get_latest_financial_data("TESTCORP", evaluation_date="2025-09-30")
        self.assertEqual(res_sep["quarter"], "2025-Q2")
        res_oct = get_latest_financial_data("TESTCORP", evaluation_date="2025-10-15")
        self.assertEqual(res_oct["quarter"], "2025-Q2")

    # =========================================================================
    # Test 8: Verify evaluation-date propagation in downstream services
    # =========================================================================
    def test_08_verify_evaluation_date_propagation(self):
        """
        Verify that stock_snapshot_service propagates evaluation_date down to
        get_latest_financial_data and receives point-in-time results.
        """
        self._insert_quarter("2024-Q3", revenue=111.0, publication_date="2024-11-10")
        self._insert_quarter("2024-Q4", revenue=222.0, publication_date="2025-02-10")

        # Evaluate on 2025-01-05 via snapshot service
        snapshot = get_stock_snapshot("TESTCORP", evaluation_date="2025-01-05")
        self.assertIsNotNone(snapshot["financial"])
        self.assertEqual(snapshot["financial"]["quarter"], "2024-Q3")
        self.assertEqual(snapshot["financial"]["revenue"], 111.0)

        # Evaluate on 2025-02-15 via snapshot service
        snapshot_later = get_stock_snapshot("TESTCORP", evaluation_date="2025-02-15")
        self.assertIsNotNone(snapshot_later["financial"])
        self.assertEqual(snapshot_later["financial"]["quarter"], "2024-Q4")
        self.assertEqual(snapshot_later["financial"]["revenue"], 222.0)

    # =========================================================================
    # Test 9: Verify later data cannot alter earlier evaluations (Point-in-time stability)
    # =========================================================================
    def test_09_later_data_cannot_alter_earlier_evaluations(self):
        """
        Key point-in-time test:
        1. Evaluate historical date T (2025-01-15).
        2. Observe result.
        3. Insert new financial result published at T+15 (2025-01-30).
        4. Re-evaluate historical date T.
        5. The returned financial data for T MUST NOT CHANGE.
        """
        # Initial database state at T:
        self._insert_quarter("2024-Q2", revenue=500.0, publication_date="2024-08-10")
        eval_t = "2025-01-15"

        result_before = get_latest_financial_data("TESTCORP", evaluation_date=eval_t)
        self.assertEqual(result_before["quarter"], "2024-Q2")
        self.assertEqual(result_before["revenue"], 500.0)

        # Now, simulate new quarterly results arriving and being committed later
        self._insert_quarter("2024-Q3", revenue=750.0, publication_date="2025-01-25")
        self._insert_quarter("2024-Q4", revenue=900.0, publication_date="2025-04-10")

        # Re-evaluate historical date T
        result_after = get_latest_financial_data("TESTCORP", evaluation_date=eval_t)
        self.assertEqual(
            result_after["quarter"],
            result_before["quarter"],
            "Point-in-time violation! Later-published results altered earlier historical evaluation!",
        )
        self.assertEqual(result_after["revenue"], result_before["revenue"])


if __name__ == "__main__":
    unittest.main()
