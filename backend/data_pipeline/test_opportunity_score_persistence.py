"""
Opportunity Score Persistence Test Suite
========================================

Validates save_opportunity_score() in backend/data_pipeline/opportunity_service.py.

Coverage:
1. TCS persistence (tech=56.0, fin=82.0358, mom=63.3333, opp=66.9459)
2. WIPRO persistence (tech=56.0, fin=71.3916, mom=75.0000, opp=66.1371)
3. RELIANCE persistence (tech=72.0, fin=51.9755, mom=100.0000, opp=71.9914)
4. INFY persistence (tech=75.0, fin=70.8268, mom=100.0000, opp=79.7894)
5. HDFCBANK persistence skip (INSUFFICIENT data with opportunity_score=None skipped)
6. Idempotency & duplicate execution (DELETE + INSERT replacing existing record)
7. Unknown ticker symbol handling
8. Empty / invalid symbol handling
9. Custom date persistence
10. Transaction safety and Rollback on insert failure

Author: Logic Engineer
"""

import sqlite3
import unittest
from unittest.mock import patch

from backend.data_pipeline.opportunity_service import (
    DATABASE_PATH,
    save_opportunity_score,
)


class TestOpportunityScorePersistence(unittest.TestCase):
    """Unit and Integration tests for Opportunity Score Database Persistence."""

    def setUp(self):
        """Setup test environment and clean up test rows."""
        self.test_date = "2026-08-26"
        self._cleanup_test_records()

    def tearDown(self):
        """Clean up test records after tests complete."""
        self._cleanup_test_records()

    def _cleanup_test_records(self):
        """Helper to remove test rows from opportunity_scores table."""
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM opportunity_scores WHERE date = ?", (self.test_date,)
            )
            connection.commit()
        finally:
            connection.close()

    def _query_score_row(self, symbol, date):
        """Helper to query opportunity_scores for a symbol and date."""
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    os.company_id,
                    c.symbol,
                    os.date,
                    os.technical_score,
                    os.financial_score,
                    os.momentum_score,
                    os.opportunity_score
                FROM opportunity_scores os
                JOIN companies c ON os.company_id = c.id
                WHERE c.symbol = ? AND os.date = ?
                """,
                (symbol.upper().strip(), date),
            )
            return cursor.fetchone()
        finally:
            connection.close()

    def test_save_tcs_opportunity_score(self):
        """Test persisting TCS opportunity score into database."""
        success = save_opportunity_score("TCS", date=self.test_date)
        self.assertTrue(success)

        row = self._query_score_row("TCS", self.test_date)
        self.assertIsNotNone(row)

        comp_id, sym, dt, tech, fin, mom, opp = row
        self.assertEqual(sym, "TCS")
        self.assertEqual(dt, self.test_date)
        self.assertEqual(tech, 56.0)
        self.assertEqual(fin, 82.0358)
        self.assertEqual(mom, 63.3333)
        self.assertEqual(opp, 66.9459)

    def test_save_wipro_opportunity_score(self):
        """Test persisting WIPRO opportunity score into database."""
        success = save_opportunity_score("WIPRO", date=self.test_date)
        self.assertTrue(success)

        row = self._query_score_row("WIPRO", self.test_date)
        self.assertIsNotNone(row)

        comp_id, sym, dt, tech, fin, mom, opp = row
        self.assertEqual(sym, "WIPRO")
        self.assertEqual(dt, self.test_date)
        self.assertEqual(tech, 56.0)
        self.assertEqual(fin, 71.3916)
        self.assertEqual(mom, 75.0)
        self.assertEqual(opp, 66.1371)

    def test_save_reliance_opportunity_score(self):
        """Test persisting RELIANCE opportunity score into database."""
        success = save_opportunity_score("RELIANCE", date=self.test_date)
        self.assertTrue(success)

        row = self._query_score_row("RELIANCE", self.test_date)
        self.assertIsNotNone(row)

        comp_id, sym, dt, tech, fin, mom, opp = row
        self.assertEqual(sym, "RELIANCE")
        self.assertEqual(dt, self.test_date)
        self.assertEqual(tech, 72.0)
        self.assertEqual(fin, 51.9755)
        self.assertEqual(mom, 100.0)
        self.assertEqual(opp, 71.9914)

    def test_save_infy_opportunity_score(self):
        """Test persisting INFY opportunity score into database."""
        success = save_opportunity_score("INFY", date=self.test_date)
        self.assertTrue(success)

        row = self._query_score_row("INFY", self.test_date)
        self.assertIsNotNone(row)

        comp_id, sym, dt, tech, fin, mom, opp = row
        self.assertEqual(sym, "INFY")
        self.assertEqual(dt, self.test_date)
        self.assertEqual(tech, 75.0)
        self.assertEqual(fin, 70.8268)
        self.assertEqual(mom, 100.0)
        self.assertEqual(opp, 79.7894)

    def test_hdfcbank_insufficient_data_skip(self):
        """Test that HDFCBANK (opportunity_score=None) skips persistence and returns False."""
        success = save_opportunity_score("HDFCBANK", date=self.test_date)
        self.assertFalse(success)

        # Confirm NO row was created in opportunity_scores table
        row = self._query_score_row("HDFCBANK", self.test_date)
        self.assertIsNone(row)

    def test_idempotency_duplicate_execution(self):
        """Test repeated save calls for same symbol and date update existing row without duplicates."""
        success1 = save_opportunity_score("TCS", date=self.test_date)
        self.assertTrue(success1)

        # Call a second time
        success2 = save_opportunity_score("TCS", date=self.test_date)
        self.assertTrue(success2)

        # Verify exactly 1 row exists
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM opportunity_scores os
                JOIN companies c ON os.company_id = c.id
                WHERE c.symbol = 'TCS' AND os.date = ?
                """,
                (self.test_date,),
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            connection.close()

    def test_unknown_symbol_handling(self):
        """Test graceful handling when company symbol does not exist in companies table."""
        success = save_opportunity_score("NONEXISTENT_TICKER", date=self.test_date)
        self.assertFalse(success)

    def test_empty_symbol_handling(self):
        """Test graceful handling for empty string or None symbols."""
        self.assertFalse(save_opportunity_score(""))
        self.assertFalse(save_opportunity_score(None))

    def test_custom_date_persistence(self):
        """Test persisting opportunity score under an explicit YYYY-MM-DD date."""
        custom_date = "2025-12-31"
        try:
            success = save_opportunity_score("TCS", date=custom_date)
            self.assertTrue(success)

            row = self._query_score_row("TCS", custom_date)
            self.assertIsNotNone(row)
            self.assertEqual(row[2], custom_date)
        finally:
            connection = sqlite3.connect(DATABASE_PATH)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM opportunity_scores WHERE date = ?", (custom_date,))
            connection.commit()
            connection.close()

    @patch("backend.data_pipeline.opportunity_service.calculate_opportunity_score")
    @patch("backend.data_pipeline.opportunity_service.sqlite3.connect")
    def test_transaction_rollback_on_insert_failure(self, mock_connect, mock_calc_opp):
        """Verify transaction rollback occurs and connection closes on SQL execution error."""
        mock_calc_opp.return_value = {
            "symbol": "TCS",
            "status": "VALID",
            "technical_score": 56.0,
            "financial_score": 82.0358,
            "momentum_score": 63.3333,
            "opportunity_score": 66.9459,
            "recommendation": "WATCH",
        }

        mock_conn = unittest.mock.MagicMock()
        mock_cursor = unittest.mock.MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (12,)

        def side_effect(sql, *args, **kwargs):
            if "INSERT" in sql:
                raise sqlite3.OperationalError("Database disk I/O error")
            return unittest.mock.MagicMock()

        mock_cursor.execute.side_effect = side_effect

        success = save_opportunity_score("TCS", date=self.test_date)
        self.assertFalse(success)

        # Verify rollback and close were called
        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
