"""
Week 15 - Data Service Reliability Test Suite
==============================================

Comprehensive reliability validation for all major Data Engineering entry points
in the Swing Trading Intelligence Platform.

Tests:
1. Major data-service entry points
2. Individual stock retrieval
3. Multi-stock retrieval
4. Historical evaluation-date retrieval
5. Missing-symbol handling
6. Incomplete financial-data handling
7. Missing market/technical data handling
8. Consistent schema return guarantees
9. Explicit and actionable error messages

Data Engineer boundary:
- Validates data service behavior, contracts, and schema consistency.
- Does not modify or calculate trading signals/scores.
"""

import sys
import unittest
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_pipeline.data_service import (
    get_available_stocks,
    get_latest_price,
    get_stock_data,
    get_stock_data_with_adjusted_close,
    get_stock_record_count,
)
from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.technical_indicator_service import (
    get_latest_technical_indicators,
    get_technical_indicators,
)
from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_financial_record_count,
    get_financial_stocks,
    get_latest_financial_data,
)
from backend.data_pipeline.classification_service import (
    get_all_classifications,
    get_company_classification,
    get_industry_stocks,
    get_sector_stocks,
)
from backend.data_pipeline.stock_snapshot_service import get_stock_snapshot
from backend.data_pipeline.peer_group_service import (
    get_industry_peers,
    get_peer_group,
    get_sector_peers,
)
from backend.data_pipeline.entry_exit_input_service import (
    get_entry_exit_inputs,
    get_entry_exit_inputs_for_stocks,
)
from backend.data_pipeline.stop_target_input_service import get_stop_target_inputs
from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_input,
    get_backtest_inputs,
)
from backend.data_pipeline.backtest_result_service import (
    get_backtest_results,
    store_backtest_result,
    store_backtest_results,
    validate_backtest_result,
)


class TestWeek15ServiceReliability(unittest.TestCase):
    """
    Data Service Reliability tests verifying entry-point contracts, schemas,
    error handling, edge cases, and deterministic historical outputs.
    """

    KNOWN_VALID_SYMBOL = "INFY"
    KNOWN_SECOND_SYMBOL = "TCS"
    NON_EXISTENT_SYMBOL = "NONEXISTENT_XYZ_123"

    # ============================================================
    # 1. INDIVIDUAL STOCK RETRIEVAL & SCHEMA CONSISTENCY
    # ============================================================

    def test_data_service_stock_data_schema(self):
        """Verify get_stock_data returns consistent columns and ascending date order."""
        df = get_stock_data(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "Expected non-empty OHLCV for INFY")

        expected_cols = ["date", "open", "high", "low", "close", "volume"]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Missing expected OHLCV column: {col}")

        # Check chronological ordering
        dates = pd.to_datetime(df["date"]).tolist()
        self.assertEqual(dates, sorted(dates), "OHLCV data must be sorted chronologically ascending")

    def test_data_service_with_adjusted_close_schema(self):
        """Verify get_stock_data_with_adjusted_close returns adjusted_close."""
        df = get_stock_data_with_adjusted_close(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("adjusted_close", df.columns)

    def test_data_service_latest_price(self):
        """Verify get_latest_price returns dictionary with required fields."""
        latest = get_latest_price(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(latest, dict)
        for key in ["date", "open", "high", "low", "close", "volume"]:
            self.assertIn(key, latest)
            self.assertIsNotNone(latest[key])

    def test_technical_indicator_service_schema(self):
        """Verify get_technical_indicators returns standard indicator fields."""
        df = get_technical_indicators(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

        required_indicators = [
            "symbol",
            "date",
            "rsi",
            "macd",
            "macd_signal",
            "ema_20",
            "ema_50",
            "ema_200",
            "macd_histogram",
            "atr_14",
            "technical_score",
        ]
        for col in required_indicators:
            self.assertIn(col, df.columns, f"Missing indicator column: {col}")

    def test_financial_service_schema(self):
        """Verify get_financial_data returns standardized quarterly financial fields."""
        df = get_financial_data(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

        required_financials = [
            "symbol",
            "company_name",
            "sector",
            "industry",
            "quarter",
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]
        for col in required_financials:
            self.assertIn(col, df.columns, f"Missing financial column: {col}")

    def test_company_classification_schema(self):
        """Verify get_company_classification returns correct dictionary mapping."""
        info = get_company_classification(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(info, dict)
        self.assertEqual(info.get("symbol"), self.KNOWN_VALID_SYMBOL)
        self.assertIn("company_name", info)
        self.assertIn("sector", info)
        self.assertIn("industry", info)
        self.assertTrue(info["sector"], "Sector must not be empty")
        self.assertTrue(info["industry"], "Industry must not be empty")

    def test_stock_snapshot_schema(self):
        """Verify get_stock_snapshot aggregates market, financial, and identity state."""
        snapshot = get_stock_snapshot(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(snapshot, dict)
        self.assertEqual(snapshot.get("symbol"), self.KNOWN_VALID_SYMBOL)
        self.assertIn("market", snapshot)
        self.assertIn("financial", snapshot)
        self.assertIn("identity", snapshot)
        self.assertIn("data_quality", snapshot)
        self.assertEqual(snapshot.get("status"), "VALID")

    def test_peer_group_service_schema(self):
        """Verify get_peer_group returns peer group metrics."""
        peers = get_peer_group(self.KNOWN_VALID_SYMBOL)
        self.assertIsInstance(peers, dict)
        self.assertIn("sector", peers)
        self.assertIn("industry", peers)
        self.assertIn("sector_peers", peers)
        self.assertIn("industry_peers", peers)
        self.assertIsInstance(peers["sector_peers"], list)
        self.assertIsInstance(peers["industry_peers"], list)
        self.assertGreater(len(peers["sector_peers"]), 0)
        self.assertGreater(len(peers["industry_peers"]), 0)

    # ============================================================
    # 2. MULTI-STOCK RETRIEVAL
    # ============================================================

    def test_multi_stock_entry_exit_inputs(self):
        """Verify get_entry_exit_inputs_for_stocks processes multiple symbols independently."""
        symbols = [self.KNOWN_VALID_SYMBOL, self.KNOWN_SECOND_SYMBOL, self.NON_EXISTENT_SYMBOL]
        results = get_entry_exit_inputs_for_stocks(symbols)

        self.assertEqual(len(results), 3)

        # First two valid stocks must succeed
        self.assertEqual(results[0]["symbol"], self.KNOWN_VALID_SYMBOL)
        self.assertEqual(results[0]["data_quality"], "VALID")

        self.assertEqual(results[1]["symbol"], self.KNOWN_SECOND_SYMBOL)
        self.assertEqual(results[1]["data_quality"], "VALID")

        # Third invalid symbol must be handled safely without crashing the batch
        self.assertEqual(results[2]["symbol"], self.NON_EXISTENT_SYMBOL)
        self.assertIn(results[2]["data_quality"], ["INVALID", "INCOMPLETE"])

    # ============================================================
    # 3. HISTORICAL EVALUATION-DATE & DETERMINISTIC OUTPUTS
    # ============================================================

    def test_backtest_data_access_deterministic_output(self):
        """Verify backtest inputs return identical deterministic records for repeat queries."""
        inputs_run1 = get_backtest_inputs(
            self.KNOWN_VALID_SYMBOL,
            start_date="2025-08-01",
            end_date="2025-08-10",
        )
        inputs_run2 = get_backtest_inputs(
            self.KNOWN_VALID_SYMBOL,
            start_date="2025-08-01",
            end_date="2025-08-10",
        )

        self.assertEqual(len(inputs_run1), len(inputs_run2))
        self.assertGreater(len(inputs_run1), 0)

        for r1, r2 in zip(inputs_run1, inputs_run2):
            self.assertEqual(r1["evaluation_date"], r2["evaluation_date"])
            self.assertEqual(r1["close"], r2["close"])
            self.assertEqual(r1["reporting_period"], r2["reporting_period"])
            self.assertEqual(r1["leakage_check"], "PASS")

    # ============================================================
    # 4. MISSING SYMBOL & ERROR HANDLING
    # ============================================================

    def test_missing_symbol_data_service(self):
        """Verify get_stock_data returns empty DataFrame for unknown symbol without crashing."""
        df = get_stock_data(self.NON_EXISTENT_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_missing_symbol_latest_price(self):
        """Verify get_latest_price returns None for unknown symbol."""
        latest = get_latest_price(self.NON_EXISTENT_SYMBOL)
        self.assertIsNone(latest)

    def test_missing_symbol_technical_indicators(self):
        """Verify get_technical_indicators returns empty DataFrame for unknown symbol."""
        df = get_technical_indicators(self.NON_EXISTENT_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_missing_symbol_financials(self):
        """Verify get_financial_data returns empty standardized DataFrame for unknown symbol."""
        df = get_financial_data(self.NON_EXISTENT_SYMBOL)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_missing_symbol_backtest_inputs(self):
        """Verify get_backtest_inputs returns empty list for unknown symbol."""
        records = get_backtest_inputs(
            self.NON_EXISTENT_SYMBOL,
            start_date="2025-08-01",
            end_date="2025-08-10",
        )
        self.assertEqual(records, [])

    # ============================================================
    # 5. ACTIONABLE INPUT VALIDATION ERRORS
    # ============================================================

    def test_backtest_data_access_invalid_symbol_error(self):
        """Verify empty or non-string symbols raise actionable ValueError."""
        with self.assertRaises(ValueError) as ctx:
            get_backtest_input("", "2025-08-01")
        self.assertIn("Symbol must be a non-empty string", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            get_backtest_inputs(None, "2025-08-01", "2025-08-10")
        self.assertIn("Symbol must be a non-empty string", str(ctx.exception))

    def test_backtest_data_access_invalid_date_format_error(self):
        """Verify malformed dates raise actionable ValueError."""
        with self.assertRaises(ValueError) as ctx:
            get_backtest_input(self.KNOWN_VALID_SYMBOL, "01-08-2025")
        self.assertIn("Invalid date format", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            get_backtest_inputs(self.KNOWN_VALID_SYMBOL, "2025-08-01", "invalid-date")
        self.assertIn("Invalid date format", str(ctx.exception))

    def test_backtest_data_access_inverted_date_range_error(self):
        """Verify start_date > end_date raises actionable ValueError."""
        with self.assertRaises(ValueError) as ctx:
            get_backtest_inputs(self.KNOWN_VALID_SYMBOL, "2025-08-20", "2025-08-01")
        self.assertIn("cannot be after end_date", str(ctx.exception))

    def test_backtest_result_validation(self):
        """Verify validate_backtest_result enforces schema and catches missing fields."""
        valid_result = {
            "run_id": "RUN_001",
            "symbol": "INFY",
            "evaluation_date": "2025-08-15",
            "result_metadata": {"score": 85.0},
        }
        self.assertTrue(validate_backtest_result(valid_result))

        # Missing field
        invalid_result = {
            "run_id": "RUN_001",
            "symbol": "INFY",
            # missing evaluation_date and result_metadata
        }
        with self.assertRaises(ValueError) as ctx:
            validate_backtest_result(invalid_result)
        self.assertIn("Missing required backtest result fields", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
