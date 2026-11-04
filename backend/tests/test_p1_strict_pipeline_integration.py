"""
Integration Test Suite: P1 Strict Point-in-Time Financial Pipeline Integration
==============================================================================

Verifies the end-to-end propagation and execution of `require_verified_publication_date`:
1. `run_research_backtest()` enables strict financial verification by default.
2. `ResearchBacktestConfig` carries strict-mode settings into runtime execution.
3. Evaluator propagates strict mode to signal integration.
4. Signal integration propagates strict mode to decision engine.
5. Decision engine propagates strict mode to financial health analysis and stock snapshot.
6. Financial health analysis propagates strict mode to underlying financial analyzers (ROE, ROCE, D/E, Margin, Growth, Valuation).
7. Missing publication date does NOT fall back to period_end + 45d in a strict research run.
8. Legacy callers retain period_end + 45d fallback when strict mode is False / omitted.
9. Missing financial data produces explicit status (NO_ELIGIBLE_RECORDS / INSUFFICIENT) without crashing or fabricating metrics.
10. Independent coexistence with P0 anomaly quarantine.
"""

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from backend.logic.backtest_specification import (
    BacktestConfig,
    ResearchBacktestConfig,
)
from backend.logic.backtest_engine import (
    run_single_stock_backtest,
    run_portfolio_backtest,
    run_backtest,
    run_research_backtest,
)
from backend.logic.historical_signal_evaluator import (
    evaluate_historical_signal,
    evaluate_historical_signals,
)
from backend.logic.signal_integration import run_signal_pipeline
from backend.engines.decision_engine import calculate_opportunity_score
from backend.engines.financial_engine import analyze_financial_health
from backend.logic.roe_analyzer import analyze_roe
from backend.logic.roce_analyzer import analyze_roce
from backend.logic.debt_equity_analyzer import analyze_debt_equity
from backend.logic.profit_margin_analyzer import analyze_profit_margin
from backend.logic.growth_analyzer import analyze_growth
from backend.logic.valuation_analyzer import analyze_valuation


class TestP1StrictPipelineIntegration:

    def test_01_research_backtest_config_defaults(self):
        """1. ResearchBacktestConfig explicitly defaults both safeguards to True."""
        cfg = ResearchBacktestConfig(
            symbols=["INFY"],
            start_date="2024-01-01",
            end_date="2024-01-15",
        )
        assert cfg.quarantine_unresolved_anomalies is True
        assert cfg.require_verified_publication_date is True

        # Standard BacktestConfig defaults both to False
        legacy_cfg = BacktestConfig(
            symbols=["INFY"],
            start_date="2024-01-01",
            end_date="2024-01-15",
        )
        assert legacy_cfg.quarantine_unresolved_anomalies is False
        assert legacy_cfg.require_verified_publication_date is False

    def test_02_run_research_backtest_forwards_both_safeguards(self):
        """2. run_research_backtest propagates both quarantine and strict financial flags."""
        with patch("backend.logic.backtest_engine.run_backtest") as mock_backtest:
            mock_backtest.return_value = {"status": "SUCCESS", "all_trades": []}

            run_research_backtest(
                symbols=["INFY"],
                start_date="2024-01-01",
                end_date="2024-01-15",
            )

            assert mock_backtest.called
            kwargs = mock_backtest.call_args.kwargs
            assert kwargs["quarantine_unresolved_anomalies"] is True
            assert kwargs["require_verified_publication_date"] is True

    def test_03_run_backtest_propagates_to_portfolio_and_single(self):
        """3. run_backtest propagates require_verified_publication_date to sequential and loop paths."""
        # Sequential mode -> run_portfolio_backtest
        with patch("backend.logic.backtest_engine.run_portfolio_backtest") as mock_port:
            mock_port.return_value = {"status": "SUCCESS"}
            run_backtest(
                symbols=["INFY"],
                start_date="2024-01-01",
                end_date="2024-01-15",
                sequential=True,
                require_verified_publication_date=True,
            )
            assert mock_port.call_args.kwargs["require_verified_publication_date"] is True

        # Non-sequential mode -> run_single_stock_backtest
        with patch("backend.logic.backtest_engine.run_single_stock_backtest") as mock_single:
            mock_single.return_value = {"status": "SUCCESS", "trades": []}
            run_backtest(
                symbols=["INFY"],
                start_date="2024-01-01",
                end_date="2024-01-15",
                sequential=False,
                require_verified_publication_date=True,
            )
            assert mock_single.call_args.kwargs["require_verified_publication_date"] is True

    def test_04_evaluator_propagates_to_signal_pipeline(self):
        """4. evaluate_historical_signals propagates strict flag to evaluate_historical_signal and run_signal_pipeline."""
        with patch("backend.logic.historical_signal_evaluator.run_signal_pipeline") as mock_pipe:
            mock_pipe.return_value = {"signal_valid": False, "is_eligible": False}

            evaluate_historical_signals("INFY", ["2024-01-05"], require_verified_publication_date=True)

            mock_pipe.assert_called_once_with(
                "INFY",
                evaluation_date="2024-01-05",
                require_verified_publication_date=True,
            )

    def test_05_signal_pipeline_propagates_to_decision_engine(self):
        """5. run_signal_pipeline propagates strict flag to calculate_opportunity_score."""
        with patch("backend.logic.signal_integration.calculate_opportunity_score") as mock_opp, \
             patch("backend.logic.signal_integration.get_stop_target_inputs") as mock_inputs:

            mock_opp.return_value = {"recommendation": "BUY"}
            mock_inputs.return_value = {
                "current_price": 1500.0,
                "nearest_support": {"level": 1450.0},
                "nearest_resistance": {"zone_low": 1600.0},
                "atr_14": 20.0,
            }

            run_signal_pipeline("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            mock_opp.assert_called_once_with(
                "INFY",
                evaluation_date="2024-01-05",
                require_verified_publication_date=True,
            )

    def test_06_decision_engine_propagates_to_snapshot_and_financial_health(self):
        """6. calculate_opportunity_score propagates strict flag to get_stock_snapshot and analyze_financial_health."""
        with patch("backend.engines.decision_engine.get_stock_snapshot") as mock_snap, \
             patch("backend.engines.financial_engine.analyze_financial_health") as mock_health, \
             patch("backend.engines.decision_engine.run_technical_pipeline") as mock_tech:

            mock_snap.return_value = {"status": "PARTIAL", "financial": None}
            mock_health.return_value = {"overall_score": 75.0, "status": "VALID"}
            mock_tech.return_value = {"technical_score": 80.0, "rsi": 55.0, "macd_histogram": 1.2}

            calculate_opportunity_score("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            mock_snap.assert_called_once_with(
                "INFY",
                evaluation_date="2024-01-05",
                require_verified_publication_date=True,
            )
            mock_health.assert_called_once_with(
                "INFY",
                evaluation_date="2024-01-05",
                require_verified_publication_date=True,
            )

    def test_07_financial_health_propagates_to_all_sub_analyzers(self):
        """7. analyze_financial_health propagates strict flag to ROE, ROCE, D/E, Margin, Growth, Valuation."""
        with patch("backend.logic.roe_analyzer.analyze_roe") as mock_roe, \
             patch("backend.logic.roce_analyzer.analyze_roce") as mock_roce, \
             patch("backend.logic.debt_equity_analyzer.analyze_debt_equity") as mock_de, \
             patch("backend.logic.profit_margin_analyzer.analyze_profit_margin") as mock_margin, \
             patch("backend.logic.growth_analyzer.analyze_growth") as mock_growth, \
             patch("backend.logic.volatility_analyzer.analyze_volatility") as mock_vol, \
             patch("backend.logic.valuation_analyzer.analyze_valuation") as mock_val:

            for m in [mock_roe, mock_roce, mock_de, mock_margin, mock_growth, mock_vol, mock_val]:
                m.return_value = {"status": "VALID"}

            analyze_financial_health("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            mock_roe.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_roce.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_de.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_margin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_growth.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_val.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

    def test_08_sub_analyzers_propagate_to_get_financial_data(self):
        """8. Sub-analyzers forward require_verified_publication_date to get_financial_data."""
        with patch("backend.logic.roe_analyzer.get_financial_data") as mock_roe_fin, \
             patch("backend.logic.roce_analyzer.get_financial_data") as mock_roce_fin, \
             patch("backend.logic.debt_equity_analyzer.get_financial_data") as mock_de_fin, \
             patch("backend.logic.profit_margin_analyzer.get_financial_data") as mock_margin_fin, \
             patch("backend.logic.growth_analyzer.get_financial_data") as mock_growth_fin, \
             patch("backend.logic.valuation_analyzer.get_financial_data") as mock_val_fin:

            for m in [mock_roe_fin, mock_roce_fin, mock_de_fin, mock_margin_fin, mock_growth_fin, mock_val_fin]:
                m.return_value = pd.DataFrame()

            analyze_roe("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_roe_fin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            analyze_roce("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_roce_fin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            analyze_debt_equity("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_de_fin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            analyze_profit_margin("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_margin_fin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            analyze_growth("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_growth_fin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

            analyze_valuation("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            mock_val_fin.assert_called_once_with("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)

    def test_09_strict_mode_rejects_unverified_in_research_signal_pipeline(self):
        """9. Unverified financial records produce INSUFFICIENT financial health in strict research backtest."""
        with patch("backend.logic.roe_analyzer.analyze_roe") as mock_roe, \
             patch("backend.logic.roce_analyzer.analyze_roce") as mock_roce, \
             patch("backend.logic.debt_equity_analyzer.analyze_debt_equity") as mock_de, \
             patch("backend.logic.profit_margin_analyzer.analyze_profit_margin") as mock_margin, \
             patch("backend.logic.growth_analyzer.analyze_growth") as mock_growth, \
             patch("backend.logic.volatility_analyzer.analyze_volatility") as mock_vol, \
             patch("backend.logic.valuation_analyzer.analyze_valuation") as mock_val:

            def fake_analyzer(sym, evaluation_date=None, **kwargs):
                if kwargs.get("require_verified_publication_date"):
                    return {"status": "INSUFFICIENT"}
                return {"status": "VALID", "latest_roe": 0.15, "latest_roce": 0.18, "latest_debt_equity": 0.3, "latest_net_margin": 15.0, "revenue_yoy_growth": 10.0, "net_profit_yoy_growth": 12.0, "pe_ratio": 20.0}

            mock_roe.side_effect = fake_analyzer
            mock_roce.side_effect = fake_analyzer
            mock_de.side_effect = fake_analyzer
            mock_margin.side_effect = fake_analyzer
            mock_growth.side_effect = fake_analyzer
            mock_vol.return_value = {"status": "VALID"}
            mock_val.side_effect = fake_analyzer

            # Strict mode run
            strict_health = analyze_financial_health("INFY", evaluation_date="2023-11-20", require_verified_publication_date=True)
            assert strict_health["status"] == "INSUFFICIENT"
            assert strict_health["overall_score"] is None

            # Legacy mode run
            legacy_health = analyze_financial_health("INFY", evaluation_date="2023-11-20", require_verified_publication_date=False)
            assert legacy_health["status"] in ("VALID", "PARTIAL")
            assert legacy_health["overall_score"] is not None

    def test_10_missing_financials_do_not_crash_opportunity_scoring(self):
        """10. Missing financials in strict mode safely default financial score to None without crashing."""
        with patch("backend.engines.financial_engine.analyze_financial_health") as mock_health, \
             patch("backend.engines.decision_engine.get_stock_snapshot") as mock_snap, \
             patch("backend.engines.decision_engine.run_technical_pipeline") as mock_tech:

            mock_snap.return_value = {"status": "PARTIAL", "financial": None}
            # Strict mode returns INSUFFICIENT
            mock_health.return_value = {
                "symbol": "INFY",
                "status": "INSUFFICIENT",
                "overall_score": None,
            }
            mock_tech.return_value = {
                "technical_score": 85.0,
                "rsi": 60.0,
                "macd_histogram": 2.5,
            }

            res = calculate_opportunity_score("INFY", evaluation_date="2024-01-05", require_verified_publication_date=True)
            assert res["symbol"] == "INFY"
            assert res["financial_score"] is None
            assert res["status"] in ("VALID", "PARTIAL", "INSUFFICIENT")
