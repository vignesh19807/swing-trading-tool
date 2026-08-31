"""
Week 14 - Backtest Data Access Service Tests

Data Engineer boundary:
    - Validate historical input access.
    - Validate date handling.
    - Validate chronological ordering.
    - Validate historical leakage protection.
    - Do NOT modify or test trading decisions.
"""

import unittest

from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_input,
    get_backtest_inputs,
)


class TestBacktestDataAccessService(unittest.TestCase):

    def test_single_date_access(self):
        record = get_backtest_input(
            "INFY",
            "2025-08-28",
        )

        self.assertIsNotNone(record)
        self.assertEqual(record["symbol"], "INFY")
        self.assertEqual(
            str(record["evaluation_date"])[:10],
            "2025-08-28",
        )

    def test_multiple_representative_stocks(self):
        for symbol in [
            "INFY",
            "TCS",
            "RELIANCE",
        ]:
            record = get_backtest_input(
                symbol,
                "2025-08-28",
            )

            self.assertIsNotNone(record)
            self.assertEqual(
                record["symbol"],
                symbol,
            )

    def test_date_range_access(self):
        records = get_backtest_inputs(
            "INFY",
            "2025-08-01",
            "2025-08-28",
        )

        self.assertGreater(
            len(records),
            0,
        )

    def test_chronological_order(self):
        records = get_backtest_inputs(
            "INFY",
            "2025-08-01",
            "2025-08-28",
        )

        dates = [
            str(record["evaluation_date"])[:10]
            for record in records
        ]

        self.assertEqual(
            dates,
            sorted(dates),
        )

    def test_requested_date_range_is_respected(self):
        records = get_backtest_inputs(
            "INFY",
            "2025-08-01",
            "2025-08-28",
        )

        for record in records:
            date = str(
                record["evaluation_date"]
            )[:10]

            self.assertGreaterEqual(
                date,
                "2025-08-01",
            )

            self.assertLessEqual(
                date,
                "2025-08-28",
            )

    def test_no_future_financial_period(self):
        records = get_backtest_inputs(
            "INFY",
            "2025-08-01",
            "2025-08-28",
        )

        for record in records:
            evaluation_date = str(
                record["evaluation_date"]
            )[:10]

            reporting_period = record.get(
                "reporting_period"
            )

            if reporting_period:
                reporting_period = str(
                    reporting_period
                )[:10]

                self.assertLessEqual(
                    reporting_period,
                    evaluation_date,
                )

    def test_leakage_check_passes(self):
        records = get_backtest_inputs(
            "INFY",
            "2025-08-01",
            "2025-08-28",
        )

        for record in records:
            self.assertEqual(
                record.get("leakage_check"),
                "PASS",
            )

    def test_missing_historical_date_returns_none(self):
        record = get_backtest_input(
            "INFY",
            "2020-01-01",
        )

        self.assertIsNone(record)

    def test_empty_symbol(self):
        with self.assertRaises(ValueError):
            get_backtest_input(
                "",
                "2025-08-28",
            )

    def test_whitespace_symbol(self):
        with self.assertRaises(ValueError):
            get_backtest_input(
                "   ",
                "2025-08-28",
            )

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            get_backtest_input(
                "INFY",
                "2025-99-99",
            )

    def test_reversed_date_range(self):
        with self.assertRaises(ValueError):
            get_backtest_inputs(
                "INFY",
                "2025-08-28",
                "2025-08-01",
            )

    def test_future_date_rejected(self):
        with self.assertRaises(ValueError):
            get_backtest_input(
                "INFY",
                "2099-01-01",
            )

    def test_required_historical_fields(self):
        record = get_backtest_input(
            "INFY",
            "2025-08-28",
        )

        required_fields = [
            "symbol",
            "evaluation_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
            "market_data_status",
            "technical_data_status",
            "financial_availability_status",
            "leakage_check",
        ]

        for field in required_fields:
            self.assertIn(
                field,
                record,
            )

    def test_market_data_is_available(self):
        records = get_backtest_inputs(
            "INFY",
            "2025-08-01",
            "2025-08-28",
        )

        for record in records:
            self.assertEqual(
                record.get("market_data_status"),
                "AVAILABLE",
            )


if __name__ == "__main__":
    unittest.main()