"""
Week 12 - Backtest Engine (Orchestrator)
========================================

Top-level Backtest Engine orchestrating historical signal evaluation, trade simulation,
performance metrics calculation, and optional persistence via existing Data Engineer services.

Author: Logic Engineer
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.data_pipeline.historical_data_service import get_historical_data
from backend.data_pipeline.backtest_result_service import store_backtest_results
from backend.logic.historical_signal_evaluator import evaluate_historical_signals
from backend.logic.trade_simulator import simulate_trades_for_signals
from backend.logic.backtest_metrics import calculate_backtest_metrics
from backend.logic.backtest_specification import BacktestConfig

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
    eval_dates = market_df["date"].astype(str).tolist()

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


def run_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    run_id: Optional[str] = None,
    persist_results: bool = False
) -> Dict[str, Any]:
    """
    Executes a multi-stock / multi-period historical backtest across a portfolio universe.

    Parameters
    ----------
    symbols : list of str
        List of NSE stock symbols.
    start_date : str
        Evaluation start date (YYYY-MM-DD).
    end_date : str
        Evaluation end date (YYYY-MM-DD).
    run_id : str, optional
        Unique run identifier.
    persist_results : bool
        If True, stores backtest result metadata using Data Engineer backtest_result_service.

    Returns
    -------
    dict
        Comprehensive portfolio backtest result dictionary.
    """
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
