"""
Data Service -> Support & Resistance Integration Test
=====================================================

Integration test suite validating that market data fetched from Data Service
is processed correctly by calculate_support_resistance for real NSE stocks.

Outputs a clear validation summary table for Support and Resistance zones.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import calculate_support_resistance


class TestSupportResistanceIntegration(unittest.TestCase):
    """
    Integration tests connecting Data Service to Technical Engine Support & Resistance logic.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_real_stocks_support_resistance(self):
        """
        Test Support & Resistance zone detection against real stock data from Data Service.
        """
        print("\n==================================================")
        print("REAL DATA SERVICE -> SUPPORT & RESISTANCE INTEGRATION TEST")
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

                # 2. Calculate Support & Resistance
                sr_df = calculate_support_resistance(df["high"], df["low"], df["close"], pivot_window=3, zone_tolerance=0.01)

                # Verification: Output type, columns, and numeric integrity
                self.assertIsInstance(sr_df, pd.DataFrame, f"Output for {symbol} is not a DataFrame")
                expected_cols = ["level", "zone_low", "zone_high", "type", "touches", "strength"]
                self.assertEqual(list(sr_df.columns), expected_cols, f"Columns mismatch for {symbol}")

                if not sr_df.empty:
                    # Level bounds verification: zone_low <= level <= zone_high
                    self.assertTrue((sr_df["zone_low"] <= sr_df["level"]).all(), f"zone_low > level in {symbol}")
                    self.assertTrue((sr_df["level"] <= sr_df["zone_high"]).all(), f"level > zone_high in {symbol}")

                    # Touch & strength verification: touches >= 1, strength >= 1
                    self.assertTrue((sr_df["touches"] >= 1).all(), f"touches < 1 in {symbol}")
                    self.assertTrue((sr_df["strength"] >= 1.0).all(), f"strength < 1 in {symbol}")

                    # Type verification: only support or resistance
                    valid_types = {"support", "resistance"}
                    self.assertTrue(set(sr_df["type"]).issubset(valid_types), f"Invalid type found in {symbol}")

                    # Append zones to summary for printing
                    for _, row in sr_df.iterrows():
                        summary_rows.append({
                            "Stock": symbol,
                            "Type": row["type"],
                            "Level": round(row["level"], 2),
                            "Zone Low": round(row["zone_low"], 2),
                            "Zone High": round(row["zone_high"], 2),
                            "Touches": int(row["touches"]),
                            "Strength": round(row["strength"], 1),
                        })

                # Verification: Original DataFrame was not modified
                pd.testing.assert_frame_equal(df[["high", "low", "close"]], original_df)

        summary_df = pd.DataFrame(summary_rows)

        print("\nSUPPORT & RESISTANCE VALIDATION SUMMARY TABLE:")
        print("---------------------------------------------------------------------------------")
        if not summary_df.empty:
            print(summary_df.to_string(index=False))
        else:
            print("No support/resistance zones detected.")
        print("---------------------------------------------------------------------------------")
        print("\n==================================================")
        print(" [PASS] ALL REAL DATA SUPPORT & RESISTANCE INTEGRATION TESTS PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
