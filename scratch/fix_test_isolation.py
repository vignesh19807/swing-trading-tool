import pathlib

file_path = pathlib.Path("backend/data_pipeline/test_backtest_result_service.py")
content = file_path.read_text(encoding="utf-8")

old_str = """import sqlite3
import unittest

from backend.data_pipeline.backtest_result_service import (
    initialize_backtest_results_table,
    store_backtest_result,
    store_backtest_results,
    get_backtest_results,
    validate_backtest_result,
)


class TestBacktestResultService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_backtest_results_table()

    def setUp(self):
        connection = sqlite3.connect(
            "database/swing_trading.db"
        )

        connection.execute(
            "DELETE FROM backtest_results"
        )

        connection.commit()
        connection.close()"""

new_str = """import sqlite3
import unittest
import tempfile
import pathlib

import backend.data_pipeline.backtest_result_service as b_svc
from backend.data_pipeline.backtest_result_service import (
    initialize_backtest_results_table,
    store_backtest_result,
    store_backtest_results,
    get_backtest_results,
    validate_backtest_result,
)


class TestBacktestResultService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = pathlib.Path(cls.temp_dir.name) / "test_swing_trading.db"
        cls.orig_db_path = b_svc.DATABASE_PATH
        b_svc.DATABASE_PATH = cls.test_db_path
        initialize_backtest_results_table()

    @classmethod
    def tearDownClass(cls):
        b_svc.DATABASE_PATH = cls.orig_db_path
        cls.temp_dir.cleanup()

    def setUp(self):
        connection = sqlite3.connect(
            b_svc.DATABASE_PATH
        )

        connection.execute(
            "DELETE FROM backtest_results"
        )

        connection.commit()
        connection.close()"""

# Normalize newlines for matching
normalized_content = content.replace("\r\n", "\n")
normalized_old = old_str.replace("\r\n", "\n")
normalized_new = new_str.replace("\r\n", "\n")

if normalized_old in normalized_content:
    updated = normalized_content.replace(normalized_old, normalized_new, 1)
    # Save back with original CRLF
    file_path.write_text(updated.replace("\n", "\r\n"), encoding="utf-8")
    print("Successfully patched test_backtest_result_service.py")
else:
    print("Could not find match in test_backtest_result_service.py")

