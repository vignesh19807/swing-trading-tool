"""
Data Service → RSI Technical Engine Integration Test
=====================================================

Integration test suite validating that market data fetched from Data Service
is processed correctly by calculate_rsi for real NSE stocks.

Includes manual TradingView RSI(14) validation printing for cross-checking.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import calculate_rsi


class TestRSIIntegration(unittest.TestCase):
    """
    Integration tests connecting Data Service to Technical Engine.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_real_stocks_rsi_generation(self):
        """
        Test RSI calculation against real stock data from Data Service.
        """
        print("\n==================================================")
        print("REAL DATA SERVICE -> RSI INTEGRATION TEST")
        print("==================================================")

        for symbol in self.TEST_SYMBOLS:
            with self.subTest(symbol=symbol):
                # 1. Fetch data from Data Service
                df = get_stock_data(symbol)

                # Verification: Data exists and has close column
                self.assertIsNotNone(df, f"Data returned for {symbol} is None")
                self.assertFalse(df.empty, f"Data returned for {symbol} is empty")
                self.assertIn("close", df.columns, f"No 'close' column in data for {symbol}")

                # Deep copy of original close column to check non-mutation
                original_close = df["close"].copy()

                # 2. Calculate RSI
                rsi = calculate_rsi(df["close"], period=14)

                # Verification: Output type and length
                self.assertIsInstance(rsi, pd.Series, f"RSI output for {symbol} is not a Series")
                self.assertEqual(len(rsi), len(df), f"RSI length mismatch for {symbol}")
                self.assertTrue(rsi.index.equals(df.index), f"Index mismatch for {symbol}")

                # Verification: Bounded between 0 and 100
                valid_rsi = rsi.dropna()
                self.assertGreater(len(valid_rsi), 0, f"No valid RSI values computed for {symbol}")
                self.assertTrue((valid_rsi >= 0.0).all(), f"RSI < 0 found in {symbol}")
                self.assertTrue((valid_rsi <= 100.0).all(), f"RSI > 100 found in {symbol}")

                # Verification: Original DataFrame was not modified
                pd.testing.assert_series_equal(df["close"], original_close)

                # 3. Print TradingView Manual Validation Data
                latest_date = df["date"].iloc[-1].strftime("%Y-%m-%d") if "date" in df.columns else "N/A"
                latest_rsi = rsi.iloc[-1]
                latest_close = df["close"].iloc[-1]

                print(f"\n--- {symbol} ---")
                print(f"Total Records : {len(df)}")
                print(f"Latest Date   : {latest_date}")
                print(f"Latest Close  : {latest_close:.2f}")
                print(f"Latest RSI(14): {latest_rsi:.2f}")
                print("\nLast 5 Days RSI(14) values for TradingView manual validation:")

                summary_df = pd.DataFrame({
                    "Date": df["date"].dt.strftime("%Y-%m-%d") if "date" in df.columns else df.index,
                    "Close": df["close"],
                    "RSI(14)": rsi.round(2)
                }).tail(5)
                print(summary_df.to_string(index=False))

        print("\n==================================================")
        print(" [PASS] ALL REAL DATA INTEGRATION TESTS PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
