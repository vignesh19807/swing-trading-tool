"""
Financial Health Score Persistence Test Suite
=============================================

Validates save_financial_health_scores() in backend/data_pipeline/financial_service.py.

Coverage:
1. TCS persistence (All 3 sub-scores valid)
2. INFY persistence (NULL valuation score stored as SQL NULL)
3. HDFCBANK persistence skip (INSUFFICIENT data with overall_score=None skipped)
4. Idempotency & duplicate execution (DELETE + INSERT replacing existing record)
5. Unknown / Invalid symbol safety
6. Transaction safety and Cleanup

Author: Logic Engineer
"""

import sqlite3
import unittest
from unittest.mock import patch

from backend.data_pipeline.financial_service import (
    DATABASE_PATH,
    save_financial_health_scores,
)


class TestFinancialScorePersistence(unittest.TestCase):
    """Unit and Integration tests for Financial Health Score Database Persistence."""

    def setUp(self):
        """Setup test environment and clean up test rows."""
        self.test_date = "2026-08-26"
        self._cleanup_test_records()

    def tearDown(self):
        """Clean up test records after tests complete."""
        self._cleanup_test_records()

    def _cleanup_test_records(self):
        """Helper to remove test rows from financial_scores table."""
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM financial_scores WHERE date = ?", (self.test_date,)
            )
            connection.commit()
        finally:
            connection.close()

    def _query_score_row(self, symbol, date):
        """Helper to query financial_scores for a symbol and date."""
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    fs.company_id,
                    c.symbol,
                    fs.date,
                    fs.profitability_score,
                    fs.growth_score,
                    fs.valuation_score,
                    fs.overall_score
                FROM financial_scores fs
                JOIN companies c ON fs.company_id = c.id
                WHERE c.symbol = ? AND fs.date = ?
                """,
                (symbol.upper().strip(), date),
            )
            return cursor.fetchone()
        finally:
            connection.close()

    def test_save_tcs_scores(self):
        """Test persisting TCS financial scores into database."""
        success = save_financial_health_scores("TCS", date=self.test_date)
        self.assertTrue(success)

        row = self._query_score_row("TCS", self.test_date)
        self.assertIsNotNone(row)

        comp_id, sym, dt, prof, growth, val, overall = row
        self.assertEqual(sym, "TCS")
        self.assertEqual(dt, self.test_date)
        self.assertIsNotNone(prof)
        self.assertIsNotNone(growth)
        self.assertIsNotNone(val)
        self.assertIsNotNone(overall)
        self.assertGreater(overall, 0.0)

    def test_save_infy_scores_null_valuation(self):
        """Test persisting INFY financial scores storing valuation_score as SQL NULL."""
        success = save_financial_health_scores("INFY", date=self.test_date)
        self.assertTrue(success)

        row = self._query_score_row("INFY", self.test_date)
        self.assertIsNotNone(row)

        comp_id, sym, dt, prof, growth, val, overall = row
        self.assertEqual(sym, "INFY")
        self.assertEqual(dt, self.test_date)
        self.assertIsNotNone(prof)
        self.assertIsNotNone(growth)
        # Valuation score MUST be SQL NULL (None in Python tuple)
        self.assertIsNone(val)
        # Overall score MUST be populated via dynamic re-weighting
        self.assertIsNotNone(overall)
        self.assertGreater(overall, 0.0)

    def test_hdfcbank_insufficient_data_skip(self):
        """Test that HDFCBANK (overall_score=None) skips persistence and returns False."""
        success = save_financial_health_scores("HDFCBANK", date=self.test_date)
        self.assertFalse(success)

        # Confirm NO row was created in financial_scores table
        row = self._query_score_row("HDFCBANK", self.test_date)
        self.assertIsNone(row)

    def test_idempotency_duplicate_execution(self):
        """Test repeated save calls for same symbol and date update existing row without duplicates."""
        success1 = save_financial_health_scores("TCS", date=self.test_date)
        self.assertTrue(success1)

        # Call a second time
        success2 = save_financial_health_scores("TCS", date=self.test_date)
        self.assertTrue(success2)

        # Verify exactly 1 row exists
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM financial_scores fs
                JOIN companies c ON fs.company_id = c.id
                WHERE c.symbol = 'TCS' AND fs.date = ?
                """,
                (self.test_date,),
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            connection.close()

    def test_unknown_symbol_handling(self):
        """Test graceful handling when company symbol does not exist in companies table."""
        success = save_financial_health_scores(
            "NONEXISTENT_TICKER", date=self.test_date
        )
        self.assertFalse(success)

    def test_empty_or_invalid_symbol_handling(self):
        """Test graceful handling for empty string or None symbols."""
        self.assertFalse(save_financial_health_scores(""))
        self.assertFalse(save_financial_health_scores(None))


if __name__ == "__main__":
    unittest.main()
