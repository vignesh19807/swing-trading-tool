import datetime
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest

pytestmark = pytest.mark.requires_preseeded_db

from backend.data_pipeline.financial_service import (
    get_financial_data,
    get_latest_financial_data,
    parse_quarter_period_end,
)
from backend.data_pipeline.stock_snapshot_service import get_stock_snapshot
from backend.data_pipeline.backtesting_dataset_service import (
    _prepare_financial_data,
    build_backtesting_dataset,
)
from backend.data_pipeline.backtest_data_access_service import (
    get_backtest_input,
    get_backtest_inputs,
)


@pytest.fixture
def sample_financial_df():
    """
    Standard sample DataFrame representing quarterly financials with varying publication dates.
    """
    return pd.DataFrame([
        {
            "id": 1,
            "company_id": 101,
            "quarter": "2023-12-31",
            "revenue": 1000.0,
            "net_profit": 150.0,
            "operating_margin": 15.0,
            "pe_ratio": 20.0,
            "pb_ratio": 3.0,
            "debt_to_equity": 0.5,
            "roe": 18.0,
            "eps": 10.0,
            "publication_date": None,  # unverified / missing
        },
        {
            "id": 2,
            "company_id": 101,
            "quarter": "2024-03-31",
            "revenue": 1200.0,
            "net_profit": 180.0,
            "operating_margin": 16.0,
            "pe_ratio": 22.0,
            "pb_ratio": 3.2,
            "debt_to_equity": 0.45,
            "roe": 19.0,
            "eps": 12.0,
            "publication_date": "2024-05-15 18:00:00",  # verified Q4 announcement
        },
        {
            "id": 3,
            "company_id": 101,
            "quarter": "2024-06-30",
            "revenue": 1300.0,
            "net_profit": 200.0,
            "operating_margin": 16.5,
            "pe_ratio": 24.0,
            "pb_ratio": 3.5,
            "debt_to_equity": 0.4,
            "roe": 20.0,
            "eps": 14.0,
            "publication_date": "2024-08-10 17:30:00",  # future relative to early August
        },
    ])


class TestP1PointInTimeFinancialIntegrity:
    """
    Comprehensive test suite for P1 Point-in-Time (PIT) Financial Data Integrity.
    """

    def test_01_test_a_unverified_record_excluded_in_strict_mode(self, sample_financial_df):
        """
        Test A: Record with publication_date=None returns fallback in legacy mode,
        but is completely excluded in strict mode (require_verified_publication_date=True).
        """
        # Slice only the unverified record (2023-12-31)
        df_unverified = sample_financial_df[sample_financial_df["quarter"] == "2023-12-31"].copy()

        # Evaluation date after period_end + 45 days (2024-02-14 is 45 days after 2023-12-31)
        eval_date = "2024-03-01"

        # 1. Legacy mode (require_verified_publication_date=False):
        # Uses period_end + 45 fallback, so record is eligible
        rec_legacy, status_legacy = _prepare_financial_data(
            df_unverified,
            evaluation_date=eval_date,
            reporting_lag_days=45,
            require_verified_publication_date=False,
        )
        assert rec_legacy is not None
        assert rec_legacy["quarter"] == "2023-12-31"
        assert status_legacy == "PERIOD_ELIGIBLE_FALLBACK_LAG"

        # 2. Strict mode (require_verified_publication_date=True):
        # Unverified publication_date rejected, no fallback allowed -> NO_ELIGIBLE_RECORDS
        rec_strict, status_strict = _prepare_financial_data(
            df_unverified,
            evaluation_date=eval_date,
            reporting_lag_days=45,
            require_verified_publication_date=True,
        )
        assert rec_strict is None
        assert status_strict == "NO_ELIGIBLE_RECORDS"

    def test_02_test_b_valid_publication_date_eligible_in_strict_mode(self, sample_financial_df):
        """
        Test B: Record with valid publication date before evaluation date is eligible in strict mode.
        """
        df_verified = sample_financial_df[sample_financial_df["quarter"] == "2024-03-31"].copy()
        # publication_date is "2024-05-15 18:00:00"
        eval_date = "2024-05-20"

        rec_strict, status_strict = _prepare_financial_data(
            df_verified,
            evaluation_date=eval_date,
            reporting_lag_days=45,
            require_verified_publication_date=True,
        )
        assert rec_strict is not None
        assert rec_strict["quarter"] == "2024-03-31"
        assert rec_strict["revenue"] == 1200.0
        assert status_strict == "VERIFIED_POINT_IN_TIME"
        assert rec_strict["_is_publication_date_verified"] is True

    def test_03_test_c_publication_after_evaluation_date_excluded(self, sample_financial_df):
        """
        Test C: Record published after evaluation date is excluded in strict mode (and legacy mode).
        """
        df_verified = sample_financial_df[sample_financial_df["quarter"] == "2024-03-31"].copy()
        # publication_date is "2024-05-15 18:00:00"
        # Evaluation is before publication
        eval_date = "2024-05-10"

        rec_strict, status_strict = _prepare_financial_data(
            df_verified,
            evaluation_date=eval_date,
            reporting_lag_days=45,
            require_verified_publication_date=True,
        )
        assert rec_strict is None
        assert status_strict == "NO_ELIGIBLE_RECORDS"

    def test_04_test_d_exact_boundary_matching(self, sample_financial_df):
        """
        Test D: Inclusive boundary check: publication date on evaluation date.
        """
        df_verified = sample_financial_df[sample_financial_df["quarter"] == "2024-03-31"].copy()
        # publication_date is "2024-05-15 18:00:00"
        eval_date_same_day = "2024-05-15"

        # On the same date, evaluation date is parsed with end-of-day (23:59:59.999999),
        # so 18:00:00 on the same date is included!
        rec_same_day, status_same_day = _prepare_financial_data(
            df_verified,
            evaluation_date=eval_date_same_day,
            require_verified_publication_date=True,
        )
        assert rec_same_day is not None
        assert status_same_day == "VERIFIED_POINT_IN_TIME"

        # Set publication date to the next day
        df_boundary = df_verified.copy()
        df_boundary.loc[df_boundary.index[0], "publication_date"] = "2024-05-16 09:00:00"
        rec_next_day, status_next_day = _prepare_financial_data(
            df_boundary,
            evaluation_date="2024-05-15",
            require_verified_publication_date=True,
        )
        assert rec_next_day is None
        assert status_next_day == "NO_ELIGIBLE_RECORDS"

    def test_05_test_e_malformed_publication_date_rejected(self, sample_financial_df):
        """
        Test E: Malformed publication timestamp cannot silently become verified.
        In strict mode, it must be excluded.
        """
        df_malformed = sample_financial_df[sample_financial_df["quarter"] == "2024-03-31"].copy()
        df_malformed.loc[df_malformed.index[0], "publication_date"] = "INVALID_DATE_STRING"

        rec_strict, status_strict = _prepare_financial_data(
            df_malformed,
            evaluation_date="2024-06-01",
            require_verified_publication_date=True,
        )
        assert rec_strict is None
        assert status_strict == "NO_ELIGIBLE_RECORDS"

    def test_06_test_f_snapshot_service_forwards_strict_flag(self):
        """
        Test F: Snapshot path: get_stock_snapshot(..., require_verified_publication_date=True)
        forwards strict mode and handles unverified financials gracefully.
        """
        with patch("backend.data_pipeline.stock_snapshot_service.get_latest_price") as mock_price, \
             patch("backend.data_pipeline.stock_snapshot_service.get_company_classification") as mock_class, \
             patch("backend.data_pipeline.stock_snapshot_service.get_latest_financial_data") as mock_fin:

            mock_price.return_value = {
                "symbol": "INFY",
                "price": 1500.0,
                "change": 10.0,
                "percent_change": 0.67,
                "volume": 1000000,
                "timestamp": "2024-06-01 15:30:00",
            }
            mock_class.return_value = {
                "symbol": "INFY",
                "company_name": "Infosys Ltd",
                "sector": "Information Technology",
                "industry": "IT Services",
            }
            # Return None when strict verification is demanded
            mock_fin.return_value = None

            snapshot = get_stock_snapshot("INFY", require_verified_publication_date=True)

            mock_fin.assert_called_once_with(
                "INFY",
                evaluation_date=None,
                require_verified_publication_date=True,
            )
            assert snapshot["symbol"] == "INFY"
            assert snapshot["financial"] is None
            assert any("Latest financial data unavailable" in w for w in snapshot["data_quality"]["warnings"])
            assert snapshot["status"] == "PARTIAL"

    def test_07_test_g_backtest_dataset_builder_strict_mode(self):
        """
        Test G: Backtest dataset path: build_backtesting_dataset(..., require_verified_publication_date=True)
        populates None for financial metrics when publication dates are missing.
        """
        dummy_hist = {
            "symbol": "TCS",
            "data": pd.DataFrame([
                {
                    "symbol": "TCS",
                    "date": "2024-02-20",
                    "open": 3800.0,
                    "high": 3850.0,
                    "low": 3790.0,
                    "close": 3820.0,
                    "volume": 500000,
                    "adjusted_close": 3820.0,
                }
            ]),
        }

        dummy_financial = pd.DataFrame([
            {
                "id": 1,
                "symbol": "TCS",
                "company_id": 10,
                "quarter": "2023-12-31",
                "revenue": 50000.0,
                "net_profit": 10000.0,
                "operating_margin": 25.0,
                "pe_ratio": 30.0,
                "pb_ratio": 10.0,
                "debt_equity": 0.05,
                "roe": 35.0,
                "eps": 100.0,
                "roce": 40.0,
                "net_margin": 20.0,
                "publication_date": None,  # unverified
            }
        ])

        with patch("backend.data_pipeline.backtesting_dataset_service.get_historical_data") as mock_h, \
             patch("backend.data_pipeline.backtesting_dataset_service.get_financial_data") as mock_f:

            mock_h.return_value = dummy_hist
            mock_f.return_value = dummy_financial

            # 1. Strict mode: unverified publication_date rejected
            df_strict = build_backtesting_dataset(
                symbol="TCS",
                start_date="2024-02-20",
                end_date="2024-02-20",
                require_verified_publication_date=True,
            )
            assert not df_strict.empty
            row_strict = df_strict.iloc[0]
            assert row_strict["financial_data_status"] == "NO_ELIGIBLE_RECORDS"
            assert pd.isna(row_strict["reporting_period"]) or row_strict["reporting_period"] is None
            assert pd.isna(row_strict["revenue"]) or row_strict["revenue"] is None

            # 2. Legacy mode: fallback period_end + 45 days applies (2023-12-31 + 45d = 2024-02-14 <= 2024-02-20)
            df_legacy = build_backtesting_dataset(
                symbol="TCS",
                start_date="2024-02-20",
                end_date="2024-02-20",
                require_verified_publication_date=False,
            )
            assert not df_legacy.empty
            row_legacy = df_legacy.iloc[0]
            assert row_legacy["financial_data_status"] == "PERIOD_ELIGIBLE_FALLBACK_LAG"
            assert row_legacy["reporting_period"] == "2023-12-31"
            assert row_legacy["revenue"] == 50000.0

    def test_08_test_h_backtest_data_access_service_propagation(self):
        """
        Test H: Backtest data access service: get_backtest_inputs properly propagates flag.
        """
        with patch("backend.data_pipeline.backtest_data_access_service.build_backtesting_dataset") as mock_build:
            mock_build.return_value = pd.DataFrame([{"symbol": "INFY", "close": 1500.0}])

            get_backtest_input(
                symbol="INFY",
                evaluation_date="2024-01-15",
                require_verified_publication_date=True,
            )
            mock_build.assert_called_with(
                symbol="INFY",
                start_date="2024-01-15",
                end_date="2024-01-15",
                reporting_lag_days=45,
                filter_synthetic_holidays=False,
                quarantine_unresolved_anomalies=False,
                require_verified_publication_date=True,
            )

            get_backtest_inputs(
                symbol="INFY",
                start_date="2024-01-01",
                end_date="2024-01-15",
                require_verified_publication_date=True,
            )
            mock_build.assert_called_with(
                symbol="INFY",
                start_date="2024-01-01",
                end_date="2024-01-15",
                reporting_lag_days=45,
                filter_synthetic_holidays=False,
                quarantine_unresolved_anomalies=False,
                require_verified_publication_date=True,
            )

    def test_09_test_i_backward_compatibility_defaults(self):
        """
        Test I: Backward compatibility: callers omitting require_verified_publication_date
        default to False (legacy fallback behavior preserved).
        """
        with patch("backend.data_pipeline.backtest_data_access_service.build_backtesting_dataset") as mock_build:
            mock_build.return_value = pd.DataFrame([{"symbol": "INFY"}])

            get_backtest_input(symbol="INFY", evaluation_date="2024-01-15")
            assert mock_build.call_args.kwargs["require_verified_publication_date"] is False

            get_backtest_inputs(symbol="INFY", start_date="2024-01-01", end_date="2024-01-15")
            assert mock_build.call_args.kwargs["require_verified_publication_date"] is False

    def test_10_test_j_financial_service_direct_query_strict_filtering(self):
        """
        Test J: Direct calls to financial_service.get_financial_data and get_latest_financial_data
        respect require_verified_publication_date in an isolated SQLite database.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db_path = tf.name

        try:
            conn = sqlite3.connect(temp_db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE companies (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT UNIQUE,
                    company_name TEXT,
                    sector TEXT,
                    industry TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE quarterly_results (
                    id INTEGER PRIMARY KEY,
                    company_id INTEGER,
                    quarter TEXT,
                    revenue REAL,
                    net_profit REAL,
                    eps REAL,
                    roe REAL,
                    roce REAL,
                    debt_equity REAL,
                    operating_margin REAL,
                    net_margin REAL,
                    publication_date TEXT
                )
            """)
            cur.execute("INSERT INTO companies VALUES (1, 'RELIANCE', 'Reliance Industries', 'Energy', 'Oil & Gas')")
            # Quarter 1: unverified publication_date
            cur.execute("INSERT INTO quarterly_results VALUES (1, 1, '2023-09-30', 100.0, 10.0, 5.0, 10.0, 12.0, 0.5, 12.0, 8.0, NULL)")
            # Quarter 2: verified publication_date
            cur.execute("INSERT INTO quarterly_results VALUES (2, 1, '2023-12-31', 110.0, 12.0, 6.0, 11.0, 13.0, 0.48, 13.0, 9.0, '2024-01-20 10:00:00')")
            conn.commit()
            conn.close()

            with patch("backend.data_pipeline.financial_service.DATABASE_PATH", Path(temp_db_path)):
                # Call with as_of_date and strict mode
                res_strict = get_financial_data(
                    symbol="RELIANCE",
                    evaluation_date="2024-02-01",
                    require_verified_publication_date=True,
                )

                # In strict mode, only the record with publication_date <= 2024-02-01 should survive
                assert len(res_strict) == 1
                assert res_strict.iloc[0]["quarter"] == "2023-12-31"
                assert res_strict.attrs["data_eligibility_status"] == "VERIFIED_POINT_IN_TIME"

                # In legacy mode, both quarters should survive (2023-09-30 + 45d = 2023-11-14 <= 2024-02-01)
                res_legacy = get_financial_data(
                    symbol="RELIANCE",
                    evaluation_date="2024-02-01",
                    require_verified_publication_date=False,
                )
                assert len(res_legacy) == 2

                # Check get_latest_financial_data in strict mode
                latest_strict = get_latest_financial_data(
                    symbol="RELIANCE",
                    evaluation_date="2024-02-01",
                    require_verified_publication_date=True,
                )
                assert latest_strict is not None
                assert latest_strict["quarter"] == "2023-12-31"

                # Before publication date in strict mode
                latest_before = get_latest_financial_data(
                    symbol="RELIANCE",
                    evaluation_date="2024-01-10",
                    require_verified_publication_date=True,
                )
                assert latest_before is None
        finally:
            Path(temp_db_path).unlink(missing_ok=True)
