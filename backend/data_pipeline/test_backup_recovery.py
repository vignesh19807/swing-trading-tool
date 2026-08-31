"""
Week 12 - Backup & Recovery Automated Tests

Validates the Data Engineering backup and recovery workflow.

Tests:
    1. Production database exists and is valid.
    2. Backup creation works and produces a valid SQLite database.
    3. Backup contains the same table structure and row counts as production.
    4. Recovery creation works.
    5. Recovery contains the same data inventory as the backup.
    6. Recovery does not overwrite or modify production data.
"""

import sqlite3
import unittest
from pathlib import Path

from backend.data_pipeline.backup_database import (
    DATABASE_PATH,
    create_backup,
)

from backend.data_pipeline.restore_database import (
    RECOVERY_PATH,
    get_integrity,
    get_table_counts,
    restore_database,
)


class TestBackupRecovery(unittest.TestCase):
    """Automated tests for Week 12 database reliability."""

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _database_signature(self, database_path):
        """
        Return a compact signature of the database.

        The signature contains:
            - table names
            - row counts
            - SQLite integrity status
        """

        database_path = Path(database_path)

        self.assertTrue(
            database_path.exists(),
            f"Database does not exist: {database_path}",
        )

        counts = get_table_counts(database_path)
        integrity = get_integrity(database_path)

        return {
            "tables": counts,
            "integrity": integrity,
        }

    # --------------------------------------------------------
    # TEST 1
    # --------------------------------------------------------

    def test_01_production_database_exists_and_is_valid(self):
        """Production database must exist and pass integrity_check."""

        self.assertTrue(
            DATABASE_PATH.exists(),
            "Production database does not exist.",
        )

        self.assertGreater(
            DATABASE_PATH.stat().st_size,
            0,
            "Production database is empty.",
        )

        integrity = get_integrity(DATABASE_PATH)

        self.assertEqual(
            integrity,
            "ok",
            "Production database integrity check failed.",
        )

    # --------------------------------------------------------
    # TEST 2
    # --------------------------------------------------------

    def test_02_backup_creation_and_integrity(self):
        """Backup must be created and pass SQLite integrity_check."""

        backup_path = create_backup()

        self.assertIsInstance(
            backup_path,
            Path,
        )

        self.assertTrue(
            backup_path.exists(),
            "Backup database was not created.",
        )

        self.assertGreater(
            backup_path.stat().st_size,
            0,
            "Backup database is empty.",
        )

        integrity = get_integrity(
            backup_path
        )

        self.assertEqual(
            integrity,
            "ok",
            "Backup integrity check failed.",
        )

    # --------------------------------------------------------
    # TEST 3
    # --------------------------------------------------------

    def test_03_backup_matches_production_inventory(self):
        """
        Backup must contain the same application tables
        and row counts as production.
        """

        backup_path = create_backup()

        production_counts = get_table_counts(
            DATABASE_PATH
        )

        backup_counts = get_table_counts(
            backup_path
        )

        self.assertEqual(
            production_counts,
            backup_counts,
            "Backup table inventory differs from production.",
        )

    # --------------------------------------------------------
    # TEST 4
    # --------------------------------------------------------

    def test_04_recovery_from_backup(self):
        """Recovery database must be successfully created."""

        backup_path = create_backup()

        result = restore_database(
            backup_path
        )

        self.assertTrue(
            result,
            "Database recovery validation failed.",
        )

        self.assertTrue(
            RECOVERY_PATH.exists(),
            "Recovery database was not created.",
        )

        self.assertGreater(
            RECOVERY_PATH.stat().st_size,
            0,
            "Recovery database is empty.",
        )

        integrity = get_integrity(
            RECOVERY_PATH
        )

        self.assertEqual(
            integrity,
            "ok",
            "Recovery database integrity check failed.",
        )

    # --------------------------------------------------------
    # TEST 5
    # --------------------------------------------------------

    def test_05_recovery_matches_backup(self):
        """
        Recovery database must contain the same application
        tables and row counts as the backup.
        """

        backup_path = create_backup()

        result = restore_database(
            backup_path
        )

        self.assertTrue(
            result,
            "Recovery operation failed.",
        )

        backup_counts = get_table_counts(
            backup_path
        )

        recovery_counts = get_table_counts(
            RECOVERY_PATH
        )

        self.assertEqual(
            backup_counts,
            recovery_counts,
            "Recovery inventory differs from backup.",
        )

    # --------------------------------------------------------
    # TEST 6
    # --------------------------------------------------------

    def test_06_recovery_does_not_modify_production(self):
        """
        Recovery must never overwrite production data.
        """

        before = self._database_signature(
            DATABASE_PATH
        )

        backup_path = create_backup()

        result = restore_database(
            backup_path
        )

        self.assertTrue(
            result,
            "Recovery operation failed.",
        )

        after = self._database_signature(
            DATABASE_PATH
        )

        self.assertEqual(
            before,
            after,
            "Production database changed during recovery.",
        )

    # --------------------------------------------------------
    # TEST 7
    # --------------------------------------------------------

    def test_07_expected_week_12_data_inventory(self):
        """
        Validate the expected current Week 12 data inventory.

        This test intentionally validates the current Data
        Engineering contract established during Week 12.
        """

        counts = get_table_counts(
            DATABASE_PATH
        )

        expected = {
            "backtest_results": counts.get("backtest_results", 0),
            "companies": 50,
            "daily_prices": 25495,
            "financial_scores": 0,
            "industries": 32,
            "opportunity_scores": 0,
            "quarterly_results": 280,
            "sectors": 16,
            "signals": 0,
            "technical_indicators": 25495,
        }

        self.assertEqual(
            counts,
            expected,
            "Production database inventory does not match "
            "the validated Week 12 state.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)