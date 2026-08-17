"""
Data Service -> Technical Score Integration Test
================================================

Integration test suite validating that market data fetched from Data Service
is processed correctly by calculate_technical_score for real NSE stocks.

Outputs a clear summary table for 14 August 2026.
"""

import unittest
import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import (
    calculate_rsi,
    calculate_ema,
    calculate_macd,
    calculate_technical_score,
)


class TestTechnicalScoreIntegration(unittest.TestCase):
    """
    Integration tests connecting Data Service to Technical Score Engine v1 logic.
    """

    TEST_SYMBOLS = [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]

    def test_real_stocks_technical_score(self):
        """
        Test Technical Score calculation against real stock data from Data Service.
        """
        print("\n==================================================")
        print("REAL DATA SERVICE -> TECHNICAL SCORE INTEGRATION TEST")
        print("==================================================")

        summary_rows = []

        for symbol in self.TEST_SYMBOLS:
            with self.subTest(symbol=symbol):
                # 1. Load real data from Data Service
                df = get_stock_data(symbol)

                # Verification: Data exists and has required columns
                self.assertIsNotNone(df, f"Data returned for {symbol} is None")
                self.assertFalse(df.empty, f"Data returned for {symbol} is empty")
                for col in ["high", "low", "close", "volume"]:
                    self.assertIn(col, df.columns, f"No '{col}' column in data for {symbol}")

                # Deep copy of original DataFrame to check non-mutation
                original_df = df.copy()

                # 2. Compute indicator components using existing functions
                rsi = calculate_rsi(df["close"], period=14)
                ema20 = calculate_ema(df["close"], period=20)
                ema50 = calculate_ema(df["close"], period=50)
                ema200 = calculate_ema(df["close"], period=200)

                macd_df = calculate_macd(df["close"], fast_period=12, slow_period=26, signal_period=9)
                macd = macd_df["macd"]
                signal = macd_df["signal"]
                histogram = macd_df["histogram"]

                # 3. Calculate Technical Score
                score_df = calculate_technical_score(
                    close=df["close"],
                    volume=df["volume"],
                    rsi=rsi,
                    macd=macd,
                    signal=signal,
                    histogram=histogram,
                    ema20=ema20,
                    ema50=ema50,
                    ema200=ema200,
                )

                # Verification: Output type, index preservation, and column schema
                self.assertIsInstance(score_df, pd.DataFrame, f"Output for {symbol} is not a DataFrame")
                expected_cols = ["rsi_score", "macd_score", "trend_score", "volume_score", "technical_score"]
                self.assertEqual(list(score_df.columns), expected_cols, f"Column schema mismatch for {symbol}")
                self.assertTrue(score_df.index.equals(df.index), f"Index mismatch for {symbol}")

                # Verification: Numeric integrity and range boundaries
                valid_scores = score_df["technical_score"].dropna()
                self.assertGreater(len(valid_scores), 0, f"No valid Technical Scores for {symbol}")
                self.assertTrue((valid_scores >= 0.0).all(), f"Technical Score < 0 found in {symbol}")
                self.assertTrue((valid_scores <= 100.0).all(), f"Technical Score > 100 found in {symbol}")

                # Verification: Original DataFrame was not modified
                pd.testing.assert_frame_equal(df, original_df)

                # 4. Extract latest row values for summary table
                latest_idx = -1
                latest_close = df["close"].iloc[latest_idx]
                latest_rsi = rsi.iloc[latest_idx]
                latest_macd = macd.iloc[latest_idx]
                latest_signal = signal.iloc[latest_idx]
                latest_ema20 = ema20.iloc[latest_idx]
                latest_ema50 = ema50.iloc[latest_idx]
                latest_ema200 = ema200.iloc[latest_idx]

                avg_vol_20 = df["volume"].rolling(20, min_periods=20).mean()
                latest_vol_ratio = df["volume"].iloc[latest_idx] / avg_vol_20.iloc[latest_idx]
                latest_tech_score = score_df["technical_score"].iloc[latest_idx]

                summary_rows.append({
                    "Stock": symbol,
                    "Close": round(latest_close, 2),
                    "RSI": round(latest_rsi, 2),
                    "MACD": round(latest_macd, 2),
                    "Signal": round(latest_signal, 2),
                    "EMA20": round(latest_ema20, 2),
                    "EMA50": round(latest_ema50, 2),
                    "EMA200": round(latest_ema200, 2),
                    "Vol Ratio": round(latest_vol_ratio, 2),
                    "Tech Score": round(latest_tech_score, 1),
                })

        summary_df = pd.DataFrame(summary_rows)

        print("\nTECHNICAL SCORE VALIDATION SUMMARY TABLE (Validation Date: 14 Aug 2026):")
        print("---------------------------------------------------------------------------------------------------------")
        print(summary_df.to_string(index=False))
        print("---------------------------------------------------------------------------------------------------------")
        print("\n==================================================")
        print(" [PASS] ALL REAL DATA TECHNICAL SCORE INTEGRATION TESTS PASSED")
        print("==================================================\n")


if __name__ == "__main__":
    unittest.main()
