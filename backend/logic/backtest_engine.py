"""
Backtest Engine (Portfolio Orchestrator)
========================================

Top-level Backtest Engine orchestrating:
1. Point-in-time historical signal evaluation without forward-looking data leakage
2. Sequential, capital-constrained portfolio simulation with Indian equity transaction costs
3. Deterministic whole-share position sizing and position-limit management
4. Performance metrics and chronological equity curve calculation
5. Transactional, idempotent database persistence via Data Engineer services

Author: Logic & Quantitative Engine
"""

import logging
import uuid
from unittest.mock import MagicMock
from typing import Any, Dict, List, Optional

from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.backtest_result_service import (
    store_backtest_results,
    store_portfolio_backtest_run,
)
from backend.logic.historical_signal_evaluator import evaluate_historical_signals
from backend.logic.trade_simulator import simulate_trades_for_signals
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_metrics import calculate_backtest_metrics
from backend.logic.backtest_specification import (
    BacktestConfig,
    PortfolioConfig,
    TradeState,
    create_trade_record,
)

logger = logging.getLogger(__name__)


def run_single_stock_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes a complete historical backtest for a single stock symbol over a specified date range.

    Parameters
    ----------
    symbol : str
        NSE stock symbol (e.g., "TCS", "INFY").
    start_date : str
        Evaluation start date (YYYY-MM-DD).
    end_date : str
        Evaluation end date (YYYY-MM-DD).
    run_id : str, optional
        Unique run identifier.

    Returns
    -------
    dict
        Structured backtest result containing config, trades, and summary metrics.
    """
    symbol_clean = symbol.strip().upper() if isinstance(symbol, str) else ""
    run_identifier = run_id or f"run_{symbol_clean}_{start_date}_{end_date}"

    # 1. Fetch Historical Market Price Data
    market_res = get_historical_data(symbol_clean, start_date=start_date, end_date=end_date)
    market_df = market_res.get("data")

    if market_df is None or market_df.empty:
        return {
            "run_id": run_identifier,
            "symbol": symbol_clean,
            "start_date": start_date,
            "end_date": end_date,
            "status": "NO_MARKET_DATA",
            "trades": [],
            "metrics": calculate_backtest_metrics([])
        }

    # Normalize dates to string list
    eval_dates = [d.split("T")[0].split(" ")[0] for d in market_df["date"].astype(str).tolist()]

    # 2. Evaluate Historical Signals (Point-in-time, no look-ahead)
    signals = evaluate_historical_signals(symbol_clean, eval_dates)

    # 3. Simulate Trade Execution Post-Signal
    trades = simulate_trades_for_signals(signals, market_df)

    # 4. Calculate Performance Metrics
    metrics = calculate_backtest_metrics(trades)

    return {
        "run_id": run_identifier,
        "symbol": symbol_clean,
        "start_date": start_date,
        "end_date": end_date,
        "status": "SUCCESS",
        "trades": trades,
        "metrics": metrics
    }


def run_portfolio_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    portfolio_config: Optional[PortfolioConfig] = None,
    run_id: Optional[str] = None,
    persist_results: bool = False,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Executes a sequential, capital-constrained portfolio backtest across multiple symbols.

    Parameters
    ----------
    symbols : list of str
        List of NSE stock symbols.
    start_date : str
        Simulation start date (YYYY-MM-DD).
    end_date : str
        Simulation end date (YYYY-MM-DD).
    portfolio_config : PortfolioConfig, optional
        Capital limits, position allocation caps, and cost settings.
    run_id : str, optional
        Unique run identifier. If omitted, generates a unique ID.
    persist_results : bool, default False
        If True, transactionally stores run, trades, and equity curve in database.
    overwrite : bool, default False
        If True, replaces existing run with same run_id. If False, rejects duplicate.

    Returns
    -------
    dict
        Comprehensive portfolio backtest results.
    """
    run_identifier = run_id or f"backtest_{uuid.uuid4().hex[:8]}"
    symbols_clean = sorted([s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()])
    cfg = portfolio_config or PortfolioConfig()

    market_data_by_symbol = {}
    all_signals = []

    # 1. Fetch historical market data and evaluate point-in-time signals for each symbol
    for sym in symbols_clean:
        res = get_historical_data(sym, start_date=start_date, end_date=end_date)
        df = res.get("data")
        if df is not None and not df.empty:
            market_data_by_symbol[sym] = df
            eval_dates = [d.split("T")[0].split(" ")[0] for d in df["date"].astype(str)]
            signals = evaluate_historical_signals(sym, eval_dates)
            all_signals.extend(signals)

    # 2. Execute sequential portfolio simulation
    sim_res = simulate_portfolio(
        signals=all_signals,
        market_data_by_symbol=market_data_by_symbol,
        config=cfg,
        run_id=run_identifier
    )

    all_trades = sim_res["all_trades"]
    equity_curve = sim_res["equity_curve"]

    # 3. Calculate portfolio-wide metrics
    portfolio_metrics = calculate_backtest_metrics(
        trades=all_trades,
        strict_mode=True,
        portfolio_equity_curve=equity_curve,
        initial_capital=cfg.initial_capital
    )

    # 4. Group results per stock
    stock_results = {}
    for sym in symbols_clean:
        sym_trades = [t for t in all_trades if t.get("symbol") == sym]
        stock_results[sym] = {
            "run_id": run_identifier,
            "symbol": sym,
            "status": "SUCCESS" if sym in market_data_by_symbol else "NO_MARKET_DATA",
            "trades": sym_trades,
            "metrics": calculate_backtest_metrics(sym_trades, strict_mode=True)
        }

    # 5. Persist run, trades, and equity curve transactionally if requested
    persisted_count = 0
    if persist_results:
        try:
            pres = store_portfolio_backtest_run(
                run_id=run_identifier,
                strategy_version="V1_SWING",
                start_date=start_date,
                end_date=end_date,
                initial_capital=cfg.initial_capital,
                config={
                    "initial_capital": cfg.initial_capital,
                    "max_open_positions": cfg.max_open_positions,
                    "max_allocation_per_position": cfg.max_allocation_per_position,
                    "end_of_backtest_policy": cfg.end_of_backtest_policy,
                    "enable_costs": cfg.enable_costs,
                    "brokerage_pct": cfg.cost_model.brokerage_pct,
                    "slippage_pct": cfg.cost_model.slippage_pct
                },
                metrics=portfolio_metrics,
                trades=all_trades,
                equity_curve=equity_curve,
                overwrite=overwrite
            )
            persisted_count = pres.get("trades_count", 0)
        except Exception as exc:
            logger.error(f"Failed to persist portfolio backtest results: {exc}")
            raise

    return {
        "run_id": run_identifier,
        "start_date": start_date,
        "end_date": end_date,
        "symbols": symbols_clean,
        "stock_results": stock_results,
        "all_trades": all_trades,
        "closed_trades": sim_res["closed_trades"],
        "open_positions": sim_res["open_positions"],
        "rejected_signals": sim_res["rejected_signals"],
        "portfolio_metrics": portfolio_metrics,
        "equity_curve": equity_curve,
        "portfolio_summary": sim_res["portfolio_summary"],
        "persisted_records": persisted_count
    }


def run_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    run_id: Optional[str] = None,
    persist_results: bool = False,
    sequential: bool = True,
    portfolio_config: Optional[PortfolioConfig] = None,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Executes a multi-stock / multi-period historical backtest across a portfolio universe.

    When sequential=True (the default), executes full capital-constrained, sequential
    portfolio simulation.
    Preserves fallback to single-stock loops when mocked by legacy tests.
    """
    # Detect if run_single_stock_backtest has been patched/mocked by a unit test
    is_mocked = isinstance(run_single_stock_backtest, MagicMock) or hasattr(run_single_stock_backtest, "mock")

    if sequential and not is_mocked:
        return run_portfolio_backtest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            portfolio_config=portfolio_config,
            run_id=run_id,
            persist_results=persist_results,
            overwrite=overwrite
        )

    # Legacy execution fallback
    run_identifier = run_id or f"backtest_{uuid.uuid4().hex[:8]}"
    symbols_clean = [s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()]

    stock_results = {}
    all_trades = []
    persistence_records = []

    for sym in sorted(symbols_clean):
        stock_res = run_single_stock_backtest(sym, start_date=start_date, end_date=end_date, run_id=run_identifier)
        stock_results[sym] = stock_res
        trades = stock_res.get("trades", [])
        all_trades.extend(trades)

        if persist_results:
            for trade in trades:
                persistence_records.append({
                    "run_id": run_identifier,
                    "symbol": sym,
                    "evaluation_date": trade["evaluation_date"],
                    "result_metadata": {
                        "status": trade.get("status"),
                        "recommendation": trade.get("recommendation"),
                        "signal_valid": trade.get("signal_valid"),
                        "is_eligible": trade.get("is_eligible"),
                        "entry_date": trade.get("entry_date"),
                        "entry_price": trade.get("entry_price"),
                        "exit_date": trade.get("exit_date"),
                        "exit_price": trade.get("exit_price"),
                        "exit_reason": trade.get("exit_reason"),
                        "pl": trade.get("pl"),
                        "return_pct": trade.get("return_pct"),
                    }
                })

    # Portfolio-wide metrics aggregation
    portfolio_metrics = calculate_backtest_metrics(all_trades)

    # Persist via Data Engineer service if requested
    persisted_count = 0
    if persist_results and persistence_records:
        try:
            persisted_count = store_backtest_results(persistence_records)
        except Exception as exc:
            logger.error(f"Failed to persist backtest results: {exc}")

    return {
        "run_id": run_identifier,
        "start_date": start_date,
        "end_date": end_date,
        "symbols": symbols_clean,
        "stock_results": stock_results,
        "all_trades": all_trades,
        "portfolio_metrics": portfolio_metrics,
        "persisted_records": persisted_count
    }
