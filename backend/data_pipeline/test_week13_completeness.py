"""
Week 13 Completeness Test Suite
===============================

This test suite validates the remaining Week 13 requirements:
1. Testing multiple representative stocks (INFY, TCS, RELIANCE, HDFCBANK, WIPRO) across multiple date ranges.
2. Explicitly checking for missing trading dates against the database sequence (excluding weekends/holidays).
3. Verifying historical technical/market date alignment.
4. Verifying the financial availability status limitation ("UNVERIFIED").
"""

import unittest
import pandas as pd
from backend.data_pipeline.backtesting_dataset_service import (
    build_backtesting_dataset,
    get_dataset_quality_report,
)
from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.data_service import get_connection

class TestWeek13Completeness(unittest.TestCase):
    """
    Validation tests for Week 13 Data Engineering requirements.
    """

    @classmethod
    def setUpClass(cls):
        cls.symbols = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "WIPRO"]
        # Define multiple historical ranges
        cls.ranges = [
            ("2025-08-01", "2025-08-28"),
            ("2026-08-01", "2026-08-14")
        ]

    def test_multiple_stocks_and_dates(self):
        """
        1. Test construction on representative stocks and dates.
        Verify that datasets are non-empty and have valid columns.
        """
        for symbol in self.symbols:
            for start, end in self.ranges:
                with self.subTest(symbol=symbol, start=start, end=end):
                    dataset = build_backtesting_dataset(symbol, start_date=start, end_date=end)
                    
                    # Validate basic presence and validity
                    self.assertFalse(dataset.empty, f"Dataset for {symbol} ({start} to {end}) should not be empty")
                    self.assertTrue((dataset["symbol"] == symbol).all())
                    
                    # Verify key columns exist
                    self.assertIn("evaluation_date", dataset.columns)
                    self.assertIn("close", dataset.columns)
                    self.assertIn("rsi", dataset.columns)
                    self.assertIn("company_name", dataset.columns)
                    
                    # Verify quality status is VALID
                    report = get_dataset_quality_report(dataset)
                    self.assertEqual(report["status"], "VALID")
                    self.assertEqual(report["duplicate_observations"], 0)
                    self.assertEqual(report["leakage_failures"], 0)

    def test_missing_trading_dates(self):
        """
        2. Check missing trading dates.
        The dataset evaluation dates must align exactly with the actual trading
        dates available in the database (i.e. daily_prices table for that period),
        ignoring weekends/holidays.
        """
        for symbol in self.symbols:
            for start, end in self.ranges:
                with self.subTest(symbol=symbol, start=start, end=end):
                    dataset = build_backtesting_dataset(symbol, start_date=start, end_date=end)
                    
                    # Retrieve the expected raw trading dates from historical service
                    hist_res = get_historical_data(symbol, start_date=start, end_date=end, include_adjusted_close=True)
                    self.assertEqual(hist_res["status"], "VALID")
                    raw_dates = hist_res["data"]["date"]
                    
                    # Normalize raw dates to compare
                    expected_dates = pd.to_datetime(raw_dates).dt.strftime("%Y-%m-%d").tolist()
                    actual_dates = dataset["evaluation_date"].tolist()
                    
                    # Verify they match 1-to-1
                    self.assertEqual(
                        actual_dates, 
                        expected_dates, 
                        f"Evaluation dates for {symbol} do not match database trading dates sequence."
                    )

    def test_technical_market_date_alignment(self):
        """
        3. Test historical technical inputs against stored market dates.
        Ensure that for every evaluation date, technical indicators align 1-to-1.
        We do this by validating that there are no mismatched or misaligned rows.
        """
        for symbol in self.symbols:
            for start, end in self.ranges:
                with self.subTest(symbol=symbol, start=start, end=end):
                    dataset = build_backtesting_dataset(symbol, start_date=start, end_date=end)
                    
                    # Get connection to query raw indicators for verification
                    connection = get_connection()
                    try:
                        cursor = connection.cursor()
                        cursor.execute("""
                            SELECT ti.date, ti.rsi, ti.macd
                            FROM technical_indicators AS ti
                            INNER JOIN companies AS c ON ti.company_id = c.id
                            WHERE c.symbol = ? AND ti.date >= ? AND ti.date <= ?
                        """, (symbol, start, end))
                        raw_tech_rows = cursor.fetchall()
                    finally:
                        connection.close()
                    
                    # If we have indicators in database, check that the dataset matches them
                    if raw_tech_rows:
                        tech_dict = {
                            pd.to_datetime(r[0]).strftime("%Y-%m-%d"): (r[1], r[2]) 
                            for r in raw_tech_rows
                        }
                        for _, row in dataset.iterrows():
                            eval_date = row["evaluation_date"]
                            if eval_date in tech_dict:
                                expected_rsi, expected_macd = tech_dict[eval_date]
                                if not pd.isna(row["rsi"]) and expected_rsi is not None:
                                    self.assertAlmostEqual(row["rsi"], expected_rsi, places=4)
                                if not pd.isna(row["macd"]) and expected_macd is not None:
                                    self.assertAlmostEqual(row["macd"], expected_macd, places=4)

    def test_financial_availability_limitation(self):
        """
        4. Financial availability before reporting period limitation verification.
        Ensure financial_availability_status is explicitly 'UNVERIFIED' or 'MISSING'
        and never assumed to be point-in-time publication dates.
        """
        for symbol in self.symbols:
            for start, end in self.ranges:
                with self.subTest(symbol=symbol, start=start, end=end):
                    dataset = build_backtesting_dataset(symbol, start_date=start, end_date=end)
                    
                    allowed_statuses = {"UNVERIFIED", "MISSING"}
                    actual_statuses = set(dataset["financial_availability_status"].unique())
                    
                    self.assertTrue(
                        actual_statuses.issubset(allowed_statuses),
                        f"Financial availability status for {symbol} contains unauthorized values: {actual_statuses}"
                    )
                    
                    # Also confirm no future-period leakage
                    reporting_dates = pd.to_datetime(dataset["reporting_period"], errors="coerce")
                    evaluation_dates = pd.to_datetime(dataset["evaluation_date"], errors="coerce")
                    
                    valid_mask = reporting_dates.notna() & evaluation_dates.notna()
                    future_leakage = reporting_dates[valid_mask] > evaluation_dates[valid_mask]
                    
                    self.assertEqual(
                        int(future_leakage.sum()),
                        0,
                        f"Found future financial period leakage in {symbol} dataset!"
                    )

if __name__ == "__main__":
    unittest.main()
