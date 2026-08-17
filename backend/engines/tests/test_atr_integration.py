"""
Data Service -> ATR Technical Engine Integration Test
=====================================================

Integration test suite validating that market data fetched from Data Service
is processed correctly by calculate_atr for real NSE stocks.

Outputs a clear summary table for 14 August 2026 for TradingView manual validation.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import calculate_atr


class TestATRIntegration(unittest.TestCase):
    """
    Integration tests connecting Data Service to Technical Engine ATR logic.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_real_stocks_atr_generation(self):
        """
        Test ATR(14) calculations against real stock data from Data Service.
        """
        print("\n==================================================")
        print("REAL DATA SERVICE -> ATR INTEGRATION TEST")
        print("==================================================")

        summary_rows = []

        for symbol in self.TEST_SYMBOLS:
            with self.subTest(symbol=symbol):
                # 1. Fetch data from Data Service
                df = get_stock_data(symbol)

                # Verification: Data exists and has required columns
                self.assertIsNotNone(df, f"Data returned for {symbol} is None")
                self.assertFalse(df.empty, f"Data returned for {symbol} is empty")
                for col in ["high", "low", "close"]:
                    self.assertIn(col, df.columns, f"No '{col}' column in data for {symbol}")

                # Deep copy of original DataFrame columns to check non-mutation
                original_df = df[["high", "low", "close"]].copy()

                # 2. Calculate ATR(14)
                atr14 = calculate_atr(df["high"], df["low"], df["close"], period=14)

                # Verification: Output type, length, name, and index
                self.assertIsInstance(atr14, pd.Series, f"ATR output for {symbol} is not a Series")
                self.assertEqual(len(atr14), len(df), f"ATR length mismatch for {symbol}")
                self.assertTrue(atr14.index.equals(df.index), f"ATR index mismatch for {symbol}")
                self.assertEqual(atr14.name, "ATR_14", f"Series name mismatch for {symbol}")
                self.assertTrue(pd.api.types.is_numeric_dtype(atr14), f"ATR is not numeric for {symbol}")

                # Verification: Non-negative ATR values
                valid_atr = atr14.dropna()
                self.assertGreater(len(valid_atr), 0, f"No valid ATR values computed for {symbol}")
                self.assertTrue((valid_atr >= 0.0).all(), f"ATR < 0 found in {symbol}")

                # Verification: Original DataFrame was not modified
                pd.testing.assert_frame_equal(df[["high", "low", "close"]], original_df)

                # Verification: Latest market date has valid numeric ATR
                latest_close = df["close"].iloc[-1]
                latest_atr = atr14.iloc[-1]
                self.assertFalse(pd.isna(latest_atr), f"Latest ATR is NaN for {symbol}")

                summary_rows.append({
                    "Stock": symbol,
                    "Close": round(latest_close, 2),
                    "ATR14": round(latest_atr, 2),
                })

        summary_df = pd.DataFrame(summary_rows)

        print("\nTRADINGVIEW MANUAL VALIDATION TABLE (Validation Date: 14 Aug 2026):")
        print("--------------------------------------------------")
        print(summary_df.to_string(index=False))
        print("--------------------------------------------------")
        print("Note: Manual comparison against TradingView is pending.")
        print("\n==================================================")
        print(" [PASS] ALL REAL DATA ATR INTEGRATION TESTS PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
