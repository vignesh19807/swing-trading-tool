"""
Financial Health Score Aggregator Engine V1 — Unit & Integration Test Suite
=============================================================================

Validates backend/engines/financial_engine.py against the approved Phase 2.1
Technical Specification.

Test Categories:
1. Normalization Boundary Tests (ROE, ROCE, Margin, D/E, Growth)
2. Valuation Scoring Tests (P/E boundaries, Unprofitable, Insufficient, Unit mismatch)
3. Component Weighting & Dynamic Re-weighting Tests (40/35/25 distribution)
4. Volatility Exclusion Tests (Verified non-influence on Financial Health Score)
5. Status Aggregation Tests (Rule C: VALID, PARTIAL, INSUFFICIENT)
6. Output Contract & Data Completeness Tests
7. Edge Case & Precision Tests (Symbol normalization, exceptions, 4-decimal precision)
8. Real-Data Integration Tests (TCS, WIPRO, RELIANCE, INFY, HDFCBANK)

Author: Logic Engineer
"""

import unittest
from unittest.mock import patch
import math

from backend.engines.financial_engine import (
    analyze_financial_health,
    _normalize_roe,
    _normalize_roce,
    _normalize_margin,
    _normalize_de,
    _normalize_growth,
    _calculate_valuation_score,
)


class TestFinancialEngineUnit(unittest.TestCase):
    """Unit tests for individual normalization functions and core engine logic."""

    # -------------------------------------------------------------------------
    # 1. NORMALIZATION BOUNDARY TESTS
    # -------------------------------------------------------------------------
    def test_roe_normalization_boundaries(self):
        """Test ROE normalization piecewise linear curve."""
        self.assertIsNone(_normalize_roe(None))
        self.assertIsNone(_normalize_roe(float("nan")))
        self.assertEqual(_normalize_roe(-0.05), 0.0)
        self.assertEqual(_normalize_roe(0.0), 0.0)
        self.assertEqual(_normalize_roe(0.05), 30.0)
        self.assertEqual(_normalize_roe(0.10), 60.0)
        self.assertEqual(_normalize_roe(0.125), 70.0)
        self.assertEqual(_normalize_roe(0.15), 80.0)
        self.assertEqual(_normalize_roe(0.175), 90.0)
        self.assertEqual(_normalize_roe(0.20), 100.0)
        self.assertEqual(_normalize_roe(0.35), 100.0)

    def test_roce_normalization_boundaries(self):
        """Test ROCE normalization piecewise linear curve."""
        self.assertIsNone(_normalize_roce(None))
        self.assertIsNone(_normalize_roce(float("nan")))
        self.assertEqual(_normalize_roce(-5.0), 0.0)
        self.assertEqual(_normalize_roce(0.0), 0.0)
        # Decimal float (0.05 = 5.0%)
        self.assertEqual(_normalize_roce(0.05), 30.0)
        # Percentage float (5.0 = 5.0%)
        self.assertEqual(_normalize_roce(5.0), 30.0)
        self.assertEqual(_normalize_roce(10.0), 60.0)
        self.assertEqual(_normalize_roce(12.5), 70.0)
        self.assertEqual(_normalize_roce(15.0), 80.0)
        self.assertEqual(_normalize_roce(17.5), 90.0)
        self.assertEqual(_normalize_roce(20.0), 100.0)
        self.assertEqual(_normalize_roce(30.0), 100.0)

    def test_margin_normalization_boundaries(self):
        """Test Net Margin normalization piecewise linear curve."""
        self.assertIsNone(_normalize_margin(None))
        self.assertIsNone(_normalize_margin(float("nan")))
        self.assertEqual(_normalize_margin(-2.0), 0.0)
        self.assertEqual(_normalize_margin(0.0), 0.0)
        self.assertEqual(_normalize_margin(2.5), 20.0)
        self.assertEqual(_normalize_margin(5.0), 40.0)
        self.assertEqual(_normalize_margin(7.5), 50.0)
        self.assertEqual(_normalize_margin(10.0), 60.0)
        self.assertEqual(_normalize_margin(12.5), 70.0)
        self.assertEqual(_normalize_margin(15.0), 80.0)
        self.assertEqual(_normalize_margin(17.5), 90.0)
        self.assertEqual(_normalize_margin(20.0), 100.0)
        self.assertEqual(_normalize_margin(35.0), 100.0)

    def test_de_normalization_boundaries(self):
        """Test Debt/Equity normalization solvency curve."""
        self.assertIsNone(_normalize_de(None))
        self.assertIsNone(_normalize_de(float("nan")))
        self.assertEqual(_normalize_de(0.0), 100.0)
        self.assertEqual(_normalize_de(0.25), 100.0)
        self.assertEqual(_normalize_de(0.50), 100.0)
        # Percentage ratio (11.52% = 0.1152 ratio)
        self.assertEqual(_normalize_de(11.52), 100.0)
        # Percentage inputs (100.0% = 1.0 ratio, 150.0% = 1.5 ratio, 225.0% = 2.25 ratio, 300.0% = 3.0 ratio)
        self.assertEqual(_normalize_de(100.0), 80.0)
        self.assertEqual(_normalize_de(150.0), 60.0)
        self.assertEqual(_normalize_de(225.0), 35.0)
        self.assertEqual(_normalize_de(300.0), 10.0)
        self.assertEqual(_normalize_de(400.0), 10.0)


    def test_growth_normalization_boundaries(self):
        """Test Growth Rate normalization piecewise linear curve."""
        self.assertIsNone(_normalize_growth(None))
        self.assertIsNone(_normalize_growth(float("nan")))
        self.assertEqual(_normalize_growth(-30.0), 0.0)
        self.assertEqual(_normalize_growth(-20.0), 0.0)
        self.assertEqual(_normalize_growth(-10.0), 35.0)
        self.assertEqual(_normalize_growth(0.0), 50.0)
        self.assertEqual(_normalize_growth(7.5), 65.0)
        self.assertEqual(_normalize_growth(15.0), 80.0)
        self.assertEqual(_normalize_growth(22.5), 90.0)
        self.assertEqual(_normalize_growth(30.0), 100.0)
        self.assertEqual(_normalize_growth(45.0), 100.0)

    # -------------------------------------------------------------------------
    # 2. VALUATION SCORING TESTS
    # -------------------------------------------------------------------------
    def test_valuation_scoring_pe_below_5(self):
        """Test valuation score for very low positive P/E (< 5.0)."""
        self.assertEqual(_calculate_valuation_score(3.0, "Undervalued"), 90.0)
        self.assertEqual(_calculate_valuation_score(0.1, "Undervalued"), 90.0)

    def test_valuation_scoring_pe_5(self):
        """Test valuation score at P/E = 5.0 boundary."""
        self.assertEqual(_calculate_valuation_score(5.0, "Undervalued"), 100.0)

    def test_valuation_scoring_pe_between_5_and_15(self):
        """Test valuation score for P/E between 5.0 and 15.0."""
        self.assertEqual(
            _calculate_valuation_score(10.0, "Undervalued"), 95.0
        )
        self.assertEqual(
            _calculate_valuation_score(14.5, "Undervalued"), 90.5
        )

    def test_valuation_scoring_pe_15(self):
        """Test valuation score at P/E = 15.0 boundary."""
        self.assertEqual(
            _calculate_valuation_score(15.0, "Fairly Valued"), 90.0
        )

    def test_valuation_scoring_pe_between_15_and_25(self):
        """Test valuation score for P/E between 15.0 and 25.0."""
        self.assertEqual(
            _calculate_valuation_score(20.0, "Fairly Valued"), 75.0
        )
        self.assertEqual(
            _calculate_valuation_score(16.9175, "Fairly Valued"), 84.2475
        )

    def test_valuation_scoring_pe_25(self):
        """Test valuation score at P/E = 25.0 boundary."""
        self.assertEqual(
            _calculate_valuation_score(25.0, "Fairly Valued"), 60.0
        )

    def test_valuation_scoring_pe_above_25(self):
        """Test valuation score for P/E > 25.0."""
        self.assertEqual(_calculate_valuation_score(30.0, "Overvalued"), 52.0)
        self.assertEqual(_calculate_valuation_score(50.0, "Overvalued"), 20.0)
        self.assertEqual(_calculate_valuation_score(80.0, "Overvalued"), 20.0)

    def test_valuation_scoring_unprofitable(self):
        """Test valuation score for Unprofitable companies (TTM EPS < 0)."""
        self.assertEqual(
            _calculate_valuation_score(-5.0, "Unprofitable"), 10.0
        )
        self.assertEqual(_calculate_valuation_score(0.0, "Unprofitable"), 10.0)

    def test_valuation_scoring_none_and_unit_mismatch(self):
        """Test valuation score for Insufficient Data / missing P/E (INFY unit mismatch)."""
        self.assertIsNone(
            _calculate_valuation_score(None, "Insufficient Data")
        )
        self.assertIsNone(
            _calculate_valuation_score(15.0, "Insufficient Data")
        )
        self.assertIsNone(_calculate_valuation_score(None, "Fairly Valued"))

    # -------------------------------------------------------------------------
    # 3. AGGREGATE WEIGHTING & DYNAMIC RE-WEIGHTING TESTS
    # -------------------------------------------------------------------------
    @patch("backend.logic.roe_analyzer.analyze_roe")
    @patch("backend.logic.roce_analyzer.analyze_roce")
    @patch("backend.logic.debt_equity_analyzer.analyze_debt_equity")
    @patch("backend.logic.profit_margin_analyzer.analyze_profit_margin")
    @patch("backend.logic.growth_analyzer.analyze_growth")
    @patch("backend.logic.volatility_analyzer.analyze_volatility")
    @patch("backend.logic.valuation_analyzer.analyze_valuation")
    def test_weighting_all_three_subscores_valid(
        self,
        mock_val,
        mock_vol,
        mock_growth,
        mock_margin,
        mock_de,
        mock_roce,
        mock_roe,
    ):
        """Test 40% Profitability / 35% Growth / 25% Valuation base weighting."""
        mock_roe.return_value = {"status": "VALID", "latest_roe": 0.20}  # Score 100
        mock_roce.return_value = {
            "status": "VALID",
            "latest_roce": 20.0,
        }  # Score 100
        mock_margin.return_value = {
            "status": "VALID",
            "latest_net_margin": 20.0,
        }  # Score 100
        mock_de.return_value = {
            "status": "VALID",
            "latest_debt_equity": 0.5,
        }  # Score 100
        # Profitability Sub-Score = 100.0

        mock_growth.return_value = {
            "status": "VALID",
            "revenue_yoy_growth": 15.0,  # Score 80
            "net_profit_yoy_growth": 15.0,  # Score 80
        }
        # Growth Sub-Score = 80.0

        mock_val.return_value = {
            "status": "VALID",
            "pe_ratio": 25.0,  # Score 60
            "valuation_classification": "Fairly Valued",
        }
        # Valuation Sub-Score = 60.0

        mock_vol.return_value = {"status": "VALID"}

        res = analyze_financial_health("TEST")
        # Overall = 100*0.40 + 80*0.35 + 60*0.25 = 40 + 28 + 15 = 83.0
        self.assertEqual(res["profitability_score"], 100.0)
        self.assertEqual(res["growth_score"], 80.0)
        self.assertEqual(res["valuation_score"], 60.0)
        self.assertEqual(res["overall_score"], 83.0)
        self.assertEqual(res["status"], "VALID")

    @patch("backend.logic.roe_analyzer.analyze_roe")
    @patch("backend.logic.roce_analyzer.analyze_roce")
    @patch("backend.logic.debt_equity_analyzer.analyze_debt_equity")
    @patch("backend.logic.profit_margin_analyzer.analyze_profit_margin")
    @patch("backend.logic.growth_analyzer.analyze_growth")
    @patch("backend.logic.volatility_analyzer.analyze_volatility")
    @patch("backend.logic.valuation_analyzer.analyze_valuation")
    def test_weighting_profitability_and_growth_only(
        self,
        mock_val,
        mock_vol,
        mock_growth,
        mock_margin,
        mock_de,
        mock_roce,
        mock_roe,
    ):
        """Test dynamic re-weighting when Valuation is None (INFY unit mismatch)."""
        mock_roe.return_value = {"status": "VALID", "latest_roe": 0.20}  # 100
        mock_roce.return_value = {"status": "VALID", "latest_roce": 20.0}  # 100
        mock_margin.return_value = {
            "status": "VALID",
            "latest_net_margin": 20.0,
        }  # 100
        mock_de.return_value = {
            "status": "VALID",
            "latest_debt_equity": 0.5,
        }  # 100
        # Profitability = 100.0

        mock_growth.return_value = {
            "status": "VALID",
            "revenue_yoy_growth": 0.0,  # 50
            "net_profit_yoy_growth": 0.0,  # 50
        }
        # Growth = 50.0

        mock_val.return_value = {
            "status": "PARTIAL",
            "pe_ratio": None,
            "valuation_classification": "Insufficient Data",
        }
        # Valuation = None

        mock_vol.return_value = {"status": "VALID"}

        res = analyze_financial_health("TEST")
        # Dynamic Weights: Prof = 40/75 = 53.3333%, Growth = 35/75 = 46.6667%
        # Overall = 100 * (40/75) + 50 * (35/75) = 53.3333 + 23.3333 = 76.6667
        self.assertEqual(res["profitability_score"], 100.0)
        self.assertEqual(res["growth_score"], 50.0)
        self.assertIsNone(res["valuation_score"])
        self.assertEqual(res["overall_score"], 76.6667)
        self.assertEqual(res["status"], "PARTIAL")

    @patch("backend.logic.roe_analyzer.analyze_roe")
    @patch("backend.logic.roce_analyzer.analyze_roce")
    @patch("backend.logic.debt_equity_analyzer.analyze_debt_equity")
    @patch("backend.logic.profit_margin_analyzer.analyze_profit_margin")
    @patch("backend.logic.growth_analyzer.analyze_growth")
    @patch("backend.logic.volatility_analyzer.analyze_volatility")
    @patch("backend.logic.valuation_analyzer.analyze_valuation")
    def test_weighting_fewer_than_two_subscores(
        self,
        mock_val,
        mock_vol,
        mock_growth,
        mock_margin,
        mock_de,
        mock_roce,
        mock_roe,
    ):
        """Test overall_score = None when fewer than 2 sub-scores are available (HDFCBANK)."""
        mock_roe.return_value = {"status": "VALID", "latest_roe": 0.15}
        mock_roce.return_value = {"status": "INSUFFICIENT", "latest_roce": None}
        mock_margin.return_value = {
            "status": "INSUFFICIENT",
            "latest_net_margin": None,
        }
        mock_de.return_value = {
            "status": "INSUFFICIENT",
            "latest_debt_equity": None,
        }
        # Profitability available = 80.0

        mock_growth.return_value = {
            "status": "INSUFFICIENT",
            "revenue_yoy_growth": None,
        }
        # Growth = None

        mock_val.return_value = {
            "status": "INSUFFICIENT",
            "pe_ratio": None,
            "valuation_classification": "Insufficient Data",
        }
        # Valuation = None

        mock_vol.return_value = {"status": "VALID"}

        res = analyze_financial_health("TEST")
        self.assertIsNotNone(res["profitability_score"])
        self.assertIsNone(res["growth_score"])
        self.assertIsNone(res["valuation_score"])
        self.assertIsNone(res["overall_score"])
        self.assertEqual(res["status"], "INSUFFICIENT")

    # -------------------------------------------------------------------------
    # 4. VOLATILITY EXCLUSION TESTS
    # -------------------------------------------------------------------------
    @patch("backend.logic.roe_analyzer.analyze_roe")
    @patch("backend.logic.roce_analyzer.analyze_roce")
    @patch("backend.logic.debt_equity_analyzer.analyze_debt_equity")
    @patch("backend.logic.profit_margin_analyzer.analyze_profit_margin")
    @patch("backend.logic.growth_analyzer.analyze_growth")
    @patch("backend.logic.volatility_analyzer.analyze_volatility")
    @patch("backend.logic.valuation_analyzer.analyze_valuation")
    def test_volatility_exclusion(
        self,
        mock_val,
        mock_vol,
        mock_growth,
        mock_margin,
        mock_de,
        mock_roce,
        mock_roe,
    ):
        """Verify that altering volatility analyzer output does NOT affect financial scores."""
        mock_roe.return_value = {"status": "VALID", "latest_roe": 0.15}
        mock_roce.return_value = {"status": "VALID", "latest_roce": 15.0}
        mock_margin.return_value = {
            "status": "VALID",
            "latest_net_margin": 15.0,
        }
        mock_de.return_value = {"status": "VALID", "latest_debt_equity": 0.5}
        mock_growth.return_value = {
            "status": "VALID",
            "revenue_yoy_growth": 15.0,
            "net_profit_yoy_growth": 15.0,
        }
        mock_val.return_value = {
            "status": "VALID",
            "pe_ratio": 15.0,
            "valuation_classification": "Fairly Valued",
        }

        # Case A: Volatility VALID
        mock_vol.return_value = {
            "status": "VALID",
            "volatility_20d_annualized": 10.0,
        }
        res_a = analyze_financial_health("TEST")

        # Case B: Volatility INSUFFICIENT / High Volatility
        mock_vol.return_value = {
            "status": "INSUFFICIENT",
            "volatility_20d_annualized": 95.0,
        }
        res_b = analyze_financial_health("TEST")

        self.assertEqual(res_a["profitability_score"], res_b["profitability_score"])
        self.assertEqual(res_a["growth_score"], res_b["growth_score"])
        self.assertEqual(res_a["valuation_score"], res_b["valuation_score"])
        self.assertEqual(res_a["overall_score"], res_b["overall_score"])
        self.assertEqual(res_a["component_statuses"]["volatility"], "VALID")
        self.assertEqual(res_b["component_statuses"]["volatility"], "INSUFFICIENT")

    # -------------------------------------------------------------------------
    # 5. STATUS AGGREGATION TESTS (RULE C)
    # -------------------------------------------------------------------------
    @patch("backend.logic.roe_analyzer.analyze_roe")
    @patch("backend.logic.roce_analyzer.analyze_roce")
    @patch("backend.logic.debt_equity_analyzer.analyze_debt_equity")
    @patch("backend.logic.profit_margin_analyzer.analyze_profit_margin")
    @patch("backend.logic.growth_analyzer.analyze_growth")
    @patch("backend.logic.volatility_analyzer.analyze_volatility")
    @patch("backend.logic.valuation_analyzer.analyze_valuation")
    def test_status_rule_c_valid(
        self,
        mock_val,
        mock_vol,
        mock_growth,
        mock_margin,
        mock_de,
        mock_roce,
        mock_roe,
    ):
        """Status is VALID only if all 3 sub-scores present AND all underlying analyzers VALID."""
        mock_roe.return_value = {"status": "VALID", "latest_roe": 0.15}
        mock_roce.return_value = {"status": "VALID", "latest_roce": 15.0}
        mock_margin.return_value = {
            "status": "VALID",
            "latest_net_margin": 15.0,
        }
        mock_de.return_value = {"status": "VALID", "latest_debt_equity": 0.5}
        mock_growth.return_value = {
            "status": "VALID",
            "revenue_yoy_growth": 15.0,
        }
        mock_val.return_value = {
            "status": "VALID",
            "pe_ratio": 15.0,
            "valuation_classification": "Fairly Valued",
        }
        mock_vol.return_value = {"status": "VALID"}

        res = analyze_financial_health("TEST")
        self.assertEqual(res["status"], "VALID")

    @patch("backend.logic.roe_analyzer.analyze_roe")
    @patch("backend.logic.roce_analyzer.analyze_roce")
    @patch("backend.logic.debt_equity_analyzer.analyze_debt_equity")
    @patch("backend.logic.profit_margin_analyzer.analyze_profit_margin")
    @patch("backend.logic.growth_analyzer.analyze_growth")
    @patch("backend.logic.volatility_analyzer.analyze_volatility")
    @patch("backend.logic.valuation_analyzer.analyze_valuation")
    def test_status_rule_c_partial_from_analyzer(
        self,
        mock_val,
        mock_vol,
        mock_growth,
        mock_margin,
        mock_de,
        mock_roce,
        mock_roe,
    ):
        """Status is PARTIAL if 3 sub-scores present but 1 underlying analyzer is PARTIAL (TCS/WIPRO)."""
        mock_roe.return_value = {"status": "VALID", "latest_roe": 0.15}
        mock_roce.return_value = {"status": "VALID", "latest_roce": 15.0}
        mock_margin.return_value = {
            "status": "VALID",
            "latest_net_margin": 15.0,
        }
        mock_de.return_value = {"status": "VALID", "latest_debt_equity": 0.5}
        mock_growth.return_value = {
            "status": "PARTIAL",
            "revenue_yoy_growth": 15.0,
        }  # PARTIAL analyzer
        mock_val.return_value = {
            "status": "VALID",
            "pe_ratio": 15.0,
            "valuation_classification": "Fairly Valued",
        }
        mock_vol.return_value = {"status": "VALID"}

        res = analyze_financial_health("TEST")
        self.assertEqual(res["status"], "PARTIAL")

    # -------------------------------------------------------------------------
    # 6. OUTPUT CONTRACT & DATA COMPLETENESS TESTS
    # -------------------------------------------------------------------------
    def test_output_contract_keys_and_types(self):
        """Verify presence, non-nullability, types, and schema of output dictionary."""
        res = analyze_financial_health("TCS")
        required_keys = [
            "symbol",
            "status",
            "overall_score",
            "profitability_score",
            "growth_score",
            "valuation_score",
            "component_statuses",
            "data_completeness",
        ]
        for key in required_keys:
            self.assertIn(key, res)

        self.assertIsInstance(res["symbol"], str)
        self.assertIn(res["status"], ["VALID", "PARTIAL", "INSUFFICIENT"])
        self.assertIsInstance(res["component_statuses"], dict)
        self.assertIsInstance(res["data_completeness"], float)

        for comp_status in res["component_statuses"].values():
            self.assertIn(comp_status, ["VALID", "PARTIAL", "INSUFFICIENT"])

    # -------------------------------------------------------------------------
    # 7. EDGE CASE & PRECISION TESTS
    # -------------------------------------------------------------------------
    def test_symbol_normalization(self):
        """Verify white space and case normalization for ticker symbol."""
        res = analyze_financial_health("   tcs   ")
        self.assertEqual(res["symbol"], "TCS")

    def test_empty_symbol_handling(self):
        """Verify graceful handling for empty/None symbols."""
        res = analyze_financial_health("")
        self.assertEqual(res["symbol"], "")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNone(res["overall_score"])

    @patch("backend.logic.roe_analyzer.analyze_roe")
    def test_analyzer_exception_safety(self, mock_roe):
        """Verify exception safety if an analyzer throws an unexpected Exception."""
        mock_roe.side_effect = RuntimeError("Database offline")
        res = analyze_financial_health("TCS")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNone(res["overall_score"])


class TestFinancialEngineIntegration(unittest.TestCase):
    """Integration tests running against the live SQLite project database."""

    def test_real_stock_tcs(self):
        """Live DB Integration Test for TCS."""
        res = analyze_financial_health("TCS")
        self.assertEqual(res["symbol"], "TCS")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertIsNotNone(res["overall_score"])
        self.assertIsNotNone(res["profitability_score"])
        self.assertIsNotNone(res["growth_score"])
        self.assertIsNotNone(res["valuation_score"])
        self.assertGreater(res["overall_score"], 0.0)
        self.assertLessEqual(res["overall_score"], 100.0)

    def test_real_stock_wipro(self):
        """Live DB Integration Test for WIPRO."""
        res = analyze_financial_health("WIPRO")
        self.assertEqual(res["symbol"], "WIPRO")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertIsNotNone(res["overall_score"])
        self.assertIsNotNone(res["profitability_score"])
        self.assertIsNotNone(res["growth_score"])
        self.assertIsNotNone(res["valuation_score"])

    def test_real_stock_reliance(self):
        """Live DB Integration Test for RELIANCE."""
        res = analyze_financial_health("RELIANCE")
        self.assertEqual(res["symbol"], "RELIANCE")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertIsNotNone(res["overall_score"])
        self.assertIsNotNone(res["profitability_score"])
        self.assertIsNotNone(res["growth_score"])
        self.assertIsNotNone(res["valuation_score"])

    def test_real_stock_infy(self):
        """Live DB Integration Test for INFY (Verifies USD ADR P/E mismatch handling)."""
        res = analyze_financial_health("INFY")
        self.assertEqual(res["symbol"], "INFY")
        self.assertEqual(res["status"], "PARTIAL")
        self.assertIsNotNone(res["overall_score"])
        self.assertIsNotNone(res["profitability_score"])
        self.assertIsNotNone(res["growth_score"])
        # Valuation score MUST be None for INFY due to ADR mismatch
        self.assertIsNone(res["valuation_score"])

    def test_real_stock_hdfcbank(self):
        """Live DB Integration Test for HDFCBANK (Verifies insufficient quarters handling)."""
        res = analyze_financial_health("HDFCBANK")
        self.assertEqual(res["symbol"], "HDFCBANK")
        self.assertEqual(res["status"], "INSUFFICIENT")
        self.assertIsNotNone(res["profitability_score"])
        self.assertIsNone(res["growth_score"])
        self.assertIsNone(res["valuation_score"])
        self.assertIsNone(res["overall_score"])


if __name__ == "__main__":
    unittest.main()
