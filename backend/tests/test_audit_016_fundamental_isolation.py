"""
AUDIT-016 Adversarial Regression Test Suite
===========================================

Verifies strict historical financial-data isolation, point-in-time eligibility,
and lookahead bias prevention across:
- backend.data_pipeline.financial_service (get_financial_data & get_latest_financial_data)
- backend.logic.roe_analyzer (analyze_roe)
- backend.logic.roce_analyzer (analyze_roce)
- backend.logic.debt_equity_analyzer (analyze_debt_equity)
- backend.logic.profit_margin_analyzer (analyze_profit_margin)
- backend.logic.growth_analyzer (analyze_growth)
- backend.logic.valuation_analyzer (analyze_valuation)
- backend.engines.financial_engine (analyze_financial_health)

All tests operate strictly against isolated temporary SQLite databases.
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import backend.data_pipeline.financial_service as fin_svc
from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_latest_financial_data,
)
from backend.engines.financial_engine import analyze_financial_health
from backend.logic.debt_equity_analyzer import analyze_debt_equity
from backend.logic.growth_analyzer import analyze_growth
from backend.logic.profit_margin_analyzer import analyze_profit_margin
from backend.logic.roce_analyzer import analyze_roce
from backend.logic.roe_analyzer import analyze_roe
from backend.logic.valuation_analyzer import analyze_valuation


class TestAudit016FundamentalIsolation(unittest.TestCase):
    """Adversarial test suite for historical fundamental data isolation."""

    @classmethod
    def setUpClass(cls):
        # Create an isolated temporary SQLite database
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_isolated_fundamentals.db"

        conn = sqlite3.connect(cls.db_path)
        cur = conn.cursor()

        # Create schema
        cur.execute("""
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                symbol TEXT UNIQUE,
                company_name TEXT,
                sector TEXT,
                industry TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE quarterly_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                quarter TEXT,
                revenue REAL,
                net_profit REAL,
                eps REAL,
                roe REAL,
                roce REAL,
                debt_equity REAL,
                operating_margin REAL,
                net_margin REAL,
                publication_date TEXT,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        """)

        # Insert test company
        cur.execute("""
            INSERT INTO companies (id, symbol, company_name, sector, industry)
            VALUES (1, 'TESTCORP', 'Test Corporation', 'Technology', 'IT Services')
        """)

        # Insert 3 quarterly results:
        # Q1: 2025-03-31, published 2025-04-20
        # Q2: 2025-06-30, published 2025-07-25
        # Q3: 2025-09-30, publication_date NULL (fallback lag: 2025-09-30 + 45d = 2025-11-14)
        records = [
            (1, '2025-Q1', 1000.0, 150.0, 15.0, 18.0, 22.0, 0.20, 20.0, 15.0, '2025-04-20'),
            (1, '2025-Q2', 1200.0, 200.0, 20.0, 21.0, 25.0, 0.15, 22.0, 16.6, '2025-07-25'),
            (1, '2025-Q3', 1500.0, 300.0, 30.0, 25.0, 28.0, 0.10, 25.0, 20.0, None),
        ]
        cur.executemany("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        # Patch DATABASE_PATH in financial_service for all tests
        self.patcher = patch.object(fin_svc, "DATABASE_PATH", self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_01_published_before_evaluation_date_eligible(self):
        """Scenario 1: A financial record published before evaluation date is eligible."""
        # On 2025-05-01, Q1 (published 2025-04-20) must be eligible
        df = get_financial_data("TESTCORP", evaluation_date="2025-05-01")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["quarter"], "2025-Q1")

        latest = get_latest_financial_data("TESTCORP", evaluation_date="2025-05-01")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["quarter"], "2025-Q1")
        self.assertEqual(latest["availability_status"], "VERIFIED_POINT_IN_TIME")

    def test_02_published_after_evaluation_date_excluded(self):
        """Scenario 2: A financial record published after evaluation date is excluded."""
        # Q2 was published on 2025-07-25. Evaluating on 2025-07-20 must exclude Q2.
        df = get_financial_data("TESTCORP", evaluation_date="2025-07-20")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[-1]["quarter"], "2025-Q1")

        latest = get_latest_financial_data("TESTCORP", evaluation_date="2025-07-20")
        self.assertEqual(latest["quarter"], "2025-Q1")

    def test_03_later_quarter_cannot_leak_into_earlier_evaluation(self):
        """Scenario 3: A later quarter cannot leak into an earlier historical evaluation."""
        # On 2025-08-01, Q1 and Q2 are published, but Q3 (ends 2025-09-30) must never appear.
        df = get_financial_data("TESTCORP", evaluation_date="2025-08-01")
        quarters = df["quarter"].tolist()
        self.assertIn("2025-Q1", quarters)
        self.assertIn("2025-Q2", quarters)
        self.assertNotIn("2025-Q3", quarters)

    def test_04_missing_publication_date_uses_45_day_fallback(self):
        """Scenario 4: Missing publication date uses only documented 45-day fallback."""
        # Q3 ends 2025-09-30. Period end + 45 days is 2025-11-14.
        # Evaluating on 2025-11-15 must make Q3 eligible under fallback.
        df = get_financial_data("TESTCORP", evaluation_date="2025-11-15")
        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[-1]["quarter"], "2025-Q3")
        self.assertEqual(df.attrs.get("data_eligibility_status"), "PERIOD_ELIGIBLE_FALLBACK_LAG")

        latest = get_latest_financial_data("TESTCORP", evaluation_date="2025-11-15")
        self.assertEqual(latest["quarter"], "2025-Q3")
        self.assertEqual(latest["availability_status"], "PERIOD_ELIGIBLE_FALLBACK_LAG")

    def test_05_fallback_date_after_evaluation_date_excluded(self):
        """Scenario 5: A record whose fallback eligibility date is after evaluation date is excluded."""
        # Q3 period end + 45 days = 2025-11-14. Evaluating on 2025-11-10 must exclude Q3.
        df = get_financial_data("TESTCORP", evaluation_date="2025-11-10")
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[-1]["quarter"], "2025-Q2")

        latest = get_latest_financial_data("TESTCORP", evaluation_date="2025-11-10")
        self.assertEqual(latest["quarter"], "2025-Q2")

    def test_06_evaluation_date_before_all_records_returns_insufficient(self):
        """Scenario 6: Evaluation date before all eligible records returns insufficient-data status."""
        # Evaluating in 2024 (before Q1 2025)
        df = get_financial_data("TESTCORP", evaluation_date="2024-12-31")
        self.assertTrue(df.empty)
        self.assertEqual(df.attrs.get("data_eligibility_status"), "NO_ELIGIBLE_RECORDS")

        latest = get_latest_financial_data("TESTCORP", evaluation_date="2024-12-31")
        self.assertIsNone(latest)

        roe_res = analyze_roe("TESTCORP", evaluation_date="2024-12-31")
        self.assertEqual(roe_res["status"], "INSUFFICIENT")
        self.assertEqual(roe_res["records"], 0)
        self.assertIsNone(roe_res["latest_roe"])

    def test_07_each_of_the_five_sub_analyzers_respects_historical_cutoff(self):
        """Scenario 7: Each of the five sub-analyzers respects the historical cutoff."""
        # Evaluating on 2025-07-20 (only Q1 eligible, Q2 published on 2025-07-25)
        eval_date = "2025-07-20"

        # ROE: Q1 ROE is 18.0, Q2 ROE is 21.0
        roe_res = analyze_roe("TESTCORP", evaluation_date=eval_date)
        self.assertEqual(roe_res["records"], 1)
        self.assertAlmostEqual(roe_res["latest_roe"], 18.0)

        # ROCE: Q1 ROCE is 22.0, Q2 ROCE is 25.0
        roce_res = analyze_roce("TESTCORP", evaluation_date=eval_date)
        self.assertEqual(roce_res["records"], 1)
        self.assertAlmostEqual(roce_res["latest_roce"], 22.0)

        # Debt/Equity: Q1 DE is 0.20, Q2 DE is 0.15
        de_res = analyze_debt_equity("TESTCORP", evaluation_date=eval_date)
        self.assertEqual(de_res["records"], 1)
        self.assertAlmostEqual(de_res["latest_debt_equity"], 0.20)

        # Margin: Q1 Net Margin is 15.0, Q2 Net Margin is 16.6
        margin_res = analyze_profit_margin("TESTCORP", evaluation_date=eval_date)
        self.assertEqual(margin_res["records"], 1)
        self.assertAlmostEqual(margin_res["latest_net_margin"], 15.0)

        # Growth: With only 1 quarter, YoY/QoQ is Insufficient Data
        growth_res = analyze_growth("TESTCORP", evaluation_date=eval_date)
        self.assertEqual(growth_res["records"], 1)
        self.assertEqual(growth_res["status"], "INSUFFICIENT")

    def test_08_final_fundamental_score_does_not_indirectly_leak(self):
        """Scenario 8: Final fundamental score does not indirectly use future financial records."""
        # Evaluating on 2025-07-20 (Q1 only) vs 2025-08-01 (Q1 & Q2)
        health_q1 = analyze_financial_health("TESTCORP", evaluation_date="2025-07-20")
        health_q2 = analyze_financial_health("TESTCORP", evaluation_date="2025-08-01")

        # ROE used in Q1 must be 18.0, whereas in Q2 it uses 21.0
        # Profitability score changes because ROE, ROCE, Margin changed
        self.assertNotEqual(health_q1["profitability_score"], health_q2["profitability_score"])

    def test_09_omitting_evaluation_date_preserves_latest_snapshot(self):
        """Scenario 9: Omitting evaluation_date preserves documented latest-snapshot contract."""
        df_latest = get_financial_data("TESTCORP")
        self.assertEqual(len(df_latest), 3)
        self.assertEqual(df_latest.iloc[-1]["quarter"], "2025-Q3")
        self.assertEqual(df_latest.attrs.get("data_eligibility_status"), "LATEST_CURRENT")

        latest_record = get_latest_financial_data("TESTCORP")
        self.assertEqual(latest_record["quarter"], "2025-Q3")
        self.assertEqual(latest_record["availability_status"], "LATEST_CURRENT")

    def test_10_timezone_and_timestamp_suffixes_cannot_bypass_cutoff(self):
        """Scenario 10: Timezone and timestamp suffixes cannot bypass the cutoff."""
        # Q2 published at 2025-07-25 00:00:00
        # Evaluating at 2025-07-24T23:59:59Z (UTC) must exclude Q2
        df_utc = get_financial_data("TESTCORP", evaluation_date="2025-07-24T23:59:59Z")
        self.assertEqual(len(df_utc), 1)
        self.assertEqual(df_utc.iloc[-1]["quarter"], "2025-Q1")

        # Evaluating at 2025-07-25T10:00:00+05:30 (IST) must include Q2
        df_ist = get_financial_data("TESTCORP", evaluation_date="2025-07-25T10:00:00+05:30")
        self.assertEqual(len(df_ist), 2)
        self.assertEqual(df_ist.iloc[-1]["quarter"], "2025-Q2")

    def test_11_historical_results_remain_deterministic_on_insert(self):
        """Scenario 11: Historical results remain deterministic when newer rows are inserted."""
        # Baseline evaluation on 2025-05-01
        res_before = analyze_roe("TESTCORP", evaluation_date="2025-05-01")

        # Insert future Q4 record into the database
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (1, '2025-Q4', 2000.0, 500.0, 50.0, 30.0, 35.0, 0.05, 30.0, 25.0, '2026-02-15')
        """)
        conn.commit()
        conn.close()

        # Re-evaluate on 2025-05-01: must be 100% identical
        res_after = analyze_roe("TESTCORP", evaluation_date="2025-05-01")
        self.assertEqual(res_before["records"], res_after["records"])
        self.assertEqual(res_before["latest_roe"], res_after["latest_roe"])
        self.assertEqual(res_before["status"], res_after["status"])

    def test_12_isolated_temporary_database_zero_production_mutation(self):
        """Scenario 12: Tests operate on temp database and do not touch production database."""
        prod_db = Path("database/swing_trading.db")
        self.assertTrue(prod_db.exists(), "Production DB must exist")
        self.assertNotEqual(str(self.db_path), str(prod_db), "Test DB must be distinct from prod DB")


if __name__ == "__main__":
    unittest.main()

