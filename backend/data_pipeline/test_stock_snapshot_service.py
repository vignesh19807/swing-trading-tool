"""
Week 11 - Unified Stock Snapshot Service Test
==============================================

Validates the Data Engineer unified stock snapshot contract.

Tests:
1. Five-stock integration
2. Required top-level fields
3. Identity/classification data
4. Latest market data
5. Latest financial data
6. Missing financial fields remain explicit
7. Invalid symbol handling
8. No trading decision fields
9. Source traceability
"""

import math
import unittest

from backend.data_pipeline.stock_snapshot_service import (
    get_stock_snapshot,
)


TEST_STOCKS = [
    "INFY",
    "TCS",
    "WIPRO",
    "RELIANCE",
    "HDFCBANK",
]


class TestStockSnapshotService(unittest.TestCase):

    def test_five_stock_integration(self):
        """All five representative stocks should return a snapshot."""

        for symbol in TEST_STOCKS:

            result = get_stock_snapshot(symbol)

            self.assertIsInstance(result, dict)
            self.assertEqual(result["symbol"], symbol)

            self.assertIn(
                result["status"],
                ["VALID", "PARTIAL", "INCOMPLETE"],
            )

    def test_required_top_level_fields(self):
        """Snapshot must expose the stable public contract."""

        result = get_stock_snapshot("INFY")

        required_fields = [
            "symbol",
            "status",
            "identity",
            "market",
            "financial",
            "data_quality",
            "source",
        ]

        for field in required_fields:
            self.assertIn(field, result)

    def test_identity_and_classification(self):
        """Identity must contain company, sector and industry."""

        result = get_stock_snapshot("INFY")

        identity = result["identity"]

        self.assertIsNotNone(identity)

        self.assertEqual(
            identity["symbol"],
            "INFY",
        )

        self.assertIn(
            "company_name",
            identity,
        )

        self.assertIn(
            "sector",
            identity,
        )

        self.assertIn(
            "industry",
            identity,
        )

    def test_latest_market_data(self):
        """Latest market snapshot must contain OHLCV fields."""

        result = get_stock_snapshot("INFY")

        market = result["market"]

        self.assertIsNotNone(market)

        for field in [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]:
            self.assertIn(field, market)

        self.assertGreater(
            market["close"],
            0,
        )

        self.assertGreaterEqual(
            market["volume"],
            0,
        )

    def test_latest_financial_data(self):
        """Latest financial record must expose standardized fields."""

        result = get_stock_snapshot("INFY")

        financial = result["financial"]

        self.assertIsNotNone(financial)

        for field in [
            "quarter",
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]:
            self.assertIn(field, financial)

    def test_missing_financial_fields_are_explicit(self):
        """
        Known missing financial values must remain missing and must
        be reported through data_quality.
        """

        result = get_stock_snapshot("HDFCBANK")

        self.assertEqual(
            result["status"],
            "PARTIAL",
        )

        missing = result[
            "data_quality"
        ]["financial_missing_fields"]

        self.assertIn(
            "roce",
            missing,
        )

        self.assertIn(
            "debt_equity",
            missing,
        )

        financial = result["financial"]

        self.assertIsNone(
            financial["roce"]
        )

        self.assertIsNone(
            financial["debt_equity"]
        )

    def test_nan_financial_values_are_detected(self):
        """Pandas NaN values must be treated as missing."""

        result = get_stock_snapshot("TCS")

        missing = result[
            "data_quality"
        ]["financial_missing_fields"]

        self.assertIn(
            "roce",
            missing,
        )

        value = result[
            "financial"
        ]["roce"]

        self.assertTrue(
            value is None
            or (
                isinstance(value, float)
                and math.isnan(value)
            )
        )

    def test_invalid_symbol(self):
        """Invalid symbols must not crash the service."""

        result = get_stock_snapshot(
            "NOT_A_REAL_STOCK"
        )

        self.assertEqual(
            result["status"],
            "INCOMPLETE",
        )

        self.assertIsNone(
            result["identity"]
        )

        self.assertIsNone(
            result["market"]
        )

        self.assertIsNone(
            result["financial"]
        )

    def test_empty_symbol(self):
        """Empty symbols must be handled safely."""

        result = get_stock_snapshot("")

        self.assertEqual(
            result["status"],
            "INVALID",
        )

        self.assertIsNone(
            result["identity"]
        )

    def test_source_traceability(self):
        """Every major dataset must expose its source."""

        result = get_stock_snapshot("INFY")

        source = result["source"]

        self.assertEqual(
            source["identity"],
            "classification_service",
        )

        self.assertEqual(
            source["market"],
            "data_service",
        )

        self.assertEqual(
            source["financial"],
            "financial_service",
        )

    def test_no_decision_or_score_fields(self):
        """
        Data Engineer snapshot must not generate trading decisions
        or scoring outputs.
        """

        result = get_stock_snapshot("INFY")

        forbidden_fields = [
            "technical_score",
            "financial_score",
            "momentum_score",
            "opportunity_score",
            "recommendation",
            "decision",
            "signal",
        ]

        for field in forbidden_fields:

            self.assertNotIn(
                field,
                result,
            )

    def test_historical_snapshot_with_evaluation_date(self):
        """Historical snapshot should respect evaluation date for market and financial."""
        eval_date = "2025-06-30"
        result = get_stock_snapshot("INFY", evaluation_date=eval_date)
        
        self.assertEqual(result["symbol"], "INFY")
        
        market = result["market"]
        self.assertIsNotNone(market)
        
        import pandas as pd
        m_date = pd.to_datetime(market["date"]).strftime("%Y-%m-%d")
        self.assertLessEqual(m_date, eval_date)
        
        financial = result["financial"]
        self.assertIsNotNone(financial)
        self.assertLessEqual(financial["quarter"], eval_date)
        
    def test_multiple_evaluation_dates(self):
        """Verify multiple evaluation dates produce different but valid snapshots."""
        eval1 = get_stock_snapshot("INFY", evaluation_date="2025-06-30")
        eval2 = get_stock_snapshot("INFY", evaluation_date="2025-12-31")
        
        import pandas as pd
        date1 = pd.to_datetime(eval1["market"]["date"]).strftime("%Y-%m-%d")
        date2 = pd.to_datetime(eval2["market"]["date"]).strftime("%Y-%m-%d")
        
        self.assertLessEqual(date1, "2025-06-30")
        self.assertLessEqual(date2, "2025-12-31")
        self.assertNotEqual(eval1["financial"]["quarter"], eval2["financial"]["quarter"])

    def test_invalid_evaluation_date(self):
        """Invalid evaluation date should raise ValueError."""
        with self.assertRaises(ValueError):
            get_stock_snapshot("INFY", evaluation_date="2024-13-99")
            
        with self.assertRaises(ValueError):
            get_stock_snapshot("INFY", evaluation_date="not-a-date")

if __name__ == "__main__":
    unittest.main()