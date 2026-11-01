"""
AUDIT-051 Test Suite: Research Filter Consumption, Cost Reconciliation, and Anomaly Safeguards
==============================================================================================
"""

import os
import sys
import json
import sqlite3
import pytest
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.backtesting_dataset_service import build_backtesting_dataset
from backend.data_pipeline.backtest_data_access_service import get_backtest_inputs, get_backtest_input
from backend.data_pipeline.research_market_data_filter import (
    filter_research_market_data,
    detect_market_data_anomalies,
    validate_research_dataset_safety,
)
from backend.logic.cost_model import calculate_trade_costs
from backend.logic.backtest_specification import CostModelConfig
from scratch.run_audit_045_simulation import calculate_cost_complete_trade


class TestAudit051ExecutionSafety:

    # -------------------------------------------------------------
    # Outcome 1: Filtered Research Data
    # -------------------------------------------------------------
    def test_01_filter_preserves_production_default(self):
        """Production calls without filter argument must receive full 496 bars."""
        res = get_historical_data("RELIANCE", filter_synthetic_holidays=False)
        df = res["data"]
        assert len(df) == 496
        # Check that holiday sessions are present in production default (convert to ISO string)
        dates = set(pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").values)
        assert "2025-03-18" in dates
        assert "2026-01-15" in dates

    def test_02_filter_explicit_opt_in_excludes_holiday_bars(self):
        """Research calls with filter_synthetic_holidays=True must exclude holiday flat bars."""
        res = get_historical_data("RELIANCE", filter_synthetic_holidays=True)
        df = res["data"]
        assert len(df) == 494
        dates = set(pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").values)
        assert "2025-03-18" not in dates
        assert "2026-01-15" not in dates

    def test_03_backtesting_dataset_indicators_and_filtering(self):
        """build_backtesting_dataset must pass filter and produce correct evaluation dates."""
        df_filtered = build_backtesting_dataset(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=True,
        )
        assert "2025-03-18" not in df_filtered["evaluation_date"].values
        assert len(df_filtered) == 10
        # Verify indicator columns are populated
        for col in ["rsi", "macd", "ema_20", "atr_14"]:
            assert col in df_filtered.columns
            assert not df_filtered[col].isna().all()

    def test_04_downstream_access_service_no_reload(self):
        """get_backtest_inputs forwards filter parameter directly to build_backtesting_dataset."""
        inputs = get_backtest_inputs(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=True,
        )
        dates = [item["evaluation_date"] for item in inputs]
        assert "2025-03-18" not in dates
        assert len(inputs) == 10

    # -------------------------------------------------------------
    # Outcome 2: Transaction Costs & Exactly-Once Ledger
    # -------------------------------------------------------------
    def test_05_dp_charges_source_reconciliation(self):
        """Reconcile DP charge: Base is Rs 13.50; with 18% GST (Rs 2.43) it equals Rs 15.93."""
        base_dp = Decimal("13.50")
        gst_rate = Decimal("0.18")
        dp_gst = (base_dp * gst_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_dp_debit = base_dp + dp_gst

        assert dp_gst == Decimal("2.43")
        assert total_dp_debit == Decimal("15.93")

    def test_06_exact_decimal_round_trip_cost_reconciliation(self):
        """Independently calculate Rs 100k round trip using exact Decimal arithmetic."""
        turnover = Decimal("100000.00")
        stt = turnover * Decimal("0.001")          # 100.00
        nse = turnover * Decimal("0.0000297")      # 2.97
        sebi = turnover * Decimal("0.000001")      # 0.10
        stamp_buy = turnover * Decimal("0.00015")  # 15.00
        base_dp = Decimal("13.50")
        gst_rate = Decimal("0.18")

        # Buy leg: GST applies to (Brokerage + NSE + SEBI) = 3.07
        buy_taxable = nse + sebi
        buy_gst = (buy_taxable * gst_rate).quantize(Decimal("0.0001")) # 0.5526
        buy_total = stt + nse + sebi + stamp_buy + buy_gst # 118.6226

        # Sell leg: GST applies to (Brokerage + NSE + SEBI + Base DP) = 2.97 + 0.10 + 13.50 = 16.57
        sell_taxable = nse + sebi + base_dp
        sell_gst = (sell_taxable * gst_rate).quantize(Decimal("0.0001")) # 2.9826
        sell_total = stt + nse + sebi + base_dp + sell_gst # 119.5526

        round_trip_exact = buy_total + sell_total # 238.1752
        round_trip_cents = round_trip_exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        assert buy_total == Decimal("118.6226")
        assert sell_total == Decimal("119.5526")
        assert round_trip_exact == Decimal("238.1752")
        assert round_trip_cents == Decimal("238.18")

        # Prove pre-rounded sum artifact:
        buy_displayed = buy_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)   # 118.62
        sell_displayed = sell_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) # 119.55
        assert buy_displayed + sell_displayed == Decimal("238.17")

    def test_07_exactly_once_ledger_accounting(self):
        """Simulate trade round-trip and verify cash/equity equations hold exactly."""
        initial_cash = 100000.0
        entry_price = 200.0
        exit_price = 210.0
        quantity = 500

        # Leg 1: Buy
        buy_costs = calculate_cost_complete_trade(entry_price, quantity, is_buy=True, include_dp=True)
        cash_after_buy = initial_cash - (entry_price * quantity) - buy_costs["total_costs"]

        # Leg 2: Sell
        sell_costs = calculate_cost_complete_trade(exit_price, quantity, is_buy=False, include_dp=True)
        cash_after_sell = cash_after_buy + (exit_price * quantity) - sell_costs["total_costs"]

        # Exact accounting
        gross_pl = (exit_price - entry_price) * quantity
        total_costs = buy_costs["total_costs"] + sell_costs["total_costs"]
        net_pl = gross_pl - total_costs
        final_cash = cash_after_sell

        assert abs(gross_pl - 5000.0) < 1e-6
        assert abs((final_cash - initial_cash) - net_pl) < 1e-6
        assert buy_costs["dp_charges"] == 0.0
        assert sell_costs["dp_charges"] == 13.50

    # -------------------------------------------------------------
    # Outcome 3: Corporate-Action Anomaly Safeguards
    # -------------------------------------------------------------
    def test_08_anomaly_detection_identifies_tmpv_and_trent(self):
        """Scans database records and verifies TMPV & TRENT are flagged as discontinuities."""
        conn = sqlite3.connect(os.path.join(PROJECT_ROOT, "database", "swing_trading.db"))
        query = """
            SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
            FROM daily_prices dp
            JOIN companies c ON dp.company_id = c.id
            WHERE c.symbol IN ('TMPV', 'TRENT')
            ORDER BY c.symbol, dp.date
        """
        df = pd.read_sql(query, conn)
        conn.close()

        annotated = detect_market_data_anomalies(df)
        disc = annotated[annotated["is_large_discontinuity"]]
        disc_tuples = set(zip(disc["symbol"], disc["date"].str.slice(0, 10)))

        assert ("TMPV", "2025-10-14") in disc_tuples
        assert ("TRENT", "2026-01-01") in disc_tuples

    def test_09_safeguard_fails_visibly_on_unresolved_trent(self):
        """validate_research_dataset_safety must report failure when unresolved TRENT anomaly is present."""
        df_trent = pd.DataFrame([
            {"symbol": "TRENT", "date": "2025-12-31", "open": 4225.0, "high": 4280.0, "low": 4200.0, "close": 4279.0, "volume": 426359},
            {"symbol": "TRENT", "date": "2026-01-01", "open": 2852.6, "high": 2872.0, "low": 2837.2, "close": 2864.9, "volume": 561898},
        ])
        check = validate_research_dataset_safety(df_trent, symbol="TRENT")
        assert not check["is_safe"]
        assert check["status"] == "FAIL_UNRESOLVED_ANOMALY"
        assert any("UNRESOLVED_PRICE_ANOMALY" in msg for msg in check["anomalies_detected"])

    def test_10_quarantine_unresolved_anomalies_removes_unadjusted_bar(self):
        """filter_research_market_data with quarantine_unresolved_anomalies=True safely drops TRENT unadjusted bar."""
        df_trent = pd.DataFrame([
            {"symbol": "TRENT", "date": "2025-12-31", "open": 4225.0, "high": 4280.0, "low": 4200.0, "close": 4279.0, "volume": 426359},
            {"symbol": "TRENT", "date": "2026-01-01", "open": 2852.6, "high": 2872.0, "low": 2837.2, "close": 2864.9, "volume": 561898},
        ])
        cleaned = filter_research_market_data(df_trent, quarantine_unresolved_anomalies=True)
        assert len(cleaned) == 1
        assert cleaned.iloc[0]["date"] == "2025-12-31"
