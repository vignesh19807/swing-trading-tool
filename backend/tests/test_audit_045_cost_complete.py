"""
AUDIT-045 Regression Test Suite: Cost-Complete Model, Robustness Diagnostics, and Safety
=======================================================================================
"""

import os
import sys
import json
import sqlite3
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import pytest

pytestmark = pytest.mark.requires_preseeded_db

from scratch.run_audit_045_simulation import calculate_cost_complete_trade, simulate_pullback_with_exact_costs


class TestAudit045CostCompleteRobustness:

    def test_01_production_database_sha256_unmodified(self):
        """Production database must remain 100% byte-for-byte untouched."""
        import hashlib
        db_path = os.path.join(PROJECT_ROOT, "database", "swing_trading.db")
        expected_hash = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"
        hasher = hashlib.sha256()
        with open(db_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        assert hasher.hexdigest().upper() == expected_hash

    def test_02_dp_charges_applied_only_on_sell(self):
        """DP charges (Rs 13.50 + 18% GST = Rs 15.93) must apply only on sell, not buy."""
        # Buy leg
        buy_costs = calculate_cost_complete_trade(price=1000.0, quantity=10, is_buy=True, include_dp=True)
        assert buy_costs["dp_charges"] == 0.0

        # Sell leg
        sell_costs = calculate_cost_complete_trade(price=1000.0, quantity=10, is_buy=False, include_dp=True)
        assert sell_costs["dp_charges"] == 13.50
        # Check GST: 18% on (Brokerage(0) + Exch + SEBI + DP(13.50))
        expected_gst = round((sell_costs["exchange_charges"] + sell_costs["sebi_charges"] + 13.50) * 0.18, 4)
        assert abs(sell_costs["gst"] - expected_gst) < 1e-4

    def test_03_cost_complete_accounting_reconciliation(self):
        """Verify mathematical ledger reconciliation in cost-complete results."""
        results_file = os.path.join(PROJECT_ROOT, "docs", "audit_artifacts", "audit_045_cost_complete_results.json")
        assert os.path.exists(results_file)
        with open(results_file, "r") as f:
            d = json.load(f)

        s10 = d["sim_cost_complete_10bps"]
        trades = d["trades_cost_complete_10bps"]
        sum_gross = sum(t["gross_pl"] for t in trades)
        sum_costs = sum(t["total_costs"] for t in trades)
        sum_net = sum(t["net_pl"] for t in trades)

        assert abs(sum_gross - s10["total_gross_pl"]) < 1e-3
        assert abs(sum_costs - s10["total_costs"]) < 1e-3
        assert abs(sum_net - s10["total_net_pl"]) < 1e-3
        assert round(s10["total_net_pl"], 2) == -253.86
        assert round(s10["final_cash"], 2) == 99746.14

    def test_04_shriramfin_concentration_ratio(self):
        """Verify that SHRIRAMFIN accounts for >100% of net profits in 10 bps model."""
        results_file = os.path.join(PROJECT_ROOT, "docs", "audit_artifacts", "audit_045_cost_complete_results.json")
        with open(results_file, "r") as f:
            d = json.load(f)

        trades = d["trades_cost_complete_10bps"]
        shriram_net = sum(t["net_pl"] for t in trades if t["symbol"] == "SHRIRAMFIN")
        other_net = sum(t["net_pl"] for t in trades if t["symbol"] != "SHRIRAMFIN")
        total_net = sum(t["net_pl"] for t in trades)

        assert shriram_net > 3000.0  # +Rs 3,424.22
        assert other_net < -3000.0   # -Rs 3,678.08
        assert total_net < 0.0       # -Rs 253.86

    def test_05_slippage_degradation_profile(self):
        """Verify performance degrades monotonically with slippage: 0 bps > 10 bps > 20 bps."""
        results_file = os.path.join(PROJECT_ROOT, "docs", "audit_artifacts", "audit_045_cost_complete_results.json")
        with open(results_file, "r") as f:
            d = json.load(f)

        pnl_0 = d["sim_cost_complete_0bps"]["total_net_pl"]
        pnl_10 = d["sim_cost_complete_10bps"]["total_net_pl"]
        pnl_20 = d["sim_cost_complete_20bps"]["total_net_pl"]

        assert pnl_0 > pnl_10 > pnl_20
        assert pnl_0 > 0.0     # +Rs 716.56
        assert pnl_10 < 0.0    # -Rs 253.86
        assert pnl_20 < -1000.0 # -Rs 1,138.47

