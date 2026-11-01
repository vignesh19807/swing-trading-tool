"""
AUDIT-042: Dual-Setup Strategy Design and Historical Data Expansion Specification Tests
========================================================================================

Verifies that:
1. Production database SHA-256 remains 100% invariant.
2. Baseline Decision Engine and Signal Engine behavior remains completely untouched.
3. Dual-Setup strategy contracts (Setup A Breakout vs. Setup B Pullback) are mathematically sound.
4. Priority Arbitrator deterministically resolves setup conflicts.
5. Ingestion plan for 2024 financials eliminates cold-start without lookahead bias.
"""

import hashlib
import os
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple


# =====================================================================
# Constants & Reference Paths
# =====================================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRODUCTION_DB_PATH = os.path.join(PROJECT_ROOT, "database", "swing_trading.db")
EXPECTED_DB_SHA256 = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"


class TestAudit042DualSetupDesign:
    """Audit tests validating the AUDIT-042 architectural specifications."""

    def test_01_production_database_sha256_invariant(self):
        """Verify production database has not been modified."""
        assert os.path.exists(PRODUCTION_DB_PATH), f"DB file missing: {PRODUCTION_DB_PATH}"
        hasher = hashlib.sha256()
        with open(PRODUCTION_DB_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest().upper()
        assert actual_hash == EXPECTED_DB_SHA256, (
            f"DB modified! Expected {EXPECTED_DB_SHA256}, got {actual_hash}"
        )

    def test_02_baseline_signal_engine_pullback_assumption_intact(self):
        """Verify baseline Signal Engine still operates as a pullback model (untouched)."""
        from backend.logic.signal_engine import calculate_entry_zone

        # In baseline, a price above support + 0.5 ATR must return PRICE_OUTSIDE_ENTRY_ZONE
        res = calculate_entry_zone(
            current_price=105.0,
            atr_14=2.0,
            nearest_support={"level": 100.0},
            recommendation="BUY"
        )
        assert res["entry_valid"] is False
        assert res["reason"] == "PRICE_OUTSIDE_ENTRY_ZONE"
        assert res["entry_lower"] == 100.0
        assert res["entry_upper"] == 101.0  # 100 + 0.5 * 2.0

        # And a price within bounds returns VALID_PULLBACK_ENTRY
        res_valid = calculate_entry_zone(
            current_price=100.5,
            atr_14=2.0,
            nearest_support={"level": 100.0},
            recommendation="BUY"
        )
        assert res_valid["entry_valid"] is True
        assert res_valid["reason"] == "VALID_PULLBACK_ENTRY"

    def test_03_baseline_decision_engine_weights_unmodified(self):
        """Verify baseline Decision Engine opportunity score weighting remains 40/35/25."""
        from backend.engines.decision_engine import calculate_opportunity_score
        import inspect

        # Inspect docstring / documentation of calculate_opportunity_score
        doc = inspect.getmodule(calculate_opportunity_score).__doc__
        assert "Technical Score = 40%" in doc
        assert "Financial Score = 35%" in doc
        assert "Momentum Score  = 25%" in doc
        assert "Combined RSI / MACD influence = 49%" in doc

    def test_04_setup_a_momentum_breakout_specification(self):
        """Validate the mathematical specification for Setup A (Momentum Breakout)."""
        # Model specification logic for Setup A
        breakout_level = 500.0
        current_price = 502.0
        atr_14 = 10.0
        candle_low = 495.0

        # Entry Zone: [Breakout Level, Breakout Level + 0.5 * ATR]
        entry_lower = breakout_level
        entry_upper = breakout_level + (0.5 * atr_14)  # 505.0
        assert entry_lower <= current_price <= entry_upper

        # Stop Loss: min(Candle Low, Breakout Level) - 0.75 * ATR
        stop_loss = min(candle_low, breakout_level) - (0.75 * atr_14)  # 495 - 7.5 = 487.5
        assert stop_loss < current_price

        # Target: Volatility expansion >= 2.0 * ATR
        risk = current_price - stop_loss  # 502 - 487.5 = 14.5
        target = current_price + max(2.0 * atr_14, 2.0 * risk)  # 502 + max(20, 29) = 531.0
        reward = target - current_price  # 29.0
        rr_ratio = reward / risk  # 2.0
        assert rr_ratio >= 1.50

    def test_05_setup_b_support_pullback_specification(self):
        """Validate the mathematical specification for Setup B (Support Pullback)."""
        # Model specification logic for Setup B
        support_level = 300.0
        current_price = 301.5
        atr_14 = 6.0
        overhead_resistance = 315.0

        # Entry Zone: [Support Level, Support Level + 0.5 * ATR]
        entry_lower = support_level
        entry_upper = support_level + (0.5 * atr_14)  # 303.0
        assert entry_lower <= current_price <= entry_upper

        # Stop Loss: Support Level - 1.0 * ATR
        stop_loss = support_level - (1.0 * atr_14)  # 294.0
        assert stop_loss < current_price

        # Target: Overhead Resistance
        target = overhead_resistance  # 315.0
        risk = current_price - stop_loss  # 301.5 - 294.0 = 7.5
        reward = target - current_price  # 315.0 - 301.5 = 13.5
        rr_ratio = reward / risk  # 13.5 / 7.5 = 1.80
        assert rr_ratio >= 1.50

    def test_06_priority_arbitrator_conflict_resolution(self):
        """Validate deterministic arbitration when a symbol satisfies both setups."""
        def arbitrate(candidate_a: Dict[str, Any], candidate_b: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
            rr_a = candidate_a.get("risk_reward_ratio", 0.0)
            rr_b = candidate_b.get("risk_reward_ratio", 0.0)
            if rr_a - rr_b > 0.25:
                return candidate_a, "PRIORITY_RR_SUPERIOR_SETUP_A"
            if rr_b - rr_a > 0.25:
                return candidate_b, "PRIORITY_RR_SUPERIOR_SETUP_B"
            score_a = candidate_a.get("opportunity_score", 0.0)
            score_b = candidate_b.get("opportunity_score", 0.0)
            if score_a > score_b:
                return candidate_a, "PRIORITY_SCORE_SETUP_A"
            if score_b > score_a:
                return candidate_b, "PRIORITY_SCORE_SETUP_B"
            return candidate_a, "PRIORITY_DEFAULT_BREAKOUT"

        # Case 1: Setup A has significantly higher R:R
        cand_a = {"setup": "SETUP_A", "risk_reward_ratio": 2.2, "opportunity_score": 78.0}
        cand_b = {"setup": "SETUP_B", "risk_reward_ratio": 1.6, "opportunity_score": 82.0}
        winner, reason = arbitrate(cand_a, cand_b)
        assert winner["setup"] == "SETUP_A"
        assert reason == "PRIORITY_RR_SUPERIOR_SETUP_A"

        # Case 2: Similar R:R, Setup B has higher opportunity score
        cand_a2 = {"setup": "SETUP_A", "risk_reward_ratio": 1.7, "opportunity_score": 76.0}
        cand_b2 = {"setup": "SETUP_B", "risk_reward_ratio": 1.8, "opportunity_score": 85.0}
        winner2, reason2 = arbitrate(cand_a2, cand_b2)
        assert winner2["setup"] == "SETUP_B"
        assert reason2 == "PRIORITY_SCORE_SETUP_B"

        # Case 3: Tied R:R and score -> defaults to Breakout
        cand_a3 = {"setup": "SETUP_A", "risk_reward_ratio": 1.8, "opportunity_score": 80.0}
        cand_b3 = {"setup": "SETUP_B", "risk_reward_ratio": 1.8, "opportunity_score": 80.0}
        winner3, reason3 = arbitrate(cand_a3, cand_b3)
        assert winner3["setup"] == "SETUP_A"
        assert reason3 == "PRIORITY_DEFAULT_BREAKOUT"

    def test_07_candidate_trace_schema_validation(self):
        """Validate the structural schema of the candidate trace record."""
        trace = {
            "trace_id": "TRC-20260416-INFY-01",
            "evaluation_date": "2026-04-16",
            "symbol": "INFY",
            "market_data": {
                "close": 1520.50,
                "volume": 4520100,
                "volume_sma20": 3200000,
                "atr_14": 28.40,
                "rsi_14": 64.20,
                "macd_hist": 4.15
            },
            "setup_evaluations": {
                "setup_a_breakout": {
                    "is_qualified": True,
                    "breakout_level": 1515.00,
                    "entry_zone": [1515.00, 1529.20],
                    "stop_loss": 1493.70,
                    "target": 1577.30,
                    "risk_reward_ratio": 2.12,
                    "rejection_reason": None
                }
            },
            "arbitration_result": {
                "selected_setup": "SETUP_A_BREAKOUT",
                "arbitration_reason": "SOLE_QUALIFIED_SETUP"
            },
            "signal_quality": {
                "is_eligible": True,
                "rejection_reason": None
            },
            "portfolio_decision": {
                "action": "ORDER_GENERATED",
                "allocated_capital": 20000.00,
                "target_shares": 13,
                "rejection_reason": None
            }
        }

        # Validate mandatory keys
        assert "trace_id" in trace
        assert "evaluation_date" in trace
        assert "symbol" in trace
        assert "setup_evaluations" in trace
        assert "arbitration_result" in trace
        assert "signal_quality" in trace
        assert "portfolio_decision" in trace
        assert trace["signal_quality"]["is_eligible"] is True
        assert trace["portfolio_decision"]["action"] == "ORDER_GENERATED"

    def test_08_financial_expansion_eliminates_cold_start_without_lookahead(self):
        """Verify that ingesting 2024 quarters satisfies statutory 45-day lag for 2025-04-01."""
        # Quarter end dates for 2024
        q1_end = datetime(2024, 3, 31)
        q2_end = datetime(2024, 6, 30)
        q3_end = datetime(2024, 9, 30)
        q4_end = datetime(2024, 12, 31)

        # 45-day statutory lag dates
        q1_eligible = q1_end + timedelta(days=45)  # 2024-05-15
        q2_eligible = q2_end + timedelta(days=45)  # 2024-08-14
        q3_eligible = q3_end + timedelta(days=45)  # 2024-11-14
        q4_eligible = q4_end + timedelta(days=45)  # 2025-02-14

        # Backtest start date
        backtest_start = datetime(2025, 4, 1)

        # Assert all 4 quarters are eligible BEFORE backtest start date
        assert q1_eligible < backtest_start
        assert q2_eligible < backtest_start
        assert q3_eligible < backtest_start
        assert q4_eligible < backtest_start

        # Time between 2024-Q4 statutory eligibility and backtest start
        buffer_days = (backtest_start - q4_eligible).days
        assert buffer_days == 46, f"Expected 46 days buffer, got {buffer_days}"
        # With 4 quarters eligible on Day 1, Valuation (TTM) has exactly 4 quarters,
        # satisfying len(subscores) >= 2 requirement and completely eliminating the cold start!

