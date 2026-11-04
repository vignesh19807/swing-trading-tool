"""
Integration regression tests for P0: Backtesting Research-Integrity Closure.

Verifies:
1. `run_single_stock_backtest` properly propagates `quarantine_unresolved_anomalies` to `get_historical_data`.
2. When `quarantine_unresolved_anomalies=True`, TRENT observations on 2026-01-01 are excluded from market data and signals.
3. When `quarantine_unresolved_anomalies=False` (default), backward compatibility is preserved.
4. `run_portfolio_backtest` propagates `quarantine_unresolved_anomalies` across all symbols.
5. `run_backtest` propagates `quarantine_unresolved_anomalies` through sequential mode and fallback loop.
6. Downstream signals cannot consume or evaluate quarantined anomaly bars.
7. Filtering behaves correctly even if DataFrame lacks an explicit 'symbol' column.
8. Unrelated symbols (e.g. INFY, TCS) on 2026-01-01 remain unaffected and preserved.
9. `run_research_backtest` explicitly enforces `quarantine_unresolved_anomalies=True` by default.
10. `ResearchBacktestConfig` dataclass explicitly defaults to `quarantine_unresolved_anomalies=True`.
11. Quarantine setting cannot be silently ignored or overridden to False without explicit intent.
"""

from unittest.mock import patch
import pandas as pd
import pytest

from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.research_market_data_filter import filter_research_market_data
from backend.logic.backtest_engine import (
    run_backtest,
    run_portfolio_backtest,
    run_research_backtest,
    run_single_stock_backtest,
)
from backend.logic.backtest_specification import (
    BacktestConfig,
    ResearchBacktestConfig,
)


def _mock_trent_df():
    """Returns a synthetic TRENT DataFrame spanning 2025-12-30 through 2026-01-05."""
    return pd.DataFrame({
        "symbol": ["TRENT"] * 5,
        "date": ["2025-12-30", "2025-12-31", "2026-01-01", "2026-01-02", "2026-01-05"],
        "open": [5000.0, 5020.0, 3350.0, 3360.0, 3380.0],
        "high": [5050.0, 5060.0, 3400.0, 3410.0, 3420.0],
        "low": [4980.0, 5000.0, 3300.0, 3320.0, 3350.0],
        "close": [5010.0, 5030.0, 3360.0, 3370.0, 3390.0],
        "volume": [100000, 120000, 250000, 110000, 115000],
    })


def _mock_infy_df():
    """Returns a synthetic INFY DataFrame spanning 2025-12-30 through 2026-01-05."""
    return pd.DataFrame({
        "symbol": ["INFY"] * 5,
        "date": ["2025-12-30", "2025-12-31", "2026-01-01", "2026-01-02", "2026-01-05"],
        "open": [1800.0, 1810.0, 1815.0, 1820.0, 1825.0],
        "high": [1820.0, 1825.0, 1830.0, 1835.0, 1840.0],
        "low": [1790.0, 1800.0, 1805.0, 1810.0, 1815.0],
        "close": [1810.0, 1815.0, 1820.0, 1825.0, 1830.0],
        "volume": [500000, 550000, 600000, 520000, 530000],
    })


def test_01_filter_research_market_data_without_symbol_column():
    """Test 1: filter_research_market_data works when DataFrame has no 'symbol' column."""
    df_no_sym = _mock_trent_df().drop(columns=["symbol"])
    assert "symbol" not in df_no_sym.columns

    # With symbol provided explicitly as argument
    filtered = filter_research_market_data(
        df_no_sym,
        symbol="TRENT",
        quarantine_unresolved_anomalies=True,
    )
    assert "2026-01-01" not in filtered["date"].values
    assert len(filtered) == 4

    # Without quarantine
    unfiltered = filter_research_market_data(
        df_no_sym,
        symbol="TRENT",
        quarantine_unresolved_anomalies=False,
    )
    assert "2026-01-01" in unfiltered["date"].values
    assert len(unfiltered) == 5


def test_02_unrelated_symbols_preserved_on_anomaly_date():
    """Test 2: Non-quarantined symbols (e.g. INFY) on 2026-01-01 are not dropped."""
    infy_df = _mock_infy_df()
    filtered = filter_research_market_data(
        infy_df,
        symbol="INFY",
        quarantine_unresolved_anomalies=True,
    )
    assert "2026-01-01" in filtered["date"].values
    assert len(filtered) == 5


def test_03_run_single_stock_backtest_quarantine_parameter():
    """Test 3: run_single_stock_backtest forwards quarantine flag to get_historical_data."""
    # Case A: quarantine_unresolved_anomalies=True
    with patch("backend.logic.backtest_engine.get_historical_data") as mock_get_hist, \
         patch("backend.logic.backtest_engine.evaluate_historical_signals", return_value=[]) as mock_eval, \
         patch("backend.logic.backtest_engine.simulate_trades_for_signals", return_value=[]):

        def fake_get_hist(sym, start_date=None, end_date=None, quarantine_unresolved_anomalies=False):
            df = _mock_trent_df()
            if quarantine_unresolved_anomalies:
                df = df[df["date"] != "2026-01-01"]
            return {"data": df, "cached": False, "count": len(df)}

        mock_get_hist.side_effect = fake_get_hist

        res_q = run_single_stock_backtest(
            "TRENT",
            "2025-12-30",
            "2026-01-05",
            quarantine_unresolved_anomalies=True,
        )
        assert mock_get_hist.call_args.kwargs["quarantine_unresolved_anomalies"] is True

        # Check dates passed to evaluate_historical_signals
        eval_dates = mock_eval.call_args.args[1]
        assert "2026-01-01" not in eval_dates
        assert len(eval_dates) == 4

    # Case B: quarantine_unresolved_anomalies=False (default)
    with patch("backend.logic.backtest_engine.get_historical_data") as mock_get_hist, \
         patch("backend.logic.backtest_engine.evaluate_historical_signals", return_value=[]) as mock_eval, \
         patch("backend.logic.backtest_engine.simulate_trades_for_signals", return_value=[]):

        mock_get_hist.side_effect = fake_get_hist

        res_default = run_single_stock_backtest(
            "TRENT",
            "2025-12-30",
            "2026-01-05",
        )
        assert mock_get_hist.call_args.kwargs["quarantine_unresolved_anomalies"] is False

        eval_dates_default = mock_eval.call_args.args[1]
        assert "2026-01-01" in eval_dates_default
        assert len(eval_dates_default) == 5


def test_04_run_portfolio_backtest_quarantine_parameter():
    """Test 4: run_portfolio_backtest forwards quarantine flag to all stock queries."""
    with patch("backend.logic.backtest_engine.get_historical_data") as mock_get_hist, \
         patch("backend.logic.backtest_engine.evaluate_historical_signals", return_value=[]), \
         patch("backend.logic.backtest_engine.simulate_portfolio") as mock_sim, \
         patch("backend.logic.backtest_engine.calculate_backtest_metrics", return_value={}):

        def fake_get_hist(sym, start_date=None, end_date=None, quarantine_unresolved_anomalies=False):
            if sym == "TRENT":
                df = _mock_trent_df()
                if quarantine_unresolved_anomalies:
                    df = df[df["date"] != "2026-01-01"]
                return {"data": df, "cached": False, "count": len(df)}
            else:
                return {"data": _mock_infy_df(), "cached": False, "count": 5}

        mock_get_hist.side_effect = fake_get_hist
        mock_sim.return_value = {
            "all_trades": [],
            "closed_trades": [],
            "open_positions": [],
            "rejected_signals": [],
            "equity_curve": [],
            "portfolio_summary": {"ending_capital": 100000.0},
            "daily_snapshots": [],
        }

        # Run with quarantine True
        res = run_portfolio_backtest(
            ["TRENT", "INFY"],
            "2025-12-30",
            "2026-01-05",
            quarantine_unresolved_anomalies=True,
        )

        # Check call arguments for both symbols
        for call in mock_get_hist.call_args_list:
            assert call.kwargs["quarantine_unresolved_anomalies"] is True

        # Check that market_data_by_symbol passed to simulate_portfolio has TRENT pruned and INFY intact
        market_data_passed = mock_sim.call_args.kwargs["market_data_by_symbol"]
        assert "2026-01-01" not in market_data_passed["TRENT"]["date"].values
        assert "2026-01-01" in market_data_passed["INFY"]["date"].values


def test_05_run_backtest_top_level_wrapper_propagation():
    """Test 5: run_backtest top-level wrapper propagates quarantine flag."""
    # Sequential mode
    with patch("backend.logic.backtest_engine.run_portfolio_backtest") as mock_port:
        mock_port.return_value = {"portfolio_summary": {}, "trades": []}
        run_backtest(
            ["TRENT"],
            "2025-12-30",
            "2026-01-05",
            sequential=True,
            quarantine_unresolved_anomalies=True,
        )
        assert mock_port.call_args.kwargs["quarantine_unresolved_anomalies"] is True

    # Legacy loop fallback mode
    with patch("backend.logic.backtest_engine.run_single_stock_backtest") as mock_single:
        mock_single.return_value = {"trades": [], "summary": {}}
        run_backtest(
            ["TRENT"],
            "2025-12-30",
            "2026-01-05",
            sequential=False,
            quarantine_unresolved_anomalies=True,
        )
        assert mock_single.call_args.kwargs["quarantine_unresolved_anomalies"] is True


def test_06_downstream_signals_cannot_consume_quarantined_anomaly():
    """Test 6: Downstream simulation cannot evaluate or trigger trades on quarantined date."""
    evaluated_dates = []

    def mock_eval_signals(sym, eval_dates):
        evaluated_dates.extend(eval_dates)
        return []

    # Patch get_stock_data at data_service level to simulate real pipeline path
    with patch("backend.data_pipeline.historical_data_service.get_stock_data") as mock_get_stock, \
         patch("backend.logic.backtest_engine.evaluate_historical_signals", side_effect=mock_eval_signals), \
         patch("backend.logic.backtest_engine.simulate_trades_for_signals", return_value=[]):

        mock_get_stock.return_value = _mock_trent_df()

        # Run with quarantine enabled
        res = run_single_stock_backtest(
            "TRENT",
            "2025-12-30",
            "2026-01-05",
            quarantine_unresolved_anomalies=True,
        )

        assert "2026-01-01" not in evaluated_dates
        assert res["status"] == "SUCCESS"
        assert len(evaluated_dates) == 4


def test_07_run_research_backtest_enforces_quarantine_by_default():
    """Test 7: run_research_backtest explicitly sets quarantine_unresolved_anomalies=True by default."""
    with patch("backend.logic.backtest_engine.run_backtest") as mock_run_backtest:
        mock_run_backtest.return_value = {"status": "SUCCESS"}

        run_research_backtest(
            symbols=["TRENT", "INFY"],
            start_date="2025-12-30",
            end_date="2026-01-05",
        )

        assert mock_run_backtest.called
        kwargs = mock_run_backtest.call_args.kwargs
        assert kwargs["quarantine_unresolved_anomalies"] is True


def test_08_research_backtest_config_defaults_to_quarantine_true():
    """Test 8: ResearchBacktestConfig dataclass defaults quarantine to True."""
    cfg = ResearchBacktestConfig(
        symbols=["TRENT"],
        start_date="2025-12-30",
        end_date="2026-01-05",
    )
    assert cfg.quarantine_unresolved_anomalies is True

    # Confirm standard BacktestConfig maintains legacy default False
    legacy_cfg = BacktestConfig(
        symbols=["TRENT"],
        start_date="2025-12-30",
        end_date="2026-01-05",
    )
    assert legacy_cfg.quarantine_unresolved_anomalies is False


def test_09_run_research_backtest_end_to_end_trent_exclusion():
    """Test 9: End-to-end execution of run_research_backtest excludes TRENT on 2026-01-01 while keeping INFY."""
    with patch("backend.data_pipeline.historical_data_service.get_stock_data") as mock_get_stock, \
         patch("backend.logic.backtest_engine.evaluate_historical_signals", return_value=[]), \
         patch("backend.logic.backtest_engine.simulate_portfolio") as mock_sim, \
         patch("backend.logic.backtest_engine.calculate_backtest_metrics", return_value={}):

        def fake_get_stock(sym, start_date=None, end_date=None, **kwargs):
            if sym == "TRENT":
                return _mock_trent_df()
            return _mock_infy_df()

        mock_get_stock.side_effect = fake_get_stock
        mock_sim.return_value = {
            "all_trades": [],
            "closed_trades": [],
            "open_positions": [],
            "rejected_signals": [],
            "equity_curve": [],
            "portfolio_summary": {"ending_capital": 100000.0},
            "daily_snapshots": [],
        }

        # Execute using dedicated research entry point
        res = run_research_backtest(
            symbols=["TRENT", "INFY"],
            start_date="2025-12-30",
            end_date="2026-01-05",
        )

        passed_market_data = mock_sim.call_args.kwargs["market_data_by_symbol"]
        assert "2026-01-01" not in passed_market_data["TRENT"]["date"].values
        assert "2026-01-01" in passed_market_data["INFY"]["date"].values
        assert len(passed_market_data["TRENT"]) == 4
        assert len(passed_market_data["INFY"]) == 5
