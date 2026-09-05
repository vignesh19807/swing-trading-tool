"""
Week 15 - Data Engineering Health Validation

Validates the integrity and point-in-time safety of the
historical data used by the Swing Trading Intelligence Platform.

Data Engineer boundary:
- Validates stored data.
- Validates data relationships.
- Validates historical/backtest safety.
- Does not calculate trading signals.
- Does not make trading decisions.
"""

import sqlite3
import unittest

from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_inputs,
)


DATABASE_PATH = "database/swing_trading.db"


class TestWeek15DataHealth(unittest.TestCase):

    REPRESENTATIVE_SYMBOLS = [
        "INFY",
        "TCS",
        "RELIANCE",
        "HDFCBANK",
        "ITC",
    ]

    def setUp(self):
        self.connection = sqlite3.connect(
            DATABASE_PATH
        )

    def tearDown(self):
        self.connection.close()

    def test_stock_universe(self):
        companies = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            """
        ).fetchone()[0]

        distinct_symbols = self.connection.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM companies
            """
        ).fetchone()[0]

        missing_symbols = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE symbol IS NULL
               OR TRIM(symbol) = ''
            """
        ).fetchone()[0]

        self.assertEqual(
            companies,
            50,
            "Expected 100 companies in the stock universe.",
        )

        self.assertEqual(
            companies,
            distinct_symbols,
            "Stock universe contains duplicate symbols.",
        )

        self.assertEqual(
            missing_symbols,
            0,
            "Stock universe contains missing symbols.",
        )

    def test_market_data_coverage(self):
        missing = self.connection.execute(
            """
            SELECT c.id
            FROM companies c
            LEFT JOIN daily_prices d
                ON c.id = d.company_id
            WHERE d.company_id IS NULL
            """
        ).fetchall()

        orphan_rows = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices d
            LEFT JOIN companies c
                ON c.id = d.company_id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        self.assertEqual(
            len(missing),
            0,
            "Companies without market data detected.",
        )

        self.assertEqual(
            orphan_rows,
            0,
            "Orphan market-data rows detected.",
        )

    def test_technical_data_coverage(self):
        missing = self.connection.execute(
            """
            SELECT c.id
            FROM companies c
            LEFT JOIN technical_indicators t
                ON c.id = t.company_id
            WHERE t.company_id IS NULL
            """
        ).fetchall()

        orphan_rows = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators t
            LEFT JOIN companies c
                ON c.id = t.company_id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        self.assertEqual(
            len(missing),
            0,
            "Companies without technical data detected.",
        )

        self.assertEqual(
            orphan_rows,
            0,
            "Orphan technical rows detected.",
        )

    def test_financial_data_coverage(self):
        missing = self.connection.execute(
            """
            SELECT c.id
            FROM companies c
            LEFT JOIN quarterly_results q
                ON c.id = q.company_id
            WHERE q.company_id IS NULL
            """
        ).fetchall()

        orphan_rows = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM quarterly_results q
            LEFT JOIN companies c
                ON c.id = q.company_id
            WHERE c.id IS NULL
            """
        ).fetchone()[0]

        self.assertEqual(
            len(missing),
            0,
            "Companies without financial data detected.",
        )

        self.assertEqual(
            orphan_rows,
            0,
            "Orphan financial rows detected.",
        )

    def test_market_technical_synchronization(self):
        daily_without_technical = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices d
            LEFT JOIN technical_indicators t
                ON d.company_id = t.company_id
               AND date(d.date) = date(t.date)
            WHERE t.id IS NULL
            """
        ).fetchone()[0]

        technical_without_daily = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators t
            LEFT JOIN daily_prices d
                ON t.company_id = d.company_id
               AND date(t.date) = date(d.date)
            WHERE d.id IS NULL
            """
        ).fetchone()[0]

        self.assertEqual(
            daily_without_technical,
            0,
            "Daily price rows without technical indicators.",
        )

        self.assertEqual(
            technical_without_daily,
            0,
            "Technical rows without matching market data.",
        )

    def test_market_technical_row_counts(self):
        mismatches = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT company_id, COUNT(*) AS daily_count
                FROM daily_prices
                GROUP BY company_id
            ) d
            JOIN (
                SELECT company_id, COUNT(*) AS technical_count
                FROM technical_indicators
                GROUP BY company_id
            ) t
                ON d.company_id = t.company_id
            WHERE d.daily_count != t.technical_count
            """
        ).fetchone()[0]

        self.assertEqual(
            mismatches,
            0,
            "Market and technical row counts do not match.",
        )

    def test_classification_data(self):
        missing_sector = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE sector IS NULL
               OR TRIM(sector) = ''
            """
        ).fetchone()[0]

        missing_industry = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM companies
            WHERE industry IS NULL
               OR TRIM(industry) = ''
            """
        ).fetchone()[0]

        sector_count = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM sectors
            """
        ).fetchone()[0]

        industry_count = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM industries
            """
        ).fetchone()[0]

        self.assertGreater(
            sector_count,
            0,
            "No sectors found.",
        )

        self.assertGreater(
            industry_count,
            0,
            "No industries found.",
        )

        self.assertEqual(
            missing_sector,
            0,
            "Companies without sector classification.",
        )

        self.assertEqual(
            missing_industry,
            0,
            "Companies without industry classification.",
        )

    def test_backtest_point_in_time_safety(self):
        violations = []

        for symbol in self.REPRESENTATIVE_SYMBOLS:

            records = get_backtest_inputs(
                symbol,
                "2025-08-01",
                "2025-08-28",
            )

            self.assertGreater(
                len(records),
                0,
                f"No backtest records returned for {symbol}.",
            )

            for record in records:

                evaluation_date = str(
                    record["evaluation_date"]
                )[:10]

                reporting_period = record.get(
                    "reporting_period"
                )

                if reporting_period is None:
                    continue

                reporting_period = str(
                    reporting_period
                )[:10]

                if reporting_period > evaluation_date:
                    violations.append(
                        (
                            symbol,
                            evaluation_date,
                            reporting_period,
                        )
                    )

        self.assertEqual(
            violations,
            [],
            (
                "Future financial periods returned by "
                "Backtest Data Access Service: "
                f"{violations[:10]}"
            ),
        )

    def test_required_tables_exist(self):
        required_tables = {
            "companies",
            "daily_prices",
            "technical_indicators",
            "quarterly_results",
            "sectors",
            "industries",
        }

        rows = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        existing_tables = {
            row[0]
            for row in rows
        }

        missing = (
            required_tables - existing_tables
        )

        self.assertEqual(
            missing,
            set(),
            f"Missing required tables: {missing}",
        )


if __name__ == "__main__":
    unittest.main()