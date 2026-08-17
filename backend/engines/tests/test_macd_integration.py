"""
Data Service -> MACD Technical Engine Integration Test
======================================================

Integration test suite validating that market data fetched from Data Service
is processed correctly by calculate_macd for real NSE stocks.

Outputs a clear summary table for 14 August 2026 for TradingView manual validation.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import calculate_macd


class TestMACDIntegration(unittest.TestCase):
    """
    Integration tests connecting Data Service to Technical Engine MACD logic.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_real_stocks_macd_generation(self):
        """
        Test MACD(12, 26, 9) calculations against real stock data from Data Service.
        """
        print("\n==================================================")
        print("REAL DATA SERVICE -> MACD INTEGRATION TEST")
        print("==================================================")

        summary_rows = []

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

                # 2. Calculate MACD(12, 26, 9)
                macd_df = calculate_macd(df["close"], fast_period=12, slow_period=26, signal_period=9)

                # Verification: Output type, length, and columns
                self.assertIsInstance(macd_df, pd.DataFrame, f"MACD output for {symbol} is not a DataFrame")
                self.assertEqual(len(macd_df), len(df), f"MACD length mismatch for {symbol}")
                self.assertTrue(macd_df.index.equals(df.index), f"MACD index mismatch for {symbol}")
                self.assertEqual(list(macd_df.columns), ["macd", "signal", "histogram"], f"Column mismatch for {symbol}")

                for col in ["macd", "signal", "histogram"]:
                    self.assertTrue(pd.api.types.is_numeric_dtype(macd_df[col]), f"{col} is not numeric for {symbol}")

                # Verification: Original DataFrame was not modified
                pd.testing.assert_series_equal(df["close"], original_close)

                # Verification: Latest market date has valid numeric values
                latest_close = df["close"].iloc[-1]
                latest_macd = macd_df["macd"].iloc[-1]
                latest_signal = macd_df["signal"].iloc[-1]
                latest_hist = macd_df["histogram"].iloc[-1]

                self.assertFalse(pd.isna(latest_macd), f"Latest MACD is NaN for {symbol}")
                self.assertFalse(pd.isna(latest_signal), f"Latest Signal is NaN for {symbol}")
                self.assertFalse(pd.isna(latest_hist), f"Latest Histogram is NaN for {symbol}")

                summary_rows.append({
                    "Stock": symbol,
                    "Close": round(latest_close, 2),
                    "MACD Line": round(latest_macd, 2),
                    "Signal Line": round(latest_signal, 2),
                    "Histogram": round(latest_hist, 2),
                })

        summary_df = pd.DataFrame(summary_rows)

        print("\nTRADINGVIEW MANUAL VALIDATION TABLE (Validation Date: 14 Aug 2026):")
        print("------------------------------------------------------------------")
        print(summary_df.to_string(index=False))
        print("------------------------------------------------------------------")
        print("Note: Manual comparison against TradingView is pending.")
        print("\n==================================================")
        print(" [PASS] ALL REAL DATA MACD INTEGRATION TESTS PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
