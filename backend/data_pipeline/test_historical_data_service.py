"""
Week 13 - Historical Data Service Tests

Validates the Data Engineering historical-data contract.
"""

import unittest

from backend.data_pipeline.historical_data_service import (
    get_historical_data,
)


class TestHistoricalDataService(unittest.TestCase):

    def test_valid_historical_data(self):
        result = get_historical_data(
            "INFY",
            start_date="2025-08-01",
            end_date="2025-08-28",
            include_adjusted_close=True,
        )

        self.assertEqual(result["symbol"], "INFY")
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["records"], 18)

        self.assertIn("date", result["columns"])
        self.assertIn("open", result["columns"])
        self.assertIn("high", result["columns"])
        self.assertIn("low", result["columns"])
        self.assertIn("close", result["columns"])
        self.assertIn("volume", result["columns"])
        self.assertIn("adjusted_close", result["columns"])

        self.assertEqual(
            result["data_quality"]["missing_required_columns"],
            [],
        )

        self.assertEqual(
            result["data_quality"]["missing_values"],
            0,
        )

    def test_empty_symbol(self):
        result = get_historical_data("")

        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["records"], 0)

    def test_whitespace_symbol(self):
        result = get_historical_data("   ")

        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["records"], 0)

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            get_historical_data(
                "INFY",
                start_date="2025-99-99",
                end_date="2025-08-28",
            )

    def test_reversed_date_range(self):
        with self.assertRaises(ValueError):
            get_historical_data(
                "INFY",
                start_date="2025-08-28",
                end_date="2025-08-01",
            )

    def test_empty_date_range(self):
        result = get_historical_data(
            "INFY",
            start_date="2030-01-01",
            end_date="2030-01-31",
        )

        self.assertEqual(result["status"], "EMPTY")
        self.assertEqual(result["records"], 0)

    def test_adjusted_close_contract(self):
        result = get_historical_data(
            "INFY",
            start_date="2025-08-01",
            end_date="2025-08-28",
            include_adjusted_close=True,
        )

        self.assertEqual(result["status"], "VALID")
        self.assertIn(
            "adjusted_close",
            result["columns"],
        )

    def test_chronological_order(self):
        result = get_historical_data(
            "INFY",
            start_date="2025-08-01",
            end_date="2025-08-28",
        )

        dates = result["data"]["date"]

        self.assertTrue(
            dates.is_monotonic_increasing
        )


if __name__ == "__main__":
    unittest.main()