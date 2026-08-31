"""
Week 14 - Data Engineering Integration Test

Flow:

Historical Backtest Data
        ↓
Backtest Data Access Service
        ↓
Decision Engine
        ↓
Backtest Result Service
        ↓
SQLite Database
        ↓
Result Retrieval

Data Engineer boundary:
- Does not modify the Decision Engine.
- Does not implement trading strategy.
- Does not calculate profitability.
"""

import sqlite3
import unittest
from uuid import uuid4

from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_inputs,
)

from backend.data_pipeline.backtest_result_service import (
    initialize_backtest_results_table,
    store_backtest_results,
    get_backtest_results,
)

from backend.engines.decision_engine import (
    calculate_opportunity_score,
)


class TestWeek14Integration(unittest.TestCase):

    SYMBOLS = [
        "INFY",
        "TCS",
        "RELIANCE",
    ]

    START_DATE = "2025-08-01"
    END_DATE = "2025-08-28"

    @classmethod
    def setUpClass(cls):
        initialize_backtest_results_table()

    def setUp(self):
        self.run_id = (
            f"WEEK14_TEST_{uuid4().hex[:8]}"
        )

    def tearDown(self):
        connection = sqlite3.connect(
            "database/swing_trading.db"
        )

        connection.execute(
            """
            DELETE FROM backtest_results
            WHERE run_id = ?
            """,
            (self.run_id,),
        )

        connection.commit()
        connection.close()

    def test_week14_integration(self):

        print("\n" + "=" * 70)
        print("WEEK 14 - DATA ENGINEERING INTEGRATION")
        print("=" * 70)

        all_results = []

        # ====================================================
        # 1. HISTORICAL DATA ACCESS
        # ====================================================

        for symbol in self.SYMBOLS:

            print("\n" + "-" * 70)
            print(f"PROCESSING: {symbol}")
            print("-" * 70)

            inputs = get_backtest_inputs(
                symbol,
                self.START_DATE,
                self.END_DATE,
            )

            self.assertGreater(
                len(inputs),
                0,
                f"No historical data for {symbol}",
            )

            print(
                "Historical records:",
                len(inputs),
            )

            # =================================================
            # 2. VERIFY DATES
            # =================================================

            dates = [
                str(record["evaluation_date"])[:10]
                for record in inputs
            ]

            self.assertEqual(
                dates,
                sorted(dates),
            )

            self.assertTrue(
                all(
                    self.START_DATE <= date <= self.END_DATE
                    for date in dates
                )
            )

            print(
                "Chronological:",
                dates == sorted(dates),
            )

            print(
                "Requested range valid: True"
            )

            # =================================================
            # 3. VERIFY LEAKAGE PROTECTION
            # =================================================

            leakage_failures = sum(
                record.get("leakage_check") != "PASS"
                for record in inputs
            )

            self.assertEqual(
                leakage_failures,
                0,
                f"Leakage detected for {symbol}",
            )

            print(
                "Leakage failures:",
                leakage_failures,
            )

            # =================================================
            # 4. CONSUME DECISION ENGINE
            # =================================================

            for record in inputs:

                evaluation_date = str(
                    record["evaluation_date"]
                )[:10]

                decision_result = (
                    calculate_opportunity_score(
                        symbol,
                        evaluation_date=evaluation_date,
                    )
                )

                self.assertIsInstance(
                    decision_result,
                    dict,
                )

                # Data Engineer does not calculate
                # or modify this result.

                all_results.append(
                    {
                        "run_id": self.run_id,
                        "symbol": symbol,
                        "evaluation_date": evaluation_date,
                        "result_metadata": decision_result,
                    }
                )

        # ====================================================
        # 5. STORE RESULTS
        # ====================================================

        print("\n" + "-" * 70)
        print("STORING RESULTS")
        print("-" * 70)

        inserted = store_backtest_results(
            all_results
        )

        print(
            "Results prepared:",
            len(all_results),
        )

        print(
            "Results inserted:",
            inserted,
        )

        self.assertEqual(
            inserted,
            len(all_results),
        )

        # ====================================================
        # 6. RETRIEVE RESULTS
        # ====================================================

        stored_results = get_backtest_results(
            run_id=self.run_id
        )

        print("\n" + "-" * 70)
        print("RETRIEVING RESULTS")
        print("-" * 70)

        print(
            "Results retrieved:",
            len(stored_results),
        )

        self.assertEqual(
            len(stored_results),
            len(all_results),
        )

        # ====================================================
        # 7. VERIFY SYMBOL COVERAGE
        # ====================================================

        stored_symbols = sorted(
            set(
                result["symbol"]
                for result in stored_results
            )
        )

        print(
            "Symbols:",
            stored_symbols,
        )

        self.assertEqual(
            stored_symbols,
            sorted(self.SYMBOLS),
        )

        # ====================================================
        # 8. VERIFY CHRONOLOGICAL RETRIEVAL
        # ====================================================

        stored_dates = [
            result["evaluation_date"]
            for result in stored_results
        ]

        self.assertEqual(
            stored_dates,
            sorted(stored_dates),
        )

        print(
            "Chronological retrieval:",
            stored_dates == sorted(stored_dates),
        )

        # ====================================================
        # 9. VERIFY DATABASE
        # ====================================================

        connection = sqlite3.connect(
            "database/swing_trading.db"
        )

        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM backtest_results
            WHERE run_id = ?
            """,
            (self.run_id,),
        ).fetchone()[0]

        connection.close()

        print(
            "Database row count:",
            count,
        )

        self.assertEqual(
            count,
            len(all_results),
        )

        # ====================================================
        # FINAL
        # ====================================================

        print("\n" + "=" * 70)
        print(
            "WEEK 14 INTEGRATION VALIDATION PASSED"
        )
        print("=" * 70)


if __name__ == "__main__":
    unittest.main()