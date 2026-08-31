import sqlite3
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
        connection.close()

    def test_insert_result(self):
        result = store_backtest_result(
            "TEST_RUN_001",
            "INFY",
            "2025-08-28",
            {
                "opportunity_score": 72,
                "status": "QUALIFIED",
            },
        )

        self.assertTrue(result)

        records = get_backtest_results(
            run_id="TEST_RUN_001"
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["symbol"],
            "INFY",
        )
        self.assertEqual(
            records[0]["evaluation_date"],
            "2025-08-28",
        )

    def test_metadata_round_trip(self):
        metadata = {
            "opportunity_score": 81,
            "technical_score": 75,
            "financial_score": 88,
            "status": "QUALIFIED",
        }

        store_backtest_result(
            "TEST_RUN_002",
            "TCS",
            "2025-08-28",
            metadata,
        )

        records = get_backtest_results(
            run_id="TEST_RUN_002"
        )

        self.assertEqual(
            records[0]["result_metadata"],
            metadata,
        )

    def test_duplicate_prevention(self):
        first = store_backtest_result(
            "TEST_RUN_003",
            "INFY",
            "2025-08-28",
            {"score": 70},
        )

        second = store_backtest_result(
            "TEST_RUN_003",
            "INFY",
            "2025-08-28",
            {"score": 80},
        )

        self.assertTrue(first)
        self.assertFalse(second)

        records = get_backtest_results(
            run_id="TEST_RUN_003"
        )

        self.assertEqual(len(records), 1)

    def test_same_symbol_date_different_run_allowed(self):
        first = store_backtest_result(
            "RUN_A",
            "INFY",
            "2025-08-28",
            {"score": 70},
        )

        second = store_backtest_result(
            "RUN_B",
            "INFY",
            "2025-08-28",
            {"score": 80},
        )

        self.assertTrue(first)
        self.assertTrue(second)

        records = get_backtest_results(
            symbol="INFY",
            start_date="2025-08-28",
            end_date="2025-08-28",
        )

        self.assertEqual(len(records), 2)

    def test_empty_run_id_rejected(self):
        with self.assertRaises(ValueError):
            store_backtest_result(
                "",
                "INFY",
                "2025-08-28",
                {"score": 70},
            )

    def test_empty_symbol_rejected(self):
        with self.assertRaises(ValueError):
            store_backtest_result(
                "RUN_001",
                "",
                "2025-08-28",
                {"score": 70},
            )

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            store_backtest_result(
                "RUN_001",
                "INFY",
                "2025-99-99",
                {"score": 70},
            )

    def test_invalid_metadata_rejected(self):
        with self.assertRaises(ValueError):
            store_backtest_result(
                "RUN_001",
                "INFY",
                "2025-08-28",
                "invalid metadata",
            )

    def test_batch_insert(self):
        results = [
            {
                "run_id": "BATCH_001",
                "symbol": "INFY",
                "evaluation_date": "2025-08-25",
                "result_metadata": {
                    "score": 70
                },
            },
            {
                "run_id": "BATCH_001",
                "symbol": "TCS",
                "evaluation_date": "2025-08-26",
                "result_metadata": {
                    "score": 75
                },
            },
            {
                "run_id": "BATCH_001",
                "symbol": "RELIANCE",
                "evaluation_date": "2025-08-27",
                "result_metadata": {
                    "score": 80
                },
            },
        ]

        inserted = store_backtest_results(
            results
        )

        self.assertEqual(inserted, 3)

        records = get_backtest_results(
            run_id="BATCH_001"
        )

        self.assertEqual(len(records), 3)

    def test_batch_transaction_rollback(self):
        results = [
            {
                "run_id": "BATCH_002",
                "symbol": "INFY",
                "evaluation_date": "2025-08-25",
                "result_metadata": {
                    "score": 70
                },
            },
            {
                "run_id": "BATCH_002",
                "symbol": "TCS",
                "evaluation_date": "2025-99-99",
                "result_metadata": {
                    "score": 75
                },
            },
        ]

        with self.assertRaises(ValueError):
            store_backtest_results(results)

        records = get_backtest_results(
            run_id="BATCH_002"
        )

        self.assertEqual(len(records), 0)

    def test_run_filter(self):
        store_backtest_result(
            "RUN_X",
            "INFY",
            "2025-08-25",
            {"score": 60},
        )

        store_backtest_result(
            "RUN_Y",
            "INFY",
            "2025-08-25",
            {"score": 80},
        )

        records = get_backtest_results(
            run_id="RUN_X"
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["run_id"],
            "RUN_X",
        )

    def test_symbol_filter(self):
        store_backtest_result(
            "RUN_001",
            "INFY",
            "2025-08-25",
            {"score": 60},
        )

        store_backtest_result(
            "RUN_001",
            "TCS",
            "2025-08-25",
            {"score": 80},
        )

        records = get_backtest_results(
            symbol="TCS"
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["symbol"],
            "TCS",
        )

    def test_date_range_filter(self):
        for date in [
            "2025-08-20",
            "2025-08-21",
            "2025-08-22",
        ]:
            store_backtest_result(
                "RUN_RANGE",
                "INFY",
                date,
                {"score": 70},
            )

        records = get_backtest_results(
            run_id="RUN_RANGE",
            start_date="2025-08-21",
            end_date="2025-08-22",
        )

        self.assertEqual(len(records), 2)

    def test_reversed_date_filter_rejected(self):
        with self.assertRaises(ValueError):
            get_backtest_results(
                start_date="2025-08-28",
                end_date="2025-08-01",
            )

    def test_results_are_chronological(self):
        for date in [
            "2025-08-28",
            "2025-08-25",
            "2025-08-26",
        ]:
            store_backtest_result(
                "RUN_ORDER",
                "INFY",
                date,
                {"score": 70},
            )

        records = get_backtest_results(
            run_id="RUN_ORDER"
        )

        dates = [
            record["evaluation_date"]
            for record in records
        ]

        self.assertEqual(
            dates,
            sorted(dates),
        )

    def test_missing_evaluation_date_rejected(self):
        with self.assertRaises(ValueError):
            store_backtest_results(
                [
                    {
                        "run_id": "MISSING_DATE",
                        "symbol": "INFY",
                        "result_metadata": {
                            "score": 70
                        },
                    }
                ]
            )

    def test_incomplete_result_rejected(self):
        with self.assertRaises(ValueError):
            validate_backtest_result(
                {
                    "run_id": "INCOMPLETE_001",
                    "symbol": "INFY",
                    "evaluation_date": "2025-08-28",
                }
            )

    def test_complete_result_is_valid(self):
        result = {
            "run_id": "COMPLETE_001",
            "symbol": "INFY",
            "evaluation_date": "2025-08-28",
            "result_metadata": {
                "opportunity_score": 75,
                "status": "QUALIFIED",
            },
        }

        self.assertTrue(
            validate_backtest_result(result)
        )


if __name__ == "__main__":
    unittest.main()
