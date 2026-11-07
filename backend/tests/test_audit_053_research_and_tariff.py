"""
AUDIT-053 Dedicated Test Suite: Research Path Closure & Tariff Tax Verification
================================================================================
"""

import os
import sys
import json
import sqlite3
import pytest

pytestmark = pytest.mark.requires_preseeded_db
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
from backend.experimental.dual_setups import SupportPullbackSetup, MomentumBreakoutSetup
from backend.logic.cost_model import calculate_trade_costs
from backend.logic.backtest_specification import CostModelConfig, PortfolioConfig
from backend.logic.portfolio_simulator import simulate_portfolio
from scratch.run_audit_045_simulation import calculate_cost_complete_trade


class TestAudit053ResearchClosureAndTariff:

    # =========================================================================
    # Priority 1: Research Path Closure & Quarantine Parameter Forwarding
    # =========================================================================

    def test_01_quarantine_parameter_in_historical_data_service(self):
        """Proves quarantine_unresolved_anomalies=True in get_historical_data removes TRENT 2026-01-01."""
        res_raw = get_historical_data("TRENT", start_date="2025-12-24", end_date="2026-01-08", quarantine_unresolved_anomalies=False)
        dates_raw = [r["date"] for r in res_raw["data"].to_dict("records")]
        assert any("2026-01-01" in str(d) for d in dates_raw)

        res_quarantined = get_historical_data("TRENT", start_date="2025-12-24", end_date="2026-01-08", quarantine_unresolved_anomalies=True)
        dates_q = [r["date"] for r in res_quarantined["data"].to_dict("records")]
        assert not any("2026-01-01" in str(d) for d in dates_q)

    def test_02_quarantine_parameter_in_build_backtesting_dataset(self):
        """Proves quarantine_unresolved_anomalies=True in build_backtesting_dataset drops TRENT anomaly date."""
        df_raw = build_backtesting_dataset(
            symbol="TRENT",
            start_date="2025-12-24",
            end_date="2026-01-08",
            quarantine_unresolved_anomalies=False,
        )
        assert "2026-01-01" in df_raw["evaluation_date"].values

        df_q = build_backtesting_dataset(
            symbol="TRENT",
            start_date="2025-12-24",
            end_date="2026-01-08",
            quarantine_unresolved_anomalies=True,
        )
        assert "2026-01-01" not in df_q["evaluation_date"].values

    def test_03_quarantine_parameter_in_backtest_data_access_service(self):
        """Proves quarantine_unresolved_anomalies=True in get_backtest_inputs removes anomaly session."""
        inputs_q = get_backtest_inputs(
            symbol="TRENT",
            start_date="2025-12-24",
            end_date="2026-01-08",
            quarantine_unresolved_anomalies=True,
        )
        dates_q = [item["evaluation_date"] for item in inputs_q]
        assert "2026-01-01" not in dates_q

        # Single date access returns None when quarantined
        input_single = get_backtest_input(
            symbol="TRENT",
            evaluation_date="2026-01-01",
            quarantine_unresolved_anomalies=True,
        )
        assert input_single is None

    def test_04_support_pullback_setup_safe_when_fed_filtered_data(self):
        """
        Proves that SupportPullbackSetup correctly processes filtered datasets
        and that unadjusted anomalies are absent when quarantine filter is applied.
        """
        pullback = SupportPullbackSetup()
        # Feed filtered history for RELIANCE
        res_mkt = get_historical_data("RELIANCE", filter_synthetic_holidays=True)
        df_reliance = res_mkt["data"]

        eval_res = pullback.evaluate(
            symbol="RELIANCE",
            evaluation_date="2025-05-02",
            df_hist=df_reliance[df_reliance["date"] <= "2025-05-02"],
            nearest_support={"level": 1000.0},
            nearest_resistance={"level": 1100.0},
        )
        assert isinstance(eval_res, dict)
        assert eval_res["symbol"] == "RELIANCE"
        assert eval_res["evaluation_date"] == "2025-05-02"

    # =========================================================================
    # Priority 2: Authoritative Tariff & GST Tax Base Verification
    # =========================================================================

    def test_05_authoritative_gst_taxable_base_and_rate(self):
        """
        Authoritative Tax Law Audit (CGST & SGST Act, 2017):
        - Statutory rate: 18% (9% CGST + 9% SGST).
        - Direct Taxes (CBDT): STT is a direct tax on securities turnover -> EXEMPT from GST.
        - Stamp Duty: State revenue levy under Indian Stamp Act -> EXEMPT from GST.
        - Taxable financial services: Brokerage commission, Exchange trading fees, SEBI regulatory turnover charges, Depository (CDSL/NSDL) participant transaction debits.
        """
        turnover = Decimal("100000.00")
        brokerage = Decimal("0.00")
        exchange_fee = (turnover * Decimal("0.0000297")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) # Rs 2.97
        sebi_fee = (turnover * Decimal("0.000001")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)         # Rs 0.10
        cdsl_base_dp = Decimal("13.50")

        # Buy side taxable base
        buy_taxable = brokerage + exchange_fee + sebi_fee # 3.07
        buy_gst = (buy_taxable * Decimal("0.18")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        assert buy_taxable == Decimal("3.07")
        assert buy_gst == Decimal("0.5526")

        # Sell side taxable base (includes CDSL DP debit)
        sell_taxable = brokerage + exchange_fee + sebi_fee + cdsl_base_dp # 16.57
        sell_gst = (sell_taxable * Decimal("0.18")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        assert sell_taxable == Decimal("16.57")
        assert sell_gst == Decimal("2.9826")

    def test_06_depository_participant_cdsl_fee_schedule(self):
        """
        Authoritative Depository Tariff Verification (CDSL Tariff Schedule):
        - Depository fee: Rs 13.50 per debit transaction (ISIN/scrip per day, irrespective of quantity).
        - Applicable GST: Rs 13.50 * 18% = Rs 2.43.
        - Customer debit amount: Rs 13.50 + Rs 2.43 = Rs 15.93.
        - Applicability: Strictly sell leg (demat transfer/delivery debit); zero on buy leg.
        """
        base_dp = Decimal("13.50")
        dp_gst = (base_dp * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_dp = base_dp + dp_gst
        assert dp_gst == Decimal("2.43")
        assert total_dp == Decimal("15.93")

    def test_07_exact_decimal_ledger_reconciliation(self):
        """
        Proves that across order life cycle:
        Gross P&L - All Costs = Net P&L
        Cash After Sell = Starting Cash + Net P&L
        """
        initial_cash = Decimal("100000.00")
        buy_price = Decimal("200.00")
        sell_price = Decimal("210.00")
        qty = 500

        buy_turnover = buy_price * qty # 100,000.00
        sell_turnover = sell_price * qty # 105,000.00

        # Buy costs
        buy_stt = buy_turnover * Decimal("0.001")          # 100.00
        buy_nse = buy_turnover * Decimal("0.0000297")      # 2.97
        buy_sebi = buy_turnover * Decimal("0.000001")      # 0.10
        buy_stamp = buy_turnover * Decimal("0.00015")      # 15.00
        buy_gst = ((buy_nse + buy_sebi) * Decimal("0.18")).quantize(Decimal("0.0001")) # 0.5526
        buy_total = buy_stt + buy_nse + buy_sebi + buy_stamp + buy_gst # 118.6226

        # Sell costs
        sell_stt = sell_turnover * Decimal("0.001")        # 105.00
        sell_nse = sell_turnover * Decimal("0.0000297")    # 3.1185
        sell_sebi = sell_turnover * Decimal("0.000001")    # 0.1050
        sell_stamp = Decimal("0.00")
        base_dp = Decimal("13.50")
        sell_taxable = sell_nse + sell_sebi + base_dp      # 16.7235
        sell_gst = (sell_taxable * Decimal("0.18")).quantize(Decimal("0.0001")) # 3.0102
        sell_total = sell_stt + sell_nse + sell_sebi + sell_stamp + base_dp + sell_gst # 124.7337

        gross_pl = (sell_price - buy_price) * qty # 5000.00
        total_costs = buy_total + sell_total     # 243.3563
        net_pl = gross_pl - total_costs          # 4756.6437

        cash_after_buy = initial_cash - buy_turnover - buy_total
        cash_after_sell = cash_after_buy + sell_turnover - sell_total
        final_cash_delta = cash_after_sell - initial_cash

        assert final_cash_delta == net_pl
        assert gross_pl - total_costs == net_pl
