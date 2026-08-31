"""
Week 13 - Backtesting Dataset Service Tests

Data Engineering tests for the historical backtesting dataset.

These tests verify:
    - historical rows are returned
    - evaluation dates are normalized
    - market data is available
    - technical data is correctly aligned
    - financial periods do not come from the future
    - duplicate observations are prevented
    - classification is attached
    - leakage checks pass
    - quality report is generated

These tests do NOT test trading decisions or strategy performance.
"""

import unittest

import pandas as pd

from backend.data_pipeline.backtesting_dataset_service import (
    build_backtesting_dataset,
    get_dataset_quality_report,
)


class TestBacktestingDatasetService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.symbol = "INFY"
        cls.start_date = "2025-08-01"
        cls.end_date = "2025-08-28"

        cls.dataset = build_backtesting_dataset(
            cls.symbol,
            start_date=cls.start_date,
            end_date=cls.end_date,
        )

    # ========================================================
    # BASIC DATASET TESTS
    # ========================================================

    def test_dataset_is_not_empty(self):
        """Historical dataset must contain observations."""

        self.assertFalse(
            self.dataset.empty
        )

    def test_expected_symbol(self):
        """Every row must belong to the requested symbol."""

        self.assertTrue(
            (self.dataset["symbol"] == self.symbol).all()
        )

    def test_expected_date_range(self):
        """Evaluation dates must remain inside requested range."""

        dates = pd.to_datetime(
            self.dataset["evaluation_date"]
        )

        self.assertGreaterEqual(
            dates.min(),
            pd.Timestamp(self.start_date),
        )

        self.assertLessEqual(
            dates.max(),
            pd.Timestamp(self.end_date),
        )

    def test_chronological_order(self):
        """Evaluation dates must be chronological."""

        dates = pd.to_datetime(
            self.dataset["evaluation_date"]
        )

        self.assertTrue(
            dates.is_monotonic_increasing
        )

    def test_no_duplicate_evaluation_dates(self):
        """One symbol/date must represent one observation."""

        duplicates = self.dataset.duplicated(
            subset=[
                "symbol",
                "evaluation_date",
            ]
        )

        self.assertEqual(
            int(duplicates.sum()),
            0,
        )

    # ========================================================
    # MARKET DATA
    # ========================================================

    def test_market_data_available(self):
        """Every evaluation date must have market data."""

        self.assertTrue(
            (
                self.dataset["market_data_status"]
                == "AVAILABLE"
            ).all()
        )

    def test_market_columns_present(self):
        """Required market columns must exist."""

        required = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
        ]

        for column in required:
            self.assertIn(
                column,
                self.dataset.columns,
            )

    # ========================================================
    # TECHNICAL DATA
    # ========================================================

    def test_technical_columns_present(self):
        """Required technical columns must exist."""

        required = [
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

        for column in required:
            self.assertIn(
                column,
                self.dataset.columns,
            )

    def test_technical_warmup_values_are_not_fabricated(self):
        """
        Early technical observations may legitimately contain
        missing values because indicators require warm-up data.
        """

        technical_columns = [
            "rsi",
            "macd",
            "macd_signal",
            "ema_20",
            "ema_50",
            "ema_200",
            "macd_histogram",
            "atr_14",
        ]

        # We only require that the dataset does not claim
        # missing technical data is available.
        missing_rows = self.dataset[
            self.dataset["technical_data_status"] == "MISSING"
        ]

        for _, row in missing_rows.iterrows():

            # At least one technical field should actually
            # be unavailable.
            self.assertTrue(
                row[technical_columns]
                .isna()
                .any()
            )

    # ========================================================
    # FINANCIAL DATA
    # ========================================================

    def test_financial_columns_present(self):
        """Financial fields must exist in the dataset."""

        required = [
            "reporting_period",
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]

        for column in required:
            self.assertIn(
                column,
                self.dataset.columns,
            )

    def test_no_future_financial_period(self):
        """
        A reporting period must never be after the
        evaluation date.
        """

        evaluation_dates = pd.to_datetime(
            self.dataset["evaluation_date"],
            errors="coerce",
        )

        reporting_dates = pd.to_datetime(
            self.dataset["reporting_period"],
            errors="coerce",
        )

        valid = (
            reporting_dates.notna()
            & evaluation_dates.notna()
        )

        future_periods = (
            reporting_dates[valid]
            > evaluation_dates[valid]
        )

        self.assertEqual(
            int(future_periods.sum()),
            0,
        )

    def test_financial_availability_is_explicit(self):
        """
        Current schema cannot prove exact public availability
        of quarterly financial results.

        Therefore availability must remain explicitly marked
        as UNVERIFIED rather than being silently assumed.
        """

        allowed = {
            "UNVERIFIED",
            "MISSING",
        }

        actual = set(
            self.dataset[
                "financial_availability_status"
            ].dropna().unique()
        )

        self.assertTrue(
            actual.issubset(allowed)
        )

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    def test_classification_columns_present(self):
        """Company classification must be attached."""

        required = [
            "company_name",
            "sector",
            "industry",
        ]

        for column in required:
            self.assertIn(
                column,
                self.dataset.columns,
            )

    def test_classification_identity(self):
        """INFY classification should identify the company."""

        self.assertTrue(
            self.dataset["company_name"]
            .notna()
            .all()
        )

        self.assertTrue(
            self.dataset["sector"]
            .notna()
            .all()
        )

        self.assertTrue(
            self.dataset["industry"]
            .notna()
            .all()
        )

    # ========================================================
    # LEAKAGE
    # ========================================================

    def test_leakage_check_passes(self):
        """No historical observation may contain future periods."""

        self.assertTrue(
            (
                self.dataset["leakage_check"]
                == "PASS"
            ).all()
        )

    # ========================================================
    # QUALITY REPORT
    # ========================================================

    def test_quality_report(self):
        """Quality report must identify a valid dataset."""

        report = get_dataset_quality_report(
            self.dataset
        )

        self.assertEqual(
            report["status"],
            "VALID",
        )

        self.assertEqual(
            report["rows"],
            len(self.dataset),
        )

        self.assertEqual(
            report["symbols"],
            1,
        )

        self.assertEqual(
            report["duplicate_observations"],
            0,
        )

        self.assertEqual(
            report["missing_market_data"],
            0,
        )

        self.assertEqual(
            report["future_financial_periods"],
            0,
        )

        self.assertEqual(
            report["leakage_failures"],
            0,
        )

    # ========================================================
    # INVALID INPUTS
    # ========================================================

    def test_empty_symbol(self):
        """Empty symbol must safely return an empty dataset."""

        result = build_backtesting_dataset(
            "",
            start_date=self.start_date,
            end_date=self.end_date,
        )

        self.assertTrue(
            result.empty
        )

    def test_invalid_date(self):
        """Invalid dates must raise ValueError."""

        with self.assertRaises(
            ValueError
        ):
            build_backtesting_dataset(
                self.symbol,
                start_date="2025-99-99",
                end_date=self.end_date,
            )

    def test_reversed_date_range(self):
        """Reversed date ranges must raise ValueError."""

        with self.assertRaises(
            ValueError
        ):
            build_backtesting_dataset(
                self.symbol,
                start_date="2025-08-28",
                end_date="2025-08-01",
            )


if __name__ == "__main__":
    unittest.main()