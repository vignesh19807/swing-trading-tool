"""
AUDIT-017: Independent Verification of Historical Fundamental Isolation
Tests the 7 mandatory properties using isolated synthetic SQLite databases.
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
from backend.engines.financial_engine import analyze_financial_health

class TestAudit017IndependentIsolation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_audit_017_isolation.db"
        
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
        
        # Historical baseline: 4 standard quarters in 2024
        # 2024-Q1 (end: 2024-03-31, pub: 2024-05-10)
        # 2024-Q2 (end: 2024-06-30, pub: 2024-08-10)
        # 2024-Q3 (end: 2024-09-30, pub: 2024-11-10)
        # 2024-Q4 (end: 2024-12-31, pub: NULL -> lag 45 days: 2025-02-14)
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

    def test_property_1_and_6_future_records_cannot_affect_earlier_scores_and_deterministic(self):
        """Property 1 & 6: Adding future conflicting/poisoned records does not alter earlier scores."""
        eval_date = "2024-12-01"
        # At 2024-12-01, Q1, Q2, Q3 are published. Q4 (ending 2024-12-31) has not ended.
        df_before = get_financial_data("TESTCORP", evaluation_date=eval_date)
        roe_before = analyze_roe("TESTCORP", evaluation_date=eval_date)
        roce_before = analyze_roce("TESTCORP", evaluation_date=eval_date)
        margin_before = analyze_profit_margin("TESTCORP", evaluation_date=eval_date)
        de_before = analyze_debt_equity("TESTCORP", evaluation_date=eval_date)
        health_before = analyze_financial_health("TESTCORP", evaluation_date=eval_date)

        # Inject extreme poisoned future records for 2025 into DB
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES 
            (1, '2025-Q1', 50000.0, -10000.0, -100.0, -50.0, -30.0, 9.9, -20.0, -20.0, '2025-05-10'),
            (1, '2025-Q2', 90000.0, 40000.0, 400.0, 80.0, 90.0, 0.01, 50.0, 44.4, '2025-08-10')
        """)
        conn.commit()
        conn.close()

        df_after = get_financial_data("TESTCORP", evaluation_date=eval_date)
        roe_after = analyze_roe("TESTCORP", evaluation_date=eval_date)
        roce_after = analyze_roce("TESTCORP", evaluation_date=eval_date)
        margin_after = analyze_profit_margin("TESTCORP", evaluation_date=eval_date)
        de_after = analyze_debt_equity("TESTCORP", evaluation_date=eval_date)
        health_after = analyze_financial_health("TESTCORP", evaluation_date=eval_date)

        self.assertEqual(len(df_before), len(df_after))
        self.assertEqual(roe_before["latest_roe"], roe_after["latest_roe"])
        self.assertEqual(roce_before["latest_roce"], roce_after["latest_roce"])
        self.assertEqual(margin_before["latest_net_margin"], margin_after["latest_net_margin"])
        self.assertEqual(de_before["latest_debt_equity"], de_after["latest_debt_equity"])
        self.assertEqual(health_before["overall_score"], health_after["overall_score"])
        self.assertEqual(health_before["status"], health_after["status"])

    def test_property_2_future_records_cannot_affect_recommendation_via_growth_or_valuation(self):
        """Property 2: Future records cannot alter growth or valuation for an earlier date."""
        eval_date = "2025-01-15"
        # At 2025-01-15, Q4 has ended (2024-12-31) but publication_date is NULL.
        # Fallback lag is 45 days -> eligible 2025-02-14.
        # So only 3 quarters (Q1, Q2, Q3) are eligible at 2025-01-15.
        df_early = get_financial_data("TESTCORP", evaluation_date=eval_date)
        growth_early = analyze_growth("TESTCORP", evaluation_date=eval_date)
        val_early = analyze_valuation("TESTCORP", evaluation_date=eval_date)
        
        # Growth and valuation require 4 quarters for full TTM
        self.assertEqual(growth_early["status"], "INSUFFICIENT")
        self.assertIsNone(growth_early["revenue_yoy_growth"])
        self.assertEqual(val_early["status"], "INSUFFICIENT")

        # Now advance evaluation_date to 2025-02-15 (after 45-day lag for Q4)
        eval_later = "2025-02-15"
        df_later = get_financial_data("TESTCORP", evaluation_date=eval_later)
        self.assertEqual(len(df_later), 4)
        growth_later = analyze_growth("TESTCORP", evaluation_date=eval_later)
        val_later = analyze_valuation("TESTCORP", evaluation_date=eval_later)
        self.assertIsNotNone(growth_later["revenue_qoq_growth"])
        self.assertEqual(val_later["ttm_eps"], 69.0)

    def test_property_3_publication_timestamps_vs_fallback_dates(self):
        """Property 3: Verified publication timestamps override the 45-day fallback rule."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        # Set explicit early publication date for Q4: 2025-01-10
        cur.execute("UPDATE quarterly_results SET publication_date = '2025-01-10' WHERE quarter = '2024-Q4'")
        conn.commit()
        conn.close()

        eval_date = "2025-01-12"
        df = get_financial_data("TESTCORP", evaluation_date=eval_date)
        # Because explicit publication date was 2025-01-10 <= 2025-01-12, Q4 IS eligible!
        self.assertEqual(len(df), 4)
        quarters = df["quarter"].tolist()
        self.assertIn("2024-Q4", quarters)

    def test_property_4_insufficient_eligibility_not_silently_treated_as_valid(self):
        """Property 4: Incomplete / future data returns INSUFFICIENT, not fake score."""
        eval_date = "2024-06-01" # Only Q1 2024 is available
        df = get_financial_data("TESTCORP", evaluation_date=eval_date)
        growth_res = analyze_growth("TESTCORP", evaluation_date=eval_date)
        self.assertEqual(growth_res["status"], "INSUFFICIENT")
        self.assertIsNone(growth_res["revenue_yoy_growth"])

    def test_property_5_latest_snapshot_compatible_when_evaluation_date_omitted(self):
        """Property 5: When evaluation_date is None, all records are returned (legacy mode)."""
        df = get_financial_data("TESTCORP", evaluation_date=None)
        self.assertEqual(len(df), 4)
        roe_res = analyze_roe("TESTCORP", evaluation_date=None)
        self.assertEqual(roe_res["data_eligibility_status"], "LATEST_CURRENT")
        self.assertEqual(roe_res["status"], "VALID")

    def test_property_7_timezone_and_timestamp_normalization(self):
        """Property 7: Timezone variations normalize properly and cannot bypass filters."""
        # Test string with UTC timezone, ISO format, and date-only
        ts1 = _normalize_eval_timestamp("2025-01-15T00:00:00Z")
        ts2 = _normalize_eval_timestamp("2025-01-15 14:30:00+05:30")
        ts3 = _normalize_eval_timestamp("2025-01-15")
        
        # Verify UTC normalization
        self.assertEqual(ts1.strftime("%Y-%m-%d"), "2025-01-15")
        self.assertEqual(ts2.strftime("%Y-%m-%d"), "2025-01-15")
        self.assertEqual(ts3.strftime("%Y-%m-%d"), "2025-01-15")
        
        pub_norm = _normalize_pub_timestamp("2025-01-15T18:00:00Z")
        self.assertEqual(pub_norm.strftime("%Y-%m-%d"), "2025-01-15")

if __name__ == "__main__":
    unittest.main()
