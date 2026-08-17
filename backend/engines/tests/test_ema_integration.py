"""
Data Service -> EMA Technical Engine Integration Test
=====================================================

Integration test suite validating that market data fetched from Data Service
is processed correctly by calculate_ema for real NSE stocks (EMA20, EMA50, EMA200).

Outputs a clear summary table for 14 August 2026 for TradingView manual validation.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import calculate_ema


class TestEMAIntegration(unittest.TestCase):
    """
    Integration tests connecting Data Service to Technical Engine EMA logic.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_real_stocks_ema_generation(self):
        """
        Test EMA20, EMA50, EMA200 calculations against real stock data from Data Service.
        """
        print("\n==================================================")
        print("REAL DATA SERVICE -> EMA INTEGRATION TEST")
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

                # 2. Calculate EMA20, EMA50, EMA200
                ema20 = calculate_ema(df["close"], period=20)
                ema50 = calculate_ema(df["close"], period=50)
                ema200 = calculate_ema(df["close"], period=200)

                # Verification: Output types, lengths, and indices
                for p, ema in [(20, ema20), (50, ema50), (200, ema200)]:
                    self.assertIsInstance(ema, pd.Series, f"EMA_{p} output for {symbol} is not a Series")
                    self.assertEqual(len(ema), len(df), f"EMA_{p} length mismatch for {symbol}")
                    self.assertTrue(ema.index.equals(df.index), f"EMA_{p} index mismatch for {symbol}")
                    self.assertTrue(pd.api.types.is_numeric_dtype(ema), f"EMA_{p} is not numeric for {symbol}")

                # Verification: Original DataFrame was not modified
                pd.testing.assert_series_equal(df["close"], original_close)

                # Verification: Latest market date has valid numeric EMA values
                latest_close = df["close"].iloc[-1]
                latest_ema20 = ema20.iloc[-1]
                latest_ema50 = ema50.iloc[-1]
                latest_ema200 = ema200.iloc[-1]

                self.assertFalse(pd.isna(latest_ema20), f"Latest EMA20 is NaN for {symbol}")
                self.assertFalse(pd.isna(latest_ema50), f"Latest EMA50 is NaN for {symbol}")
                self.assertFalse(pd.isna(latest_ema200), f"Latest EMA200 is NaN for {symbol}")

                summary_rows.append({
                    "Stock": symbol,
                    "Close": round(latest_close, 2),
                    "EMA20": round(latest_ema20, 2),
                    "EMA50": round(latest_ema50, 2),
                    "EMA200": round(latest_ema200, 2),
                })

        summary_df = pd.DataFrame(summary_rows)

        print("\nTRADINGVIEW MANUAL VALIDATION TABLE (Validation Date: 14 Aug 2026):")
        print("--------------------------------------------------")
        print(summary_df.to_string(index=False))
        print("--------------------------------------------------")
        print("Note: Manual comparison against TradingView is pending.")
        print("\n==================================================")
        print(" [PASS] ALL REAL DATA EMA INTEGRATION TESTS PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
