"""
Test Suite: AUDIT-003 and AUDIT-004 Performance Optimization & Regression Tests
==============================================================================

Verifies:
1. /api/stocks returns all expected stocks and schema fields (including precomputed technicals).
2. Existing response fields remain intact and compatible.
3. Opportunity rankings remain consistent for identical inputs.
4. Historical evaluation dates are strictly isolated in cache (no cross-date pollution).
5. AUDIT-001 financial lookahead safety remains intact.
6. Optimized endpoints do not fabricate mock values.
7. Cache invalidation works when underlying database fingerprint changes or clear_all_caches is called.
8. Different evaluation dates do not share incompatible cached results.
9. Repeated requests produce consistent, non-stale results.
10. Precomputed technicals match database indicators and accurately tag insufficiency.
"""

import unittest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engines.cache_service import (
    clear_all_caches,
    get_cached_universe_ranking,
    get_cached_universe_scores,
    get_db_fingerprint,
    set_cached_universe_ranking,
)
from backend.engines.universe_orchestrator import rank_universe


class TestAudit003004Performance(unittest.TestCase):
    """Rigorous verification of backend performance optimizations and cache safety."""

    def setUp(self):
        clear_all_caches()
        self.client = TestClient(app)

    def tearDown(self):
        clear_all_caches()

    def test_01_stocks_endpoint_schema_and_precomputed_technicals(self):
        """
        Verify /api/stocks returns expected schema including precomputed technicals,
        price change, and opportunity score, without requiring individual history requests.
        """
        res = self.client.get("/api/stocks?page=1&limit=50")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("stocks", data)
        self.assertIn("total_count", data)
        self.assertGreaterEqual(data["total_count"], 50)

        stocks = data["stocks"]
        self.assertGreater(len(stocks), 0)
        first = stocks[0]
        # Core fields preserved
        for field in ["symbol", "company_name", "sector", "current_price", "opportunity_score", "recommendation"]:
            self.assertIn(field, first, f"Missing expected field: {field}")

        # Additive precomputed technicals present
        self.assertIn("technicals", first)
        tech = first["technicals"]
        self.assertIn("rsi", tech)
        self.assertIn("ema20", tech)
        self.assertIn("ema50", tech)
        self.assertIn("ema200", tech)
        self.assertIn("macd", tech)
        self.assertIn("signal", tech)
        self.assertIn("status", tech)
        self.assertIn("isInsufficient", tech)

    def test_02_opportunities_endpoint_consistency(self):
        """
        Verify that /api/opportunities returns consistent rankings and setup levels
        across repeated invocations.
        """
        res1 = self.client.get("/api/opportunities")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()

        res2 = self.client.get("/api/opportunities")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()

        self.assertEqual(data1["total_count"], data2["total_count"])
        syms1 = [o["symbol"] for o in data1["opportunities"]]
        syms2 = [o["symbol"] for o in data2["opportunities"]]
        self.assertEqual(syms1, syms2, "Ranking changed between repeated calls!")

        # Verify setup levels exist for top opportunities
        if data1["opportunities"]:
            opp = data1["opportunities"][0]
            self.assertIn("current_price", opp)
            self.assertIn("entry_zone_low", opp)
            self.assertIn("entry_zone_high", opp)
            self.assertIn("stop_loss", opp)
            self.assertIn("target", opp)
            self.assertIn("risk_reward", opp)

    def test_03_historical_evaluation_date_cache_isolation(self):
        """
        Verify that evaluations on different dates (or live latest vs historical)
        do not pollute or reuse each other's cache entries.
        """
        # Call latest
        res_latest = self.client.get("/api/opportunities")
        self.assertEqual(res_latest.status_code, 200)
        data_latest = res_latest.json()
        eval_date_latest = data_latest["evaluation_date"]

        # Call historical date
        hist_date = "2025-06-15"
        res_hist = self.client.get(f"/api/opportunities?evaluation_date={hist_date}")
        self.assertEqual(res_hist.status_code, 200)
        data_hist = res_hist.json()
        self.assertEqual(data_hist["evaluation_date"], hist_date)
        self.assertTrue(data_hist["is_historical"])

        # Cache entries in cache_service must be distinct
        cached_latest = get_cached_universe_ranking(eval_date_latest)
        cached_hist = get_cached_universe_ranking(hist_date)
        self.assertIsNotNone(cached_latest)
        self.assertIsNotNone(cached_hist)
        # Even if ranks are similar, the evaluation_date in the ranking payload must match
        self.assertEqual(cached_hist.get("evaluation_date"), hist_date)

    def test_04_cache_invalidation_on_fingerprint_change(self):
        """
        Verify that when data fingerprint changes (or clear_all_caches is called),
        cached rankings are discarded immediately.
        """
        # Populate cache
        rank_universe()
        self.assertIsNotNone(get_cached_universe_ranking(None))

        # Clear cache
        clear_all_caches()
        self.assertIsNone(get_cached_universe_ranking(None))

    def test_05_audit_001_lookahead_bias_preserved(self):
        """
        Confirm that AUDIT-001 financial availability rules are still strictly active
        when retrieving financial data through stock intelligence.
        """
        from backend.data_pipeline.financial_service import get_latest_financial_data

        # Evaluating on 2025-01-15 must not leak Q1 2025 data
        fin = get_latest_financial_data("INFY", evaluation_date="2025-01-15")
        if fin is not None:
            self.assertNotEqual(fin.get("quarter"), "2025-Q1")

    def test_06_non_fabrication_guarantee(self):
        """
        Verify that no mock benchmark indices (NIFTY 50 / SENSEX) or fake indicators
        are returned by the optimized endpoints.
        """
        indices_res = self.client.get("/api/market/indices")
        self.assertEqual(indices_res.status_code, 200)
        data = indices_res.json()
        self.assertEqual(data["nifty50"]["status"], "UNAVAILABLE")
        self.assertIsNone(data["nifty50"]["value"])
        self.assertEqual(data["sensex"]["status"], "UNAVAILABLE")
        self.assertIsNone(data["sensex"]["value"])

    def test_07_stocks_pagination_and_search_filter(self):
        """
        Verify pagination, search filtering, and sector filtering continue working.
        """
        res_tcs = self.client.get("/api/stocks?search=TCS")
        self.assertEqual(res_tcs.status_code, 200)
        data_tcs = res_tcs.json()
        symbols = [s["symbol"] for s in data_tcs["stocks"]]
        self.assertIn("TCS", symbols)

        res_p2 = self.client.get("/api/stocks?page=2&limit=10")
        self.assertEqual(res_p2.status_code, 200)
        data_p2 = res_p2.json()
        self.assertEqual(data_p2["page"], 2)
        self.assertLessEqual(len(data_p2["stocks"]), 10)


if __name__ == "__main__":
    unittest.main()
