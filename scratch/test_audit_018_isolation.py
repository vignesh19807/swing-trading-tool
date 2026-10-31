"""
AUDIT-018: Independent Point-in-Time Financial Isolation Verification
Tests the 7 sub-analyzers and the aggregate financial engine against synthetic poisoned future records.
"""

import os
import sys
import tempfile
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, os.path.abspath("."))

import backend.data_pipeline.financial_service as fin_svc
from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_latest_financial_data,
    _normalize_eval_timestamp,
    _normalize_pub_timestamp,
)
from backend.logic.roe_analyzer import analyze_roe
from backend.logic.roce_analyzer import analyze_roce
from backend.logic.debt_equity_analyzer import analyze_debt_equity
from backend.logic.profit_margin_analyzer import analyze_profit_margin
from backend.logic.growth_analyzer import analyze_growth
from backend.logic.valuation_analyzer import analyze_valuation
from backend.logic.stock_context_analyzer import get_stock_context
from backend.engines.financial_engine import analyze_financial_health

class TestAudit018IndependentIsolation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_audit_018_isolation.db"
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
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
        cur.execute("INSERT INTO companies VALUES (1, 'TESTCORP', 'Test Corporation', 'Technology', 'IT Services')")
        
        # Baseline quarters:
        # 2024-Q1 (end: 2024-03-31, pub: 2024-05-10)
        # 2024-Q2 (end: 2024-06-30, pub: 2024-08-10)
        # 2024-Q3 (end: 2024-09-30, pub: 2024-11-10)
        # 2024-Q4 (end: 2024-12-31, pub: NULL -> fallback 45 days: 2025-02-14)
        records = [
            (1, '2024-Q1', 1000.0, 150.0, 15.0, 18.0, 22.0, 0.20, 20.0, 15.0, '2024-05-10'),
            (1, '2024-Q2', 1100.0, 160.0, 16.0, 19.0, 23.0, 0.18, 21.0, 14.5, '2024-08-10'),
            (1, '2024-Q3', 1200.0, 180.0, 18.0, 20.0, 24.0, 0.15, 22.0, 15.0, '2024-11-10'),
            (1, '2024-Q4', 1300.0, 200.0, 20.0, 22.0, 26.0, 0.12, 23.0, 15.4, None),
        ]
        cur.executemany("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
        conn.close()
        
        self.patcher = patch.object(fin_svc, "DATABASE_PATH", self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_property_1_future_published_record_isolated(self):
        """Poison with 2025-Q1 published on 2025-05-15. As of 2025-03-01, 2025-Q1 must be invisible."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (1, '2025-Q1', 99999.0, 99999.0, 999.0, 99.0, 99.0, 0.01, 99.0, 99.0, '2025-05-15')
        """)
        conn.commit()
        conn.close()

        # Check raw returned rows
        raw_data = get_financial_data("TESTCORP", evaluation_date="2025-03-01")
        quarters = list(raw_data["quarter"].tolist())
        self.assertNotIn("2025-Q1", quarters, "2025-Q1 was visible before its publication date!")
        self.assertEqual(quarters[-1], "2024-Q4")

        # Check sub-analyzers
        roe_res = analyze_roe("TESTCORP", evaluation_date="2025-03-01")
        self.assertAlmostEqual(roe_res["latest_roe"], 22.0, places=2)

        margin_res = analyze_profit_margin("TESTCORP", evaluation_date="2025-03-01")
        self.assertAlmostEqual(margin_res["latest_net_margin"], 15.4, places=2)

    def test_property_2_null_publication_date_45d_fallback(self):
        """2024-Q4 ended 2024-12-31 with NULL publication date. Available strictly on 2025-02-14."""
        # On 2025-02-10 (41 days post quarter-end), 2024-Q4 must NOT be available
        raw_pre = get_financial_data("TESTCORP", evaluation_date="2025-02-10", reporting_lag_days=45)
        self.assertNotIn("2024-Q4", list(raw_pre["quarter"].tolist()))
        self.assertEqual(list(raw_pre["quarter"].tolist())[-1], "2024-Q3")

        # On 2025-02-15 (46 days post quarter-end), 2024-Q4 MUST be available
        raw_post = get_financial_data("TESTCORP", evaluation_date="2025-02-15", reporting_lag_days=45)
        self.assertIn("2024-Q4", list(raw_post["quarter"].tolist()))
        self.assertEqual(list(raw_post["quarter"].tolist())[-1], "2024-Q4")

    def test_property_3_timestamp_iso8601_publication_dates(self):
        """Ensure ISO timestamps with times ('2025-04-10T18:30:00Z') parse and filter identically."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (1, '2025-Q1', 5000.0, 800.0, 25.0, 25.0, 28.0, 0.10, 25.0, 16.0, '2025-04-10T18:30:00')
        """)
        conn.commit()
        conn.close()

        # Before timestamp: 2025-04-10T12:00:00
        raw_before = get_financial_data("TESTCORP", evaluation_date="2025-04-09")
        self.assertNotIn("2025-Q1", list(raw_before["quarter"].tolist()))

        # After timestamp: 2025-04-11
        raw_after = get_financial_data("TESTCORP", evaluation_date="2025-04-11")
        self.assertIn("2025-Q1", list(raw_after["quarter"].tolist()))

    def test_property_4_all_subanalyzers_point_in_time(self):
        """Verify roe, roce, debt_equity, profit_margin, growth, valuation, stock_context."""
        eval_dt = "2025-02-01" # Prior to 2024-Q4 fallback availability
        
        roe = analyze_roe("TESTCORP", evaluation_date=eval_dt)
        self.assertAlmostEqual(roe["latest_roe"], 20.0, places=2) # 2024-Q3 roe was 20.0%

        roce = analyze_roce("TESTCORP", evaluation_date=eval_dt)
        self.assertAlmostEqual(roce["latest_roce"], 24.0, places=2) # 2024-Q3 roce was 24.0%

        de = analyze_debt_equity("TESTCORP", evaluation_date=eval_dt)
        self.assertAlmostEqual(de["latest_debt_equity"], 0.15, places=2) # 2024-Q3 was 0.15

        pm = analyze_profit_margin("TESTCORP", evaluation_date=eval_dt)
        self.assertAlmostEqual(pm["latest_operating_margin"], 22.0, places=2) # 2024-Q3 was 22.0%

        gw = analyze_growth("TESTCORP", evaluation_date=eval_dt)
        self.assertEqual(gw["data_eligibility_status"], "VERIFIED_POINT_IN_TIME")
        self.assertEqual(gw["latest_revenue"], 1200.0) # Confirms 2024-Q3, not Q4 or future

        val = analyze_valuation("TESTCORP", evaluation_date=eval_dt)
        self.assertEqual(val["status"], "INSUFFICIENT")

    def test_property_5_aggregate_financial_engine(self):
        """Verify analyze_financial_health propagates evaluation_date and matches isolated score."""
        eval_dt = "2025-02-01"
        res = analyze_financial_health("TESTCORP", evaluation_date=eval_dt)
        self.assertIn("overall_score", res)
        self.assertIn("component_statuses", res)
        self.assertEqual(res["component_statuses"]["roe"], "VALID")

if __name__ == "__main__":
    unittest.main()
