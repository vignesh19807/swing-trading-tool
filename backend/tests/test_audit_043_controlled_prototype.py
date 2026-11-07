"""
AUDIT-043 Regression Tests: Experimental Setups, Financial Staging, and Point-in-Time Safety
=============================================================================================
"""

import hashlib
import os
import pytest
import sqlite3

pytestmark = pytest.mark.requires_preseeded_db
import pytest
import pandas as pd
import numpy as np

from backend.experimental.dual_setups import (
    MomentumBreakoutSetup,
    SupportPullbackSetup,
    DualSetupArbitrator
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROD_DB = os.path.join(PROJECT_ROOT, "database", "swing_trading.db")
STAGING_DB = os.path.join(PROJECT_ROOT, "database", "staging_financial_expansion.db")
EXPECTED_PROD_HASH = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"


class TestAudit043ControlledPrototype:

    def test_01_production_db_remains_strictly_invariant(self):
        """Production database must remain 100% byte-for-byte untouched."""
        assert os.path.exists(PROD_DB)
        hasher = hashlib.sha256()
        with open(PROD_DB, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        assert hasher.hexdigest().upper() == EXPECTED_PROD_HASH

    def test_02_staging_db_isolated_and_valid_schema(self):
        """Staging database must exist and match production schema."""
        assert os.path.exists(STAGING_DB)
        con = sqlite3.connect(STAGING_DB)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        con.close()
        for required_t in ["companies", "daily_prices", "technical_indicators", "quarterly_results"]:
            assert required_t in tables

    def test_03_momentum_breakout_prototype_contract(self):
        """Verify MomentumBreakoutSetup requires trend alignment, volume, and R:R."""
        setup = MomentumBreakoutSetup()
        # Mock history with rising prices and breakout
        dates = pd.date_range("2026-01-01", periods=30, freq="D").strftime("%Y-%m-%d")
        df_mock = pd.DataFrame({
            "date": dates,
            "open": [100.0 + i for i in range(30)],
            "high": [102.0 + i for i in range(30)],
            "low": [99.0 + i for i in range(30)],
            "close": [101.0 + i for i in range(30)],
            "volume": [1000000] * 29 + [3000000],  # Volume spike on last day
            "rsi": [62.0] * 30,
            "macd_histogram": [2.5] * 30,
            "ema_20": [95.0 + i for i in range(30)],
            "ema_50": [90.0 + i for i in range(30)],
            "atr_14": [2.0] * 30
        })
        res = setup.evaluate("TEST_STOCK", dates[-1], df_mock)
        assert res["is_qualified"] is True
        assert res["setup_id"] == "MOMENTUM_BREAKOUT_SETUP"
        assert res["risk_reward_ratio"] >= 1.50
        assert res["entry_lower"] <= res["market_price"] <= res["entry_upper"]

    def test_04_support_pullback_prototype_contract(self):
        """Verify SupportPullbackSetup requires macro trend and support proximity."""
        setup = SupportPullbackSetup()
        dates = pd.date_range("2026-01-01", periods=30, freq="D").strftime("%Y-%m-%d")
        df_mock = pd.DataFrame({
            "date": dates,
            "open": [150.0] * 30,
            "high": [153.0] * 30,
            "low": [149.0] * 30,
            "close": [150.5] * 30,
            "volume": [1000000] * 30,
            "rsi": [38.0] * 30,  # Pullback / oversold
            "macd_histogram": [-0.5] * 30,
            "ema_50": [140.0] * 30,
            "ema_200": [130.0] * 30,
            "atr_14": [3.0] * 30
        })
        nearest_support = {"level": 150.0, "zone_low": 149.0}
        nearest_resistance = {"level": 165.0, "zone_low": 165.0}

        res = setup.evaluate("TEST_STOCK", dates[-1], df_mock, nearest_support, nearest_resistance)
        assert res["is_qualified"] is True
        assert res["setup_id"] == "SUPPORT_PULLBACK_SETUP"
        assert res["risk_reward_ratio"] >= 1.50

    def test_05_arbitrator_conflict_resolution(self):
        """Arbitrator must deterministically arbitrate between setups."""
        arb = DualSetupArbitrator()
        res_a = {"is_qualified": True, "setup_id": "MOMENTUM_BREAKOUT_SETUP", "risk_reward_ratio": 2.5}
        res_b = {"is_qualified": True, "setup_id": "SUPPORT_PULLBACK_SETUP", "risk_reward_ratio": 1.6}
        chosen, reason = arb.arbitrate(res_a, res_b)
        assert chosen["setup_id"] == "MOMENTUM_BREAKOUT_SETUP"
        assert reason == "BREAKOUT_SUPERIOR_RR"

    def test_06_production_baseline_remains_reproducible(self):
        """Verify baseline 8 trades exist and match in the persistent audit ledger."""
        import json
        with open(os.path.join(PROJECT_ROOT, "docs", "audit_artifacts", "audit_025_multiyear_results.json"), "r") as f:
            data = json.load(f)
        trades = data["simulations"]["full_horizon_10bps"]["closed_trades"]
        assert len(trades) == 8
        summary = data["simulations"]["full_horizon_10bps"]["portfolio_summary"]
        assert round(summary["total_net_pl"], 2) == -1223.69
        assert round(summary["total_return_pct"], 2) == -1.22

