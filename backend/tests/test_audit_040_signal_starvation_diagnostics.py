"""
AUDIT-040: Focused Diagnostic and Regression Tests
==================================================
Tests the exact signal starvation and entry filter conditions identified in AUDIT-040:
1. Financial health cold-start behavior (subscores < 2 vs >= 2).
2. Entry zone calculation and bounds checking (Pullback-to-Support).
3. Risk/Reward ratio evaluation and rejection threshold (RR < 1.50).
4. Exit target structural validity (Target vs Current and Entry prices).
5. Portfolio concurrency rejection (ALREADY_IN_POSITION).
6. Production database immutability verification.
"""

import pytest
import sqlite3
import hashlib
import os
from unittest.mock import patch

from backend.logic.signal_engine import (
    calculate_entry_zone,
    calculate_exit_parameters,
    generate_final_signal,
    MIN_RISK_REWARD_RATIO
)
from backend.engines.financial_engine import analyze_financial_health
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig, RejectionReason
import pandas as pd


EXPECTED_DB_SHA256 = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"
DB_PATH = os.path.abspath("database/swing_trading.db")


class TestAudit040SignalStarvationDiagnostics:

    def test_01_entry_zone_rejects_price_above_upper_bound(self):
        """Current price > support + 0.5*ATR must be rejected with PRICE_OUTSIDE_ENTRY_ZONE."""
        support = {"level": 100.0, "strength": 1.0}
        atr = 4.0
        # Entry zone is [100.0, 102.0]
        current_price = 103.5 # Exceeds 102.0 by 1.5
        res = calculate_entry_zone(current_price, support, atr, recommendation="BUY")
        assert res["entry_valid"] is False
        assert res["reason"] == "PRICE_OUTSIDE_ENTRY_ZONE"
        assert res["entry_lower"] == 100.0
        assert res["entry_upper"] == 102.0

    def test_02_entry_zone_accepts_price_within_pullback_bounds(self):
        """Current price between support and support + 0.5*ATR must be accepted."""
        support = {"level": 100.0, "strength": 1.0}
        atr = 4.0
        current_price = 101.5 # Within [100.0, 102.0]
        res = calculate_entry_zone(current_price, support, atr, recommendation="BUY")
        assert res["entry_valid"] is True
        assert res["reason"] == "VALID_PULLBACK_ENTRY"

    def test_03_entry_zone_rejects_price_below_support(self):
        """Current price below support must be rejected with PRICE_OUTSIDE_ENTRY_ZONE."""
        support = {"level": 100.0, "strength": 1.0}
        atr = 4.0
        current_price = 98.0
        res = calculate_entry_zone(current_price, support, atr, recommendation="BUY")
        assert res["entry_valid"] is False
        assert res["reason"] == "PRICE_OUTSIDE_ENTRY_ZONE"

    def test_04_insufficient_risk_reward_rejected(self):
        """Reward to risk < 1.50 must be rejected with INSUFFICIENT_RISK_REWARD_RATIO."""
        support = {"level": 100.0, "zone_low": 100.0}
        resistance = {"level": 103.0, "zone_low": 103.0} # Resistance close
        atr = 2.0
        current_price = 100.5
        # SL = 100 - 1.5*2 = 97.0 -> Risk = 100.5 - 97.0 = 3.5
        # Target = 103.0 -> Reward = 103.0 - 100.5 = 2.5
        # RR = 2.5 / 3.5 = 0.714 < 1.50
        res = generate_final_signal(current_price, support, resistance, atr, recommendation="BUY")
        assert res["signal_valid"] is False
        assert res["reason"] == "INSUFFICIENT_RISK_REWARD_RATIO"
        assert res["risk_reward_ratio"] < MIN_RISK_REWARD_RATIO

    def test_05_target_below_entry_price_rejected(self):
        """Target <= entry_price must be rejected with TARGET_BELOW_ENTRY_PRICE."""
        support = {"level": 100.0, "zone_low": 100.0}
        # Resistance zone low at 101.5, while entry_upper is 100 + 0.5*4 = 102.0
        resistance = {"level": 103.0, "zone_low": 101.5}
        atr = 4.0
        current_price = 100.5
        res = generate_final_signal(current_price, support, resistance, atr, recommendation="BUY")
        assert res["signal_valid"] is False
        assert res["reason"] == "TARGET_BELOW_ENTRY_PRICE"

    def test_06_target_below_current_price_rejected(self):
        """Target <= current_price must be rejected with TARGET_BELOW_CURRENT_PRICE."""
        support = {"level": 100.0, "zone_low": 100.0}
        resistance = {"level": 102.0, "zone_low": 100.2} # Below current_price
        atr = 4.0
        current_price = 100.5
        res = generate_final_signal(current_price, support, resistance, atr, recommendation="BUY")
        assert res["signal_valid"] is False
        assert res["reason"] == "TARGET_BELOW_CURRENT_PRICE"

    def test_07_financial_engine_cold_start_requires_min_two_subscores(self):
        """When fewer than 2 subscores are available, financial overall_score must be None."""
        # Test historical evaluation on 2025-06-15 where only 1 quarter is available
        res = analyze_financial_health("ABB", evaluation_date="2025-06-15")
        assert res["overall_score"] is None
        assert res["status"] == "INSUFFICIENT"

    @pytest.mark.requires_preseeded_db
    def test_08_financial_engine_becomes_active_when_four_quarters_eligible(self):
        """When 4 quarters are eligible (post 2026-02-14), overall_score is computed."""
        res = analyze_financial_health("ABB", evaluation_date="2026-02-16")
        assert res["overall_score"] is not None
        assert res["overall_score"] > 0
        assert res["status"] in ("VALID", "PARTIAL")

    def test_09_portfolio_simulator_rejects_already_in_position(self):
        """Portfolio simulator must reject duplicate entries for an open position."""
        df_sym = pd.DataFrame({
            "date": ["2026-04-15", "2026-04-16", "2026-04-17", "2026-04-20"],
            "open": [100.0, 100.0, 101.0, 102.0],
            "high": [105.0, 104.0, 103.0, 104.0],
            "low": [98.0, 99.0, 100.0, 101.0],
            "close": [102.0, 101.0, 102.0, 103.0],
            "volume": [1000, 1000, 1000, 1000]
        })
        sig1 = {
            "symbol": "TESTSYM",
            "evaluation_date": "2026-04-15",
            "signal_valid": True,
            "is_eligible": True,
            "stop_loss": 95.0,
            "target": 115.0,
            "recommendation": "BUY",
            "opportunity_score": 85.0
        }
        sig2 = {
            "symbol": "TESTSYM",
            "evaluation_date": "2026-04-16",
            "signal_valid": True,
            "is_eligible": True,
            "stop_loss": 95.0,
            "target": 115.0,
            "recommendation": "BUY",
            "opportunity_score": 85.0
        }
        market_data = {"TESTSYM": df_sym}
        cfg = PortfolioConfig(initial_capital=100000.0, max_open_positions=5)
        sim_res = simulate_portfolio([sig1, sig2], market_data, cfg, run_id="test_dup")
        
        assert len(sim_res["all_trades"]) == 1 # Only 1 trade entered
        rejections = sim_res["rejected_signals"]
        assert len(rejections) == 1
        assert rejections[0]["reason"] == RejectionReason.ALREADY_IN_POSITION

    @pytest.mark.requires_preseeded_db
    def test_10_production_database_remains_unmodified(self):
        """Confirm production database SHA-256 matches baseline perfectly."""
        with open(DB_PATH, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest().upper()
        assert h == EXPECTED_DB_SHA256, f"Production DB altered! Found {h}"

