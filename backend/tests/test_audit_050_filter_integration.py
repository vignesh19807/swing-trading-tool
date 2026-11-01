import pytest
import pandas as pd
from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.backtesting_dataset_service import build_backtesting_dataset
from backend.data_pipeline.backtest_data_access_service import get_backtest_inputs

class TestResearchFilterIntegration:

    def test_01_historical_data_service_filtering(self):
        # Default False: returns 496 bars
        res_unfiltered = get_historical_data("RELIANCE", filter_synthetic_holidays=False)
        df_unfiltered = pd.DataFrame(res_unfiltered["data"])
        assert len(df_unfiltered) == 496

        # Filtered True: returns 494 bars (excluding 2025-03-18 and 2026-01-15)
        res_filtered = get_historical_data("RELIANCE", filter_synthetic_holidays=True)
        df_filtered = pd.DataFrame(res_filtered["data"])
        assert len(df_filtered) == 494
        assert "2025-03-18" not in df_filtered["date"].values
        assert "2026-01-15" not in df_filtered["date"].values

    def test_02_build_backtesting_dataset_filtering(self):
        # Default False: includes 2025-03-18
        df_unfiltered = build_backtesting_dataset(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=False
        )
        assert "2025-03-18" in df_unfiltered["evaluation_date"].values
        assert len(df_unfiltered) == 11

        # Filtered True: excludes 2025-03-18
        df_filtered = build_backtesting_dataset(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=True
        )
        assert "2025-03-18" not in df_filtered["evaluation_date"].values
        assert len(df_filtered) == 10

    def test_03_backtest_data_access_service_filtering(self):
        # Filtered True via get_backtest_inputs
        inputs_filtered = get_backtest_inputs(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=True
        )
        eval_dates = [item["evaluation_date"] for item in inputs_filtered]
        assert "2025-03-18" not in eval_dates
        assert len(eval_dates) == 10

        # Unfiltered False via get_backtest_inputs
        inputs_unfiltered = get_backtest_inputs(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=False
        )
        eval_dates_unfiltered = [item["evaluation_date"] for item in inputs_unfiltered]
        assert "2025-03-18" in eval_dates_unfiltered
        assert len(eval_dates_unfiltered) == 11
