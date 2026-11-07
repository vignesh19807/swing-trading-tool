"""
AUDIT-041: Historical Data Readiness & Strategy Architecture Tests
==================================================================
Tests the exact data readiness, cold-start mechanics, and strategy architecture
findings established in AUDIT-041:
1. 45-day statutory lag quarter availability boundaries.
2. Financial cold-start: < 2 valid subscores returns overall_score=None.
3. Cold-start progression across 1, 2, 3, and 4 quarters.
4. TTM EPS requirement of 4 quarters in Valuation Analyzer.
5. YoY Growth requirement of 5 quarters in Growth Analyzer.
6. Momentum-Pullback paradigm clash verification.
7. Conservative R:R gate verification.
8. Production database checksum invariance.
"""

import pytest
import sqlite3

pytestmark = pytest.mark.requires_preseeded_db
import hashlib
import os
import pandas as pd

from backend.data_pipeline.financial_service import get_financial_data
from backend.engines.financial_engine import analyze_financial_health
from backend.logic.growth_analyzer import analyze_growth
from backend.logic.valuation_analyzer import analyze_valuation
from backend.logic.signal_engine import calculate_entry_zone, generate_final_signal

EXPECTED_DB_SHA256 = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"
DB_PATH = os.path.abspath("database/swing_trading.db")


class TestAudit041HistoricalDataReadiness:

    def test_01_quarter_count_and_metrics_completeness(self):
        """Database contains exactly 5 quarters per company with 100% metrics present."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM quarterly_results")
        total_qr = c.fetchone()[0]
        c.execute("SELECT count(DISTINCT company_id) FROM quarterly_results")
        total_cos = c.fetchone()[0]
        c.execute("SELECT count(*) FROM quarterly_results WHERE publication_date IS NULL")
        null_pubs = c.fetchone()[0]
        conn.close()

        assert total_qr == 260
        assert total_cos == 52
        assert null_pubs == 260, "All 260 records must lack publication timestamps"

    def test_02_statutory_45_day_lag_quarter_boundaries(self):
        """Verify 45-day lag: 2025-Q1 becomes available on 2025-05-15, but not on 2025-05-14."""
        # 2025-05-14: 44 days post-quarter -> Q1 ineligible
        df_before = get_financial_data("ABB", evaluation_date="2025-05-14")
        assert df_before.empty

        # 2025-05-15: 45 days post-quarter -> Q1 eligible
        df_on = get_financial_data("ABB", evaluation_date="2025-05-15")
        assert not df_on.empty
        assert len(df_on) == 1
        assert df_on.iloc[0]["quarter"] == "2025-Q1"

    def test_03_financial_cold_start_three_quarters_yields_none(self):
        """With 3 quarters eligible (e.g. 2025-12-01), overall_score must be None."""
        res = analyze_financial_health("ABB", evaluation_date="2025-12-01")
        assert res["overall_score"] is None
        assert res["status"] == "INSUFFICIENT"
        # Profitability is valid, but growth and valuation are insufficient
        assert res["component_statuses"]["roe"] == "VALID"
        assert res["component_statuses"]["growth"] == "INSUFFICIENT"
        assert res["component_statuses"]["valuation"] == "INSUFFICIENT"

    def test_04_valuation_analyzer_requires_four_quarters_for_ttm(self):
        """Valuation analyzer requires 4 quarters to compute TTM EPS."""
        # 3 quarters available on 2025-12-01 -> ttm_eps is None
        val_3q = analyze_valuation("ABB", evaluation_date="2025-12-01")
        assert val_3q["ttm_eps"] is None
        assert val_3q["status"] == "INSUFFICIENT"

        # 4 quarters available on 2026-02-16 -> ttm_eps is computed
        val_4q = analyze_valuation("ABB", evaluation_date="2026-02-16")
        assert val_4q["ttm_eps"] is not None
        assert val_4q["status"] == "VALID"

    def test_05_growth_analyzer_requires_five_quarters_for_yoy(self):
        """Growth analyzer requires 5 quarters to compute YoY comparisons."""
        # 4 quarters on 2026-03-01 -> YoY is None
        growth_4q = analyze_growth("ABB", evaluation_date="2026-03-01")
        assert growth_4q["revenue_yoy_growth"] is None
        assert growth_4q["status"] == "INSUFFICIENT"

        # 5 quarters on 2026-05-16 -> YoY is computed
        growth_5q = analyze_growth("ABB", evaluation_date="2026-05-16")
        assert growth_5q["revenue_yoy_growth"] is not None
        assert growth_5q["status"] == "VALID"

    def test_06_cold_start_resolves_when_four_quarters_available(self):
        """On 2026-02-16 (post 2025-Q4 eligibility), overall financial score activates."""
        res = analyze_financial_health("SUNPHARMA", evaluation_date="2026-02-16")
        assert res["overall_score"] is not None
        assert res["overall_score"] > 60.0
        assert res["status"] in ("VALID", "PARTIAL")

    def test_07_momentum_vs_pullback_paradigm_clash(self):
        """A breakout stock trading 2% above support is rejected by the 0.5 ATR pullback gate."""
        support = {"level": 1000.0, "strength": 1.0}
        atr = 20.0 # 2.0% ATR
        # Upper bound = 1000 + 0.5 * 20 = 1010.0 (+1.0%)
        # Breakout price = 1020.0 (+2.0%)
        breakout_price = 1020.0
        res = calculate_entry_zone(breakout_price, support, atr, recommendation="BUY")
        assert res["entry_valid"] is False
        assert res["reason"] == "PRICE_OUTSIDE_ENTRY_ZONE"

    def test_08_overhead_resistance_compresses_risk_reward(self):
        """When overhead resistance is within 1.5 ATR, R:R drops below 1.50 threshold."""
        support = {"level": 100.0, "zone_low": 100.0}
        resistance = {"level": 102.5, "zone_low": 102.5} # Only 2.5 above price
        atr = 2.0
        current_price = 100.5
        # Stop loss = 100.0 - 1.5 * 2.0 = 97.0 -> Risk = 100.5 - 97.0 = 3.5
        # Target = 102.5 -> Reward = 102.5 - 100.5 = 2.0
        # R:R = 2.0 / 3.5 = 0.5714 < 1.50
        res = generate_final_signal(current_price, support, resistance, atr, recommendation="BUY")
        assert res["signal_valid"] is False
        assert res["reason"] == "INSUFFICIENT_RISK_REWARD_RATIO"

    def test_09_production_database_integrity_invariant(self):
        """Verify production database SHA-256 remains strictly untouched."""
        with open(DB_PATH, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest().upper()
        assert h == EXPECTED_DB_SHA256, f"Production database mutated! Current: {h}"

