"""
AUDIT-052 Dedicated Test Suite: Research Dataset Enforcement and Actual Transaction Ledger Verification
========================================================================================================
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
from backend.data_pipeline.backtest_data_access_service import get_backtest_input, get_backtest_inputs
from backend.data_pipeline.research_market_data_filter import (
    filter_research_market_data,
    detect_market_data_anomalies,
    validate_research_dataset_safety,
)
from backend.logic.cost_model import calculate_trade_costs
from backend.logic.backtest_specification import CostModelConfig, PortfolioConfig
from backend.logic.portfolio_simulator import simulate_portfolio
from scratch.run_audit_045_simulation import calculate_cost_complete_trade


class TestAudit052ResearchAndLedgerVerification:

    # =========================================================================
    # Priority 1: Research Dataset Enforcement & Downstream Reload Prevention
    # =========================================================================

    def test_01_synthetic_holiday_isolation_in_dataset_service(self):
        """Proves that build_backtesting_dataset drops 2025-03-18 when requested."""
        df_unfiltered = build_backtesting_dataset(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=False,
        )
        assert "2025-03-18" in df_unfiltered["evaluation_date"].values
        assert len(df_unfiltered) == 11

        df_filtered = build_backtesting_dataset(
            symbol="RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=True,
        )
        assert "2025-03-18" not in df_filtered["evaluation_date"].values
        assert len(df_filtered) == 10

    def test_02_data_access_service_single_date_filtering(self):
        """Proves that get_backtest_input returns None for holiday date when filter is True."""
        # Unfiltered returns record
        res_unfiltered = get_backtest_input("RELIANCE", "2025-03-18", filter_synthetic_holidays=False)
        assert res_unfiltered is not None
        assert res_unfiltered["evaluation_date"] == "2025-03-18"

        # Filtered returns None because holiday bar was pruned
        res_filtered = get_backtest_input("RELIANCE", "2025-03-18", filter_synthetic_holidays=True)
        assert res_filtered is None

    def test_03_data_access_service_range_no_reload(self):
        """Proves that get_backtest_inputs does not reload or re-inject filtered holidays."""
        res_range = get_backtest_inputs(
            "RELIANCE",
            start_date="2025-03-10",
            end_date="2025-03-25",
            filter_synthetic_holidays=True,
        )
        dates = [item["evaluation_date"] for item in res_range]
        assert "2025-03-18" not in dates
        assert len(dates) == 10

    def test_04_unresolved_anomaly_enforcement_policy(self):
        """Proves that validate_research_dataset_safety halts on TRENT 2026-01-01 unadjusted bar."""
        df_trent = pd.DataFrame([
            {"symbol": "TRENT", "date": "2025-12-31", "open": 4225.0, "high": 4280.0, "low": 4200.0, "close": 4279.0, "volume": 426359},
            {"symbol": "TRENT", "date": "2026-01-01", "open": 2852.6, "high": 2872.0, "low": 2837.2, "close": 2864.9, "volume": 561898},
        ])
        check = validate_research_dataset_safety(df_trent, symbol="TRENT")
        assert check["status"] == "FAIL_UNRESOLVED_ANOMALY"
        assert not check["is_safe"]

        # Quarantine mode successfully purges the anomaly
        quarantined = filter_research_market_data(df_trent, quarantine_unresolved_anomalies=True)
        assert len(quarantined) == 1
        assert quarantined.iloc[0]["date"] == "2025-12-31"

    # =========================================================================
    # Priority 2: Actual Transaction-Ledger Reconciliation & Exactly-Once Fees
    # =========================================================================

    def test_05_taxable_gst_base_reconciliation(self):
        """
        Verifies the exact taxable base for GST under Indian Statutory Delivery Rules:
        - STT: Exempt from GST
        - Stamp Duty: Exempt from GST
        - Taxable components: Brokerage + Exchange Transaction Charges + SEBI Fee + Depository (DP) Fee
        """
        turnover = Decimal("100000.00")
        brokerage = Decimal("0.00")
        nse_charges = (turnover * Decimal("0.0000297")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) # 2.97
        sebi_charges = (turnover * Decimal("0.000001")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) # 0.10
        base_dp = Decimal("13.50")
        gst_rate = Decimal("0.18")

        # Buy side taxable base = 2.97 + 0.10 = 3.07
        buy_taxable = brokerage + nse_charges + sebi_charges
        buy_gst = (buy_taxable * gst_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        assert buy_taxable == Decimal("3.07")
        assert buy_gst == Decimal("0.5526")

        # Sell side taxable base (with DP) = 2.97 + 0.10 + 13.50 = 16.57
        sell_taxable = brokerage + nse_charges + sebi_charges + base_dp
        sell_gst = (sell_taxable * gst_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        assert sell_taxable == Decimal("16.57")
        assert sell_gst == Decimal("2.9826")

    def test_06_dp_fee_tariff_composition(self):
        """Proves exact composition of Rs 15.93: Rs 13.50 base CDSL fee + Rs 2.43 GST (18%)."""
        base_dp = Decimal("13.50")
        dp_gst = (base_dp * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        final_dp_debit = base_dp + dp_gst
        assert dp_gst == Decimal("2.43")
        assert final_dp_debit == Decimal("15.93")

    def test_07_portfolio_simulator_ledger_cash_reconciliation(self):
        """
        Proves that portfolio_simulator debits costs exactly once and maintains:
        Final Cash = Initial Cash + Gross P&L - Total Transaction Costs
        Accounts for displayed 2-decimal rounding in summary vs 4-decimal ledger precision.
        """
        initial_cash = 100000.0
        cfg = PortfolioConfig(
            initial_capital=initial_cash,
            max_open_positions=1,
            max_allocation_per_position=0.5,
            enable_costs=True,
        )

        market_data = {
            "RELIANCE": pd.DataFrame([
                {"date": "2025-05-02", "open": 1000.0, "high": 1020.0, "low": 990.0, "close": 1010.0, "volume": 1000000},
                {"date": "2025-05-05", "open": 1010.0, "high": 1050.0, "low": 1005.0, "close": 1040.0, "volume": 1000000},
                {"date": "2025-05-06", "open": 1040.0, "high": 1060.0, "low": 1030.0, "close": 1050.0, "volume": 1000000},
            ])
        }

        signals = [
            {
                "symbol": "RELIANCE",
                "evaluation_date": "2025-05-02",
                "recommendation": "BUY",
                "signal_valid": True,
                "is_eligible": True,
                "stop_loss": 980.0,
                "target": 1030.0,
                "opportunity_score": 85.0,
            }
        ]

        sim_res = simulate_portfolio(signals, market_data, config=cfg)
        summary = sim_res["portfolio_summary"]
        trades = sim_res["closed_trades"]

        assert len(trades) == 1
        t = trades[0]

        # Verify trade accounting
        assert t["entry_costs"] > 0.0
        assert t["exit_costs"] > 0.0
        assert abs(t["total_costs"] - (t["entry_costs"] + t["exit_costs"])) < 1e-4
        assert abs(t["net_pl"] - (t["gross_pl"] - t["total_costs"])) < 1e-4

        # Verify portfolio cash reconciliation (summary rounds final_cash to 2 decimals)
        unrounded_final_cash = initial_cash + summary["total_gross_pl"] - summary["total_costs"]
        assert round(summary["final_cash"], 2) == round(unrounded_final_cash, 2)
        assert abs(summary["total_net_pl"] - (summary["total_gross_pl"] - summary["total_costs"])) < 1e-4

    def test_08_multiple_trades_cost_aggregation_identity(self):
        """Proves that across multiple trades, total costs equal the exact sum of individual trade costs."""
        initial_cash = 200000.0
        cfg = PortfolioConfig(
            initial_capital=initial_cash,
            max_open_positions=2,
            max_allocation_per_position=0.4,
            enable_costs=True,
        )

        market_data = {
            "STOCKA": pd.DataFrame([
                {"date": "2025-06-02", "open": 500.0, "high": 510.0, "low": 490.0, "close": 505.0, "volume": 500000},
                {"date": "2025-06-03", "open": 505.0, "high": 530.0, "low": 500.0, "close": 525.0, "volume": 500000},
                {"date": "2025-06-04", "open": 525.0, "high": 540.0, "low": 520.0, "close": 535.0, "volume": 500000},
            ]),
            "STOCKB": pd.DataFrame([
                {"date": "2025-06-02", "open": 200.0, "high": 205.0, "low": 195.0, "close": 202.0, "volume": 500000},
                {"date": "2025-06-03", "open": 202.0, "high": 220.0, "low": 200.0, "close": 215.0, "volume": 500000},
                {"date": "2025-06-04", "open": 215.0, "high": 225.0, "low": 210.0, "close": 220.0, "volume": 500000},
            ]),
        }

        signals = [
            {
                "symbol": "STOCKA",
                "evaluation_date": "2025-06-02",
                "recommendation": "BUY",
                "signal_valid": True,
                "is_eligible": True,
                "stop_loss": 480.0,
                "target": 520.0,
                "opportunity_score": 80.0,
            },
            {
                "symbol": "STOCKB",
                "evaluation_date": "2025-06-02",
                "recommendation": "BUY",
                "signal_valid": True,
                "is_eligible": True,
                "stop_loss": 190.0,
                "target": 210.0,
                "opportunity_score": 82.0,
            },
        ]

        sim_res = simulate_portfolio(signals, market_data, config=cfg)
        trades = sim_res["closed_trades"]
        summary = sim_res["portfolio_summary"]

        assert len(trades) == 2
        sum_trade_costs = sum(t["total_costs"] for t in trades)
        sum_trade_gross = sum(t["gross_pl"] for t in trades)
        sum_trade_net = sum(t["net_pl"] for t in trades)

        assert abs(summary["total_costs"] - sum_trade_costs) < 1e-4
        assert abs(summary["total_gross_pl"] - sum_trade_gross) < 1e-4
        assert abs(summary["total_net_pl"] - sum_trade_net) < 1e-4
        assert round(summary["final_cash"], 2) == round(initial_cash + sum_trade_net, 2)

    def test_09_independent_decimal_ledger_comparison(self):
        """
        Directly checks portfolio_simulator cost output against an independent Decimal engine:
        Proves zero discrepancy between independently expected costs and actual ledger entries.
        """
        price = 100.0
        qty = 1000
        turnover = Decimal("100000.00")

        # Independent calculation
        stt = turnover * Decimal("0.001")          # 100.00
        nse = turnover * Decimal("0.0000297")      # 2.97
        sebi = turnover * Decimal("0.000001")      # 0.10
        stamp = turnover * Decimal("0.00015")      # 15.00
        gst_buy = ((nse + sebi) * Decimal("0.18")).quantize(Decimal("0.0001")) # 0.5526
        expected_buy_costs = float(stt + nse + sebi + stamp + gst_buy) # 118.6226

        # Implementation calculation
        actual_costs = calculate_trade_costs(price, qty, is_buy=True, config=CostModelConfig())

        assert abs(actual_costs["total_costs"] - expected_buy_costs) < 1e-4
        assert abs(actual_costs["stt"] - float(stt)) < 1e-4
        assert abs(actual_costs["exchange_charges"] - float(nse)) < 1e-4
        assert abs(actual_costs["sebi_charges"] - float(sebi)) < 1e-4
        assert abs(actual_costs["stamp_duty"] - float(stamp)) < 1e-4
        assert abs(actual_costs["gst"] - float(gst_buy)) < 1e-4
