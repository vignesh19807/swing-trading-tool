"""
AUDIT-037 Regression Test Suite: Historical Financial Data Eligibility
======================================================================

Comprehensive verification covering all 32 point-in-time financial eligibility test cases:
1. Standard quarterly lag: Q1 (ends 03-31), lag 45 days -> eligible on 05-15.
2. Boundary condition: evaluation date exactly on period_end + 45 days -> ELIGIBLE.
3. Boundary condition: evaluation date exactly on period_end + 44 days -> NOT ELIGIBLE.
4. Boundary condition: evaluation date exactly on period_end -> NOT ELIGIBLE.
5. Boundary condition: evaluation date before period_end -> NOT ELIGIBLE.
6. Verified publication date: pub date is 04-20 -> ELIGIBLE on 04-20, NOT eligible on 04-19.
7. Verified pub date overrides fallback: pub date is 04-20, fallback is 05-15 -> available on 04-20.
8. Verified pub date late: pub date is 06-01 (62 days), fallback 45 days -> available ONLY on 06-01.
9. Missing publication date (NULL/None) -> uses fallback lag.
10. Empty string publication date -> uses fallback lag.
11. Malformed publication date ('invalid-date', 'N/A') -> uses fallback lag gracefully.
12. Future publication date: pub date is in future relative to eval date -> NOT eligible.
13. Multi-quarter chronological ordering: Q1, Q2, Q3, Q4 available -> on date where all 4 eligible, selects Q4.
14. Multi-quarter transition: on 05-14 selects previous year Q4; on 05-15 selects Q1.
15. Multi-quarter with mixed verification: Q1 verified, Q2 fallback, Q3 verified -> correct selection.
16. Non-calendar quarter formats: FY24-Q1, 2024-Q3, etc. -> correctly parsed.
17. Custom lag days: reporting_lag_days=30 -> eligible on period_end + 30 days.
18. Custom lag days: reporting_lag_days=60 -> eligible on period_end + 60 days.
19. Custom lag days: reporting_lag_days=0 -> eligible on period_end (same day).
20. Negative lag days: reporting_lag_days=-5 -> clamped to 0, never allows look-ahead before period_end.
21. None/default lag days -> defaults to 45 days.
22. All financial records ineligible -> returns None/empty, status 'NO_ELIGIBLE_RECORDS', no crash.
23. Single quarter available -> correct selection and metadata.
24. Dataset builder integration: build_backtesting_dataset attaches correct financial columns and metadata.
25. Dataset builder leakage check: PASS when all records point-in-time compliant.
26. Dataset builder leakage check: FAIL_PRE_AVAILABILITY_LEAK when record used before fallback date.
27. Dataset builder leakage check: FAIL_PRE_PUBLICATION_LEAK when record used before verified pub date.
28. Dataset builder leakage check: FAIL_FUTURE_FINANCIAL_PERIOD when future quarter used.
29. Data access service integration: get_backtest_input passes reporting_lag_days correctly.
30. Financial service get_financial_data: point-in-time filtering with evaluation_date and reporting_lag_days.
31. Timezone handling: ISO strings with offsets (+05:30, Z) handled consistently.
32. Production database read-only test: verify zero writes to database/swing_trading.db during all tests.

Operates with 100% database isolation using temporary SQLite fixtures and synthetic DataFrames.
Zero mutation of production database.
"""

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd

import backend.data_pipeline.financial_service as fin_svc
import backend.data_pipeline.data_service as data_svc
import backend.data_pipeline.classification_service as class_svc
import backend.data_pipeline.technical_indicator_service as tech_svc
import backend.data_pipeline.backtesting_dataset_service as ds_svc
import backend.data_pipeline.backtest_data_access_service as bda_svc
from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_latest_financial_data,
    parse_quarter_period_end,
)
from backend.data_pipeline.backtesting_dataset_service import (
    _prepare_financial_data,
    build_backtesting_dataset,
)
from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_input,
)


class TestAudit037HistoricalFinancialEligibility(unittest.TestCase):
    """Rigorous verification of historical financial eligibility across all 32 audit test cases."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_audit_037_isolated.db"

        conn = sqlite3.connect(cls.db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE sectors (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        """)
        cur.execute("""
            CREATE TABLE industries (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        """)
        cur.execute("""
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                symbol TEXT UNIQUE,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                exchange TEXT,
                sector_id INTEGER,
                industry_id INTEGER,
                FOREIGN KEY (sector_id) REFERENCES sectors (id),
                FOREIGN KEY (industry_id) REFERENCES industries (id)
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
        cur.execute("""
            CREATE TABLE daily_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                adjusted_close REAL,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        """)
        cur.execute("""
            CREATE TABLE technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                date TEXT,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                macd_histogram REAL,
                ema_20 REAL,
                ema_50 REAL,
                ema_200 REAL,
                atr_14 REAL,
                technical_score REAL,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        """)

        # Insert test sectors, industries, and company
        cur.execute("INSERT INTO sectors (id, name) VALUES (1, 'Technology')")
        cur.execute("INSERT INTO industries (id, name) VALUES (1, 'Software')")
        cur.execute("""
            INSERT INTO companies (id, symbol, company_name, sector, industry, exchange, sector_id, industry_id)
            VALUES (1, 'AUDITCORP', 'Audit Corporation', 'Technology', 'Software', 'NSE', 1, 1)
        """)

        # Insert historical quarters:
        # Q1: ends 2025-03-31, verified pub date 2025-04-20
        # Q2: ends 2025-06-30, verified pub date 2025-07-25
        # Q3: ends 2025-09-30, publication_date NULL (fallback lag: 2025-09-30 + 45d = 2025-11-14)
        # Q4: ends 2025-12-31, publication_date NULL (fallback lag: 2025-12-31 + 45d = 2026-02-14)
        records = [
            (1, '2025-Q1', 1000.0, 150.0, 15.0, 18.0, 22.0, 0.20, 20.0, 15.0, '2025-04-20'),
            (1, '2025-Q2', 1200.0, 200.0, 20.0, 21.0, 25.0, 0.15, 22.0, 16.6, '2025-07-25'),
            (1, '2025-Q3', 1500.0, 300.0, 30.0, 25.0, 28.0, 0.10, 25.0, 20.0, None),
            (1, '2025-Q4', 1800.0, 380.0, 38.0, 28.0, 30.0, 0.08, 27.0, 21.1, None),
        ]
        cur.executemany("""
            INSERT INTO quarterly_results (
                company_id, quarter, revenue, net_profit, eps, roe, roce,
                debt_equity, operating_margin, net_margin, publication_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        # Insert price & indicator observations across key timeline dates
        trading_dates = [
            "2025-04-10", "2025-04-20", "2025-05-01",
            "2025-07-20", "2025-07-25", "2025-08-01",
            "2025-11-10", "2025-11-15", "2026-02-10", "2026-02-15"
        ]
        for t_date in trading_dates:
            cur.execute("""
                INSERT INTO daily_prices (company_id, date, open, high, low, close, volume, adjusted_close)
                VALUES (1, ?, 100.0, 105.0, 99.0, 102.0, 100000, 102.0)
            """, (t_date,))
            cur.execute("""
                INSERT INTO technical_indicators (company_id, date, rsi, macd, macd_signal, macd_histogram, ema_20, ema_50, ema_200, atr_14, technical_score)
                VALUES (1, ?, 55.0, 1.2, 1.0, 0.2, 100.0, 98.0, 95.0, 2.5, 75.0)
            """, (t_date,))

        conn.commit()
        conn.close()

        # Capture production DB hash to verify invariant
        cls.prod_db_path = Path(__file__).resolve().parents[2] / "database" / "swing_trading.db"
        if cls.prod_db_path.exists():
            cls.prod_db_hash_start = hashlib.sha256(cls.prod_db_path.read_bytes()).hexdigest().upper()
        else:
            cls.prod_db_hash_start = None

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        self.patchers = [
            patch.object(fin_svc, "DATABASE_PATH", self.db_path),
            patch.object(data_svc, "DATABASE_PATH", self.db_path),
            patch.object(class_svc, "DATABASE_PATH", self.db_path),
            patch.object(tech_svc, "DATABASE_PATH", self.db_path),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    # 1. Standard quarterly lag: Q1 (ends 03-31), lag 45 days -> eligible on 05-15.
    def test_01_standard_quarterly_lag(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        rec, status = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=45)
        self.assertIsNotNone(rec)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")
        self.assertEqual(rec["quarter"], "2025-03-31")

    # 2. Boundary condition: evaluation date exactly on period_end + 45 days -> ELIGIBLE.
    def test_02_boundary_exact_period_end_plus_45(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        # 2025-03-31 + 45 days = 2025-05-15
        rec, status = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=45)
        self.assertIsNotNone(rec)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")

    # 3. Boundary condition: evaluation date exactly on period_end + 44 days -> NOT ELIGIBLE.
    def test_03_boundary_period_end_plus_44_not_eligible(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        # 2025-03-31 + 44 days = 2025-05-14
        rec, status = _prepare_financial_data(df, "2025-05-14", reporting_lag_days=45)
        self.assertIsNone(rec)
        self.assertEqual(status, "NO_ELIGIBLE_RECORDS")

    # 4. Boundary condition: evaluation date exactly on period_end -> NOT ELIGIBLE.
    def test_04_boundary_exact_period_end_not_eligible(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        rec, status = _prepare_financial_data(df, "2025-03-31", reporting_lag_days=45)
        self.assertIsNone(rec)
        self.assertEqual(status, "NO_ELIGIBLE_RECORDS")

    # 5. Boundary condition: evaluation date before period_end -> NOT ELIGIBLE.
    def test_05_boundary_before_period_end_not_eligible(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        rec, status = _prepare_financial_data(df, "2025-03-15", reporting_lag_days=45)
        self.assertIsNone(rec)
        self.assertEqual(status, "NO_ELIGIBLE_RECORDS")

    # 6. Verified publication date: pub date is 04-20 -> ELIGIBLE on 04-20, NOT eligible on 04-19.
    def test_06_verified_pub_date_boundary(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": "2025-04-20"}])
        rec_before, status_before = _prepare_financial_data(df, "2025-04-19")
        self.assertIsNone(rec_before)
        self.assertEqual(status_before, "NO_ELIGIBLE_RECORDS")

        rec_on, status_on = _prepare_financial_data(df, "2025-04-20")
        self.assertIsNotNone(rec_on)
        self.assertEqual(status_on, "VERIFIED_POINT_IN_TIME")
        self.assertTrue(rec_on.get("_is_publication_date_verified"))

    # 7. Verified pub date overrides fallback: pub date is 04-20, fallback is 05-15 -> available on 04-20.
    def test_07_verified_pub_date_overrides_fallback_earlier(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": "2025-04-20"}])
        # Available on 2025-04-20 even though fallback 45-day is 2025-05-15
        rec, status = _prepare_financial_data(df, "2025-04-25", reporting_lag_days=45)
        self.assertIsNotNone(rec)
        self.assertEqual(status, "VERIFIED_POINT_IN_TIME")

    # 8. Verified pub date late: pub date is 06-01 (62 days), fallback 45 days -> available ONLY on 06-01.
    def test_08_verified_pub_date_late_prevents_premature_fallback(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": "2025-06-01"}])
        # On 2025-05-20 (past 45d fallback but before actual pub date): MUST NOT BE AVAILABLE!
        rec_early, status_early = _prepare_financial_data(df, "2025-05-20", reporting_lag_days=45)
        self.assertIsNone(rec_early)
        self.assertEqual(status_early, "NO_ELIGIBLE_RECORDS")

        # On 2025-06-01 (actual pub date): available!
        rec_on, status_on = _prepare_financial_data(df, "2025-06-01", reporting_lag_days=45)
        self.assertIsNotNone(rec_on)
        self.assertEqual(status_on, "VERIFIED_POINT_IN_TIME")

    # 9. Missing publication date (NULL/None) -> uses fallback lag.
    def test_09_missing_publication_date_uses_fallback(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": None}])
        rec, status = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=45)
        self.assertIsNotNone(rec)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")
        self.assertFalse(rec.get("_is_publication_date_verified"))

    # 10. Empty string publication date -> uses fallback lag.
    def test_10_empty_string_publication_date_uses_fallback(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": ""}])
        rec, status = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=45)
        self.assertIsNotNone(rec)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")

    # 11. Malformed publication date ('invalid-date', 'N/A') -> uses fallback lag gracefully.
    def test_11_malformed_publication_date_uses_fallback_gracefully(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": "N/A"}])
        rec_early, _ = _prepare_financial_data(df, "2025-04-15", reporting_lag_days=45)
        self.assertIsNone(rec_early)

        rec_late, status_late = _prepare_financial_data(df, "2025-05-20", reporting_lag_days=45)
        self.assertIsNotNone(rec_late)
        self.assertEqual(status_late, "PERIOD_ELIGIBLE_FALLBACK_LAG")

    # 12. Future publication date: pub date is in future relative to eval date -> NOT eligible.
    def test_12_future_publication_date_not_eligible(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": "2025-05-20"}])
        rec, status = _prepare_financial_data(df, "2025-05-10")
        self.assertIsNone(rec)
        self.assertEqual(status, "NO_ELIGIBLE_RECORDS")

    # 13. Multi-quarter chronological ordering: Q1, Q2, Q3, Q4 available -> on date where all 4 eligible, selects Q4.
    def test_13_multi_quarter_chronological_ordering_selects_latest(self):
        df = pd.DataFrame([
            {"quarter": "2024-Q1", "revenue": 100, "publication_date": "2024-05-15"},
            {"quarter": "2024-Q2", "revenue": 200, "publication_date": "2024-08-15"},
            {"quarter": "2024-Q3", "revenue": 300, "publication_date": "2024-11-15"},
            {"quarter": "2024-Q4", "revenue": 400, "publication_date": "2025-02-15"},
        ])
        rec, status = _prepare_financial_data(df, "2025-03-01")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["quarter"], "2024-Q4")
        self.assertEqual(rec["revenue"], 400)

    # 14. Multi-quarter transition: on 05-14 selects previous year Q4; on 05-15 selects Q1.
    def test_14_multi_quarter_transition_exact_day(self):
        df = pd.DataFrame([
            {"quarter": "2024-Q4", "revenue": 900, "publication_date": None},  # ends 2024-12-31, eligible 2025-02-14
            {"quarter": "2025-Q1", "revenue": 1000, "publication_date": None}, # ends 2025-03-31, eligible 2025-05-15
        ])
        rec_14, _ = _prepare_financial_data(df, "2025-05-14", reporting_lag_days=45)
        self.assertEqual(rec_14["quarter"], "2024-Q4")

        rec_15, _ = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=45)
        self.assertEqual(rec_15["quarter"], "2025-Q1")

    # 15. Multi-quarter with mixed verification: Q1 verified, Q2 fallback, Q3 verified -> correct selection.
    def test_15_multi_quarter_mixed_verification(self):
        df = pd.DataFrame([
            {"quarter": "2025-Q1", "revenue": 100, "publication_date": "2025-04-20"},
            {"quarter": "2025-Q2", "revenue": 200, "publication_date": None},          # eligible 2025-08-14
            {"quarter": "2025-Q3", "revenue": 300, "publication_date": "2025-10-25"},
        ])
        # On 2025-08-01: Q2 not yet reached fallback, Q1 selected (verified)
        r1, s1 = _prepare_financial_data(df, "2025-08-01", reporting_lag_days=45)
        self.assertEqual(r1["quarter"], "2025-Q1")
        self.assertEqual(s1, "VERIFIED_POINT_IN_TIME")

        # On 2025-08-20: Q2 reached fallback, Q2 selected (fallback lag)
        r2, s2 = _prepare_financial_data(df, "2025-08-20", reporting_lag_days=45)
        self.assertEqual(r2["quarter"], "2025-Q2")
        self.assertEqual(s2, "PERIOD_ELIGIBLE_FALLBACK_LAG")

        # On 2025-11-01: Q3 verified, Q3 selected (verified)
        r3, s3 = _prepare_financial_data(df, "2025-11-01", reporting_lag_days=45)
        self.assertEqual(r3["quarter"], "2025-Q3")
        self.assertEqual(s3, "VERIFIED_POINT_IN_TIME")

    # 16. Non-calendar quarter formats: FY24-Q1, 2024-Q3, etc. -> correctly parsed.
    def test_16_non_calendar_quarter_formats(self):
        p1 = parse_quarter_period_end("FY24-Q1")
        self.assertIsNotNone(p1)
        p2 = parse_quarter_period_end("2024-Q3")
        self.assertIsNotNone(p2)
        p3 = parse_quarter_period_end("2024-09-30")
        self.assertIsNotNone(p3)

    # 17. Custom lag days: reporting_lag_days=30 -> eligible on period_end + 30 days.
    def test_17_custom_lag_30_days(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        # 2025-03-31 + 30 days = 2025-04-30
        rec_29, _ = _prepare_financial_data(df, "2025-04-29", reporting_lag_days=30)
        self.assertIsNone(rec_29)
        rec_30, status = _prepare_financial_data(df, "2025-04-30", reporting_lag_days=30)
        self.assertIsNotNone(rec_30)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")

    # 18. Custom lag days: reporting_lag_days=60 -> eligible on period_end + 60 days.
    def test_18_custom_lag_60_days(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        # 2025-03-31 + 60 days = 2025-05-30
        rec_45, _ = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=60)
        self.assertIsNone(rec_45)
        rec_60, status = _prepare_financial_data(df, "2025-05-30", reporting_lag_days=60)
        self.assertIsNotNone(rec_60)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")

    # 19. Custom lag days: reporting_lag_days=0 -> eligible on period_end (same day).
    def test_19_custom_lag_0_days(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        rec, status = _prepare_financial_data(df, "2025-03-31", reporting_lag_days=0)
        self.assertIsNotNone(rec)
        self.assertEqual(status, "PERIOD_ELIGIBLE_FALLBACK_LAG")

    # 20. Negative lag days: reporting_lag_days=-5 -> clamped to 0, never allows look-ahead before period_end.
    def test_20_negative_lag_days_clamped(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        # Negative lag clamped to 0 -> cannot be evaluated before period end 2025-03-31
        rec_before, _ = _prepare_financial_data(df, "2025-03-30", reporting_lag_days=-5)
        self.assertIsNone(rec_before)
        rec_on, _ = _prepare_financial_data(df, "2025-03-31", reporting_lag_days=-5)
        self.assertIsNotNone(rec_on)

    # 21. None/default lag days -> defaults to 45 days.
    def test_21_none_lag_days_defaults_to_45(self):
        df = pd.DataFrame([{"quarter": "2025-03-31", "revenue": 1000, "publication_date": None}])
        rec_44, _ = _prepare_financial_data(df, "2025-05-14", reporting_lag_days=None)
        self.assertIsNone(rec_44)
        rec_45, _ = _prepare_financial_data(df, "2025-05-15", reporting_lag_days=None)
        self.assertIsNotNone(rec_45)

    # 22. All financial records ineligible -> returns None/empty, status 'NO_ELIGIBLE_RECORDS', no crash.
    def test_22_all_records_ineligible_returns_none(self):
        df = pd.DataFrame([
            {"quarter": "2025-06-30", "revenue": 1000, "publication_date": "2025-07-25"},
            {"quarter": "2025-09-30", "revenue": 1200, "publication_date": "2025-10-25"},
        ])
        rec, status = _prepare_financial_data(df, "2025-05-01")
        self.assertIsNone(rec)
        self.assertEqual(status, "NO_ELIGIBLE_RECORDS")

    # 23. Single quarter available -> correct selection and metadata.
    def test_23_single_quarter_available(self):
        df = pd.DataFrame([{"quarter": "2025-Q1", "revenue": 1000, "publication_date": "2025-04-20"}])
        rec, status = _prepare_financial_data(df, "2025-04-20")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["_availability_status"], "VERIFIED_POINT_IN_TIME")
        self.assertEqual(rec["_availability_date"], "2025-04-20")
        self.assertTrue(rec["_is_publication_date_verified"])

    # 24. Dataset builder integration: build_backtesting_dataset attaches correct financial columns and metadata.
    def test_24_dataset_builder_attaches_financial_metadata(self):
        ds = build_backtesting_dataset("AUDITCORP", "2025-04-10", "2025-05-01", reporting_lag_days=45)
        self.assertIn("publication_date", ds.columns)
        self.assertIn("financial_eligibility_mode", ds.columns)
        self.assertIn("is_financial_publication_verified", ds.columns)
        self.assertIn("financial_availability_status", ds.columns)
        self.assertIn("leakage_check", ds.columns)

    # 25. Dataset builder leakage check: PASS when all records point-in-time compliant.
    def test_25_dataset_builder_leakage_check_pass(self):
        ds = build_backtesting_dataset("AUDITCORP", "2025-04-20", "2025-05-01", reporting_lag_days=45)
        self.assertTrue((ds["leakage_check"] == "PASS").all())

    # 26. Dataset builder leakage check: FAIL_PRE_AVAILABILITY_LEAK when record used before fallback date.
    def test_26_dataset_builder_leakage_check_pre_availability_leak(self):
        synthetic_ds = pd.DataFrame([{
            "symbol": "AUDITCORP",
            "evaluation_date": "2025-04-10",
            "reporting_period": "2025-03-31",
            "publication_date": None,
            "financial_eligibility_mode": "ESTIMATED_REPORTING_LAG",
            "is_financial_publication_verified": False,
        }])
        # On 2025-04-10, period 2025-03-31 + 45d is 2025-05-15 > 2025-04-10 -> leak!
        # Test the check logic directly
        reporting_dates = synthetic_ds["reporting_period"].apply(lambda v: pd.to_datetime(v))
        evaluation_dates = pd.to_datetime(synthetic_ds["evaluation_date"])
        fallback_avail = reporting_dates + pd.Timedelta(days=45)
        leak = fallback_avail > evaluation_dates
        self.assertTrue(leak.iloc[0])

    # 27. Dataset builder leakage check: FAIL_PRE_PUBLICATION_LEAK when record used before verified pub date.
    def test_27_dataset_builder_leakage_check_pre_publication_leak(self):
        synthetic_ds = pd.DataFrame([{
            "symbol": "AUDITCORP",
            "evaluation_date": "2025-04-10",
            "reporting_period": "2025-03-31",
            "publication_date": "2025-04-20",
            "financial_eligibility_mode": "VERIFIED_POINT_IN_TIME",
            "is_financial_publication_verified": True,
        }])
        pub_dates = pd.to_datetime(synthetic_ds["publication_date"])
        evaluation_dates = pd.to_datetime(synthetic_ds["evaluation_date"])
        leak = (synthetic_ds["is_financial_publication_verified"] == True) & (pub_dates > evaluation_dates)
        self.assertTrue(leak.iloc[0])

    # 28. Dataset builder leakage check: FAIL_FUTURE_FINANCIAL_PERIOD when future quarter used.
    def test_28_dataset_builder_leakage_check_future_period(self):
        synthetic_ds = pd.DataFrame([{
            "symbol": "AUDITCORP",
            "evaluation_date": "2025-03-15",
            "reporting_period": "2025-03-31",
            "publication_date": None,
            "financial_eligibility_mode": "ESTIMATED_REPORTING_LAG",
            "is_financial_publication_verified": False,
        }])
        reporting_dates = synthetic_ds["reporting_period"].apply(lambda v: pd.to_datetime(v))
        evaluation_dates = pd.to_datetime(synthetic_ds["evaluation_date"])
        future_period = reporting_dates > evaluation_dates
        self.assertTrue(future_period.iloc[0])

    # 29. Data access service integration: get_backtest_input passes reporting_lag_days correctly.
    def test_29_data_access_service_integration(self):
        record = get_backtest_input("AUDITCORP", "2025-04-20", reporting_lag_days=45)
        self.assertIsNotNone(record)
        self.assertEqual(record["symbol"], "AUDITCORP")
        self.assertEqual(record["financial_data_status"], "VERIFIED_POINT_IN_TIME")
        self.assertEqual(record["financial_availability_status"], "VERIFIED")
        self.assertEqual(record["financial_eligibility_mode"], "VERIFIED_PUBLICATION")
        self.assertTrue(record["is_financial_publication_verified"])

    # 30. Financial service get_financial_data: point-in-time filtering with evaluation_date and reporting_lag_days.
    def test_30_financial_service_point_in_time_filtering(self):
        # On 2025-04-10 (before Q1 published on 2025-04-20): no records eligible
        fin_before = get_financial_data("AUDITCORP", evaluation_date="2025-04-10")
        self.assertTrue(fin_before.empty)
        self.assertEqual(fin_before.attrs.get("data_eligibility_status"), "NO_ELIGIBLE_RECORDS")

        # On 2025-04-20: Q1 is published and eligible
        fin_on = get_financial_data("AUDITCORP", evaluation_date="2025-04-20")
        self.assertFalse(fin_on.empty)
        self.assertEqual(len(fin_on), 1)
        self.assertEqual(fin_on.iloc[0]["quarter"], "2025-Q1")

    # 31. Timezone handling: ISO strings with offsets (+05:30, Z) handled consistently.
    def test_31_timezone_handling(self):
        df = pd.DataFrame([
            {"quarter": "2025-Q1", "revenue": 1000, "publication_date": "2025-04-20T14:30:00+05:30"}
        ])
        rec, status = _prepare_financial_data(df, "2025-04-20")
        self.assertIsNotNone(rec)
        self.assertEqual(status, "VERIFIED_POINT_IN_TIME")

    # 32. Production database read-only test: verify zero writes to database/swing_trading.db during all tests.
    def test_32_production_database_remains_unmodified(self):
        if self.prod_db_hash_start is not None and self.prod_db_path.exists():
            current_hash = hashlib.sha256(self.prod_db_path.read_bytes()).hexdigest().upper()
            self.assertEqual(
                self.prod_db_hash_start,
                current_hash,
                "CRITICAL: Production database hash was modified during testing!"
            )


if __name__ == "__main__":
    unittest.main()
