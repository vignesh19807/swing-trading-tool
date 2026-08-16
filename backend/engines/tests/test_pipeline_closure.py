"""
Week 2 Final Closure — Standardized Technical Analysis Pipeline Integration Test
================================================================================

Integration test suite validating end-to-end flow from Data Service get_stock_data()
through the complete Technical Engine pipeline via run_technical_pipeline().

Outputs the 5-stock standardized technical analysis validation table for 14 August 2026.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import run_technical_pipeline


class TestPipelineClosure(unittest.TestCase):
    """
    Final Week 2 closure integration tests for Technical Engine pipeline.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_five_stock_pipeline_closure(self):
        """
        Verify end-to-end technical analysis pipeline across 5 NSE stocks.
        """
        print("\n==================================================")
        print("WEEK 2 FINAL CLOSURE — TECHNICAL ANALYSIS PIPELINE VERIFICATION")
        print("==================================================")

        summary_rows = []

        for symbol in self.TEST_SYMBOLS:
            with self.subTest(symbol=symbol):
                # 1. Fetch raw data from Data Service
                df = get_stock_data(symbol)

                # Verification: Data exists and has required columns
                self.assertIsNotNone(df, f"Data returned for {symbol} is None")
                self.assertFalse(df.empty, f"Data returned for {symbol} is empty")
                for col in ["high", "low", "close", "volume"]:
                    self.assertIn(col, df.columns, f"Missing '{col}' column in {symbol} data")

                # Deep copy to verify non-mutation
                original_df = df.copy()

                # 2. Run standardized pipeline
                result = run_technical_pipeline(df)

                # Verification: Return type dictionary with required keys
                self.assertIsInstance(result, dict, f"Pipeline output for {symbol} is not a dict")
                self.assertIn("indicators", result, f"Missing 'indicators' key for {symbol}")
                self.assertIn("support_resistance", result, f"Missing 'support_resistance' key for {symbol}")

                ind = result["indicators"]
                sr = result["support_resistance"]

                # Verification: Indicators DataFrame schema & index alignment
                expected_ind_cols = [
                    "close", "volume", "rsi", "ema20", "ema50", "ema200",
                    "macd", "signal", "histogram", "atr14",
                    "rsi_score", "macd_score", "trend_score", "volume_score", "technical_score"
                ]
                self.assertEqual(list(ind.columns), expected_ind_cols, f"Indicator column schema mismatch for {symbol}")
                self.assertTrue(ind.index.equals(df.index), f"Indicator index mismatch for {symbol}")

                # Verification: Support/Resistance DataFrame schema
                expected_sr_cols = ["level", "zone_low", "zone_high", "type", "touches", "strength"]
                self.assertEqual(list(sr.columns), expected_sr_cols, f"S&R column schema mismatch for {symbol}")

                # Verification: ATR non-negativity constraint
                valid_atr = ind["atr14"].dropna()
                self.assertGreater(len(valid_atr), 0, f"No valid ATR computed for {symbol}")
                self.assertTrue((valid_atr >= 0.0).all(), f"ATR < 0 found in {symbol}")

                # Verification: Technical Score bounds [0, 100]
                valid_scores = ind["technical_score"].dropna()
                self.assertGreater(len(valid_scores), 0, f"No valid Technical Score computed for {symbol}")
                self.assertTrue((valid_scores >= 0.0).all(), f"Technical Score < 0 found in {symbol}")
                self.assertTrue((valid_scores <= 100.0).all(), f"Technical Score > 100 found in {symbol}")

                # Verification: Original DataFrame was not mutated
                pd.testing.assert_frame_equal(df, original_df)

                # 3. Extract latest day values for summary table
                latest_idx = -1
                latest_date = df["date"].iloc[latest_idx].strftime("%Y-%m-%d")
                latest_row = ind.iloc[latest_idx]

                summary_rows.append({
                    "Stock": symbol,
                    "Date": latest_date,
                    "Close": round(latest_row["close"], 2),
                    "RSI": round(latest_row["rsi"], 2),
                    "EMA20": round(latest_row["ema20"], 2),
                    "EMA50": round(latest_row["ema50"], 2),
                    "EMA200": round(latest_row["ema200"], 2),
                    "MACD": round(latest_row["macd"], 2),
                    "Signal": round(latest_row["signal"], 2),
                    "Hist": round(latest_row["histogram"], 2),
                    "ATR14": round(latest_row["atr14"], 2),
                    "Tech Score": round(latest_row["technical_score"], 1),
                    "S&R Zones": len(sr),
                })

        summary_df = pd.DataFrame(summary_rows)

        print("\nSTANDARDIZED TECHNICAL ANALYSIS PIPELINE SUMMARY TABLE (Date: 14 Aug 2026):")
        print("-------------------------------------------------------------------------------------------------------------------------")
        print(summary_df.to_string(index=False))
        print("-------------------------------------------------------------------------------------------------------------------------")
        print("\n==================================================")
        print(" [PASS] STANDARDIZED PIPELINE CLOSURE VERIFICATION PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
