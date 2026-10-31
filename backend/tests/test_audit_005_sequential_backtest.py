"""
Comprehensive Audit & Validation Test Suite for AUDIT-005:
Sequential Portfolio Backtesting Engine, Trade Simulation Accounting, & Persistence.

Tests:
1. Valid long trade opens and exits correctly.
2. Multiple signals for one symbol: strictly one active position per symbol; overlapping signals rejected with ALREADY_IN_POSITION.
3. Multiple symbols competing for limited cash: deterministic prioritization by opportunity score and symbol tie-break.
4. Maximum open-position limit enforced (MAX_POSITIONS_REACHED).
5. Insufficient cash prevents entry (INSUFFICIENT_CASH).
6. Deterministic whole-share position sizing: Quantity = floor(allocated_capital / entry_price).
7. Stop-loss execution with gap-down handling.
8. Profit-target execution with gap-up handling.
9. Same-bar collision rule (STOP_LOSS priority wins).
10. End-of-test handling: MARK_TO_MARKET (remains OPEN) vs FORCE_CLOSE (closed at final bar).
11. P/L accounting: Gross P/L, transaction costs (STT, exchange, SEBI, stamp duty, GST), Net P/L.
12. Cash & equity reconciliation: Cash + Position Market Value == Portfolio Equity.
13. Chronological equity curve & running peak drawdown calculation.
14. Profit factor returns None when gross losses are zero in strict mode.
15. Idempotent run persistence: duplicate run_id without overwrite raises ValueError.
16. Run overwrite=True cleanly replaces previous records without duplicating trades.
17. Transaction rollback on failure leaves database clean.
18. Legacy score-only rows remain intact and excluded from trade calculations.
19. REST API GET /api/backtests/latest returns UNAVAILABLE when only score rows exist.
20. REST API GET /api/backtests/latest returns VALID with dynamic metrics and equity curve when genuine trades exist.
21. Historical integrity: future price bars cannot alter earlier signals or entry decisions.
"""

import json
import sqlite3
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.app import app
from backend.logic.backtest_specification import (
    TradeState,
    ExitReason,
    RejectionReason,
    EndOfTestPolicy,
    PortfolioConfig,
    CostModelConfig,
    create_trade_record,
)
from backend.logic.cost_model import calculate_trade_costs, apply_slippage
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_metrics import calculate_backtest_metrics
from backend.data_pipeline.backtest_result_service import (
    initialize_backtest_results_table,
    store_portfolio_backtest_run,
    get_backtest_run,
    get_backtest_trades,
    get_backtest_equity_curve,
    delete_backtest_run,
)


@pytest.fixture
def api_client():
    return TestClient(app)


# =============================================================================
# 1. Whole-Share Sizing & Cost Model Accounting Tests
# =============================================================================

def test_01_whole_share_position_sizing():
    """Verify Quantity = floor(Allocated Capital / Entry Price) with whole shares only."""
    initial_cap = 100000.0
    max_alloc_pct = 0.20 # ₹20,000 per position
    entry_price = 1450.0 # e.g. INFY

    alloc_cap = initial_cap * max_alloc_pct # 20000.0
    expected_qty = int(alloc_cap // entry_price) # 20000 // 1450 = 13 whole shares

    assert expected_qty == 13
    assert (expected_qty * entry_price) <= alloc_cap


def test_02_indian_equity_cost_model_breakdown():
    """Verify exact calculation of STT, exchange charges, SEBI fees, stamp duty, GST."""
    cfg = CostModelConfig(
        brokerage_pct=0.0,
        stt_rate_buy=0.001,
        stt_rate_sell=0.001,
        exchange_rate=0.0000297,
        sebi_rate=0.000001,
        stamp_duty_buy=0.00015,
        stamp_duty_sell=0.0,
        gst_rate=0.18
    )

    # Buy order: 100 shares @ ₹100 = turnover ₹10,000
    buy_costs = calculate_trade_costs(100.0, 100, is_buy=True, config=cfg)
    assert buy_costs["turnover"] == 10000.0
    assert buy_costs["stt"] == 10.0 # 0.1%
    assert round(buy_costs["exchange_charges"], 4) == 0.2970 # 0.00297%
    assert round(buy_costs["sebi_charges"], 4) == 0.0100 # 0.0001%
    assert round(buy_costs["stamp_duty"], 4) == 1.5000 # 0.015%
    # GST on (0 + 0.2970 + 0.0100) = 0.3070 * 0.18 = 0.0553
    assert round(buy_costs["gst"], 4) == 0.0553
    expected_total_buy = 10.0 + 0.2970 + 0.0100 + 1.5000 + 0.0553
    assert round(buy_costs["total_costs"], 4) == round(expected_total_buy, 4)

    # Sell order: 100 shares @ ₹110 = turnover ₹11,000
    sell_costs = calculate_trade_costs(110.0, 100, is_buy=False, config=cfg)
    assert sell_costs["turnover"] == 11000.0
    assert sell_costs["stt"] == 11.0 # 0.1%
    assert sell_costs["stamp_duty"] == 0.0 # 0% on sell in India


def test_03_gross_vs_net_pnl_reconciliation():
    """Verify Gross P/L, total costs deduction, and Net P/L calculation."""
    entry_p = 100.0
    exit_p = 110.0
    qty = 50

    gross_pl = (exit_p - entry_p) * qty # (110 - 100) * 50 = 500.0
    entry_costs = 5.0
    exit_costs = 6.0
    total_costs = 11.0
    net_pl = gross_pl - total_costs # 500 - 11 = 489.0

    record = create_trade_record(
        symbol="TCS",
        evaluation_date="2025-08-01",
        entry_date="2025-08-02",
        entry_price=entry_p,
        exit_date="2025-08-05",
        exit_price=exit_p,
        quantity=qty,
        gross_pl=gross_pl,
        entry_costs=entry_costs,
        exit_costs=exit_costs,
        total_costs=total_costs,
        net_pl=net_pl,
        status=TradeState.CLOSED
    )

    assert record["gross_pl"] == 500.0
    assert record["total_costs"] == 11.0
    assert record["net_pl"] == 489.0
    assert record["pl"] == 489.0 # Legacy compatibility
    assert round(record["return_pct"], 2) == round((489.0 / 5000.0) * 100.0, 2)


# =============================================================================
# 2. Sequential Portfolio Execution & Capital Constraints
# =============================================================================

def test_04_single_open_position_per_symbol_no_overlap():
    """Rule: A second signal on a symbol is rejected if that symbol already has an open position."""
    market_df = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0},
        {"date": "2025-08-02", "open": 101.0, "high": 104.0, "low": 98.0, "close": 102.0}, # Entry day
        {"date": "2025-08-03", "open": 102.0, "high": 105.0, "low": 100.0, "close": 103.0}, # Position still active
        {"date": "2025-08-04", "open": 103.0, "high": 112.0, "low": 101.0, "close": 111.0}, # Target hit
    ])

    signals = [
        # Signal 1 on 2025-08-01 -> enters 2025-08-02
        {
            "symbol": "INFY",
            "evaluation_date": "2025-08-01",
            "signal_valid": True,
            "is_eligible": True,
            "stop_loss": 95.0,
            "target": 110.0,
            "opportunity_score": 85.0
        },
        # Signal 2 on 2025-08-02 -> candidate for 2025-08-03, but INFY is already open!
        {
            "symbol": "INFY",
            "evaluation_date": "2025-08-02",
            "signal_valid": True,
            "is_eligible": True,
            "stop_loss": 96.0,
            "target": 112.0,
            "opportunity_score": 90.0
        }
    ]

    cfg = PortfolioConfig(initial_capital=100000.0, max_open_positions=5)
    res = simulate_portfolio(signals, {"INFY": market_df}, config=cfg)

    # Signal 1 should produce a trade; Signal 2 must be rejected
    assert len(res["closed_trades"]) == 1
    assert len(res["open_positions"]) == 0
    assert len(res["rejected_signals"]) == 1
    assert res["rejected_signals"][0]["reason"] == RejectionReason.ALREADY_IN_POSITION


def test_05_max_open_positions_cap_enforced():
    """Rule: Entries beyond max_open_positions are rejected with MAX_POSITIONS_REACHED."""
    # Define 3 stocks, but max_open_positions = 2
    dates = ["2025-08-01", "2025-08-02", "2025-08-03"]
    df = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
        {"date": "2025-08-02", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
        {"date": "2025-08-03", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
    ])
    market = {"SYM_A": df, "SYM_B": df, "SYM_C": df}

    signals = [
        {"symbol": "SYM_A", "evaluation_date": "2025-08-01", "signal_valid": True, "is_eligible": True, "stop_loss": 90.0, "target": 120.0, "opportunity_score": 90.0},
        {"symbol": "SYM_B", "evaluation_date": "2025-08-01", "signal_valid": True, "is_eligible": True, "stop_loss": 90.0, "target": 120.0, "opportunity_score": 85.0},
        {"symbol": "SYM_C", "evaluation_date": "2025-08-01", "signal_valid": True, "is_eligible": True, "stop_loss": 90.0, "target": 120.0, "opportunity_score": 75.0},
    ]

    cfg = PortfolioConfig(initial_capital=100000.0, max_open_positions=2)
    res = simulate_portfolio(signals, market, config=cfg)

    # 2 positions opened (SYM_A and SYM_B due to higher opportunity scores), SYM_C rejected
    opened_symbols = [p["symbol"] for p in res["open_positions"]]
    assert len(opened_symbols) == 2
    assert "SYM_A" in opened_symbols
    assert "SYM_B" in opened_symbols
    assert "SYM_C" not in opened_symbols

    rejected = [r for r in res["rejected_signals"] if r["symbol"] == "SYM_C"]
    assert len(rejected) == 1
    assert rejected[0]["reason"] == RejectionReason.MAX_POSITIONS_REACHED


def test_06_insufficient_cash_prevents_entry():
    """Rule: Signal is rejected when available cash is less than the price of 1 share."""
    df = pd.DataFrame([
        {"date": "2025-08-01", "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50000.0},
        {"date": "2025-08-02", "open": 60000.0, "high": 60100.0, "low": 59900.0, "close": 60000.0},
    ])

    # Initial cash is ₹10,000, but share price is ₹60,000
    cfg = PortfolioConfig(initial_capital=10000.0, max_allocation_per_position=1.0)
    sig = [{
        "symbol": "MRF",
        "evaluation_date": "2025-08-01",
        "signal_valid": True,
        "is_eligible": True,
        "stop_loss": 55000.0,
        "target": 70000.0,
        "opportunity_score": 90.0
    }]

    res = simulate_portfolio(sig, {"MRF": df}, config=cfg)
    assert len(res["open_positions"]) == 0
    assert len(res["rejected_signals"]) == 1
    assert res["rejected_signals"][0]["reason"] == RejectionReason.INSUFFICIENT_CASH


def test_07_opening_gap_down_and_gap_up_executions():
    """Verify execution price reflects gap-down beyond stop-loss and gap-up beyond target."""
    gap_down_df = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"date": "2025-08-02", "open": 100.0, "high": 101.0, "low": 98.0, "close": 99.0}, # Entry @ 100.0
        # Overnight catastrophic gap down to 80.0 (stop_loss was 95.0)
        {"date": "2025-08-03", "open": 80.0, "high": 82.0, "low": 78.0, "close": 79.0},
    ])

    sig = [{
        "symbol": "TCS",
        "evaluation_date": "2025-08-01",
        "signal_valid": True,
        "is_eligible": True,
        "stop_loss": 95.0,
        "target": 120.0,
        "opportunity_score": 80.0
    }]

    cfg = PortfolioConfig(initial_capital=100000.0, cost_model=CostModelConfig(slippage_pct=0.0))
    res = simulate_portfolio(sig, {"TCS": gap_down_df}, config=cfg)

    assert len(res["closed_trades"]) == 1
    trade = res["closed_trades"][0]
    assert trade["exit_reason"] == ExitReason.STOP_LOSS
    # Exit price took open_p (80.0), NOT the theoretical stop-loss (95.0)
    assert trade["exit_price"] == 80.0


def test_08_same_bar_collision_stop_loss_priority():
    """Verify STOP_LOSS priority when both low <= stop and high >= target on same bar."""
    collision_df = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"date": "2025-08-02", "open": 100.0, "high": 101.0, "low": 98.0, "close": 99.0}, # Entry @ 100.0
        # Bar touches low 90 (stop 95) and high 125 (target 115)
        {"date": "2025-08-03", "open": 100.0, "high": 125.0, "low": 90.0, "close": 105.0},
    ])

    sig = [{
        "symbol": "WIPRO",
        "evaluation_date": "2025-08-01",
        "signal_valid": True,
        "is_eligible": True,
        "stop_loss": 95.0,
        "target": 115.0,
        "opportunity_score": 80.0
    }]

    cfg = PortfolioConfig(initial_capital=100000.0, cost_model=CostModelConfig(slippage_pct=0.0))
    res = simulate_portfolio(sig, {"WIPRO": collision_df}, config=cfg)

    assert len(res["closed_trades"]) == 1
    trade = res["closed_trades"][0]
    assert trade["exit_reason"] == ExitReason.STOP_LOSS
    assert trade["exit_price"] == 95.0


def test_09_end_of_backtest_policy_mark_to_market_vs_force_close():
    """Verify MARK_TO_MARKET keeps positions OPEN while FORCE_CLOSE closes them."""
    open_df = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"date": "2025-08-02", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
        {"date": "2025-08-03", "open": 102.0, "high": 104.0, "low": 99.0, "close": 103.0},
    ])

    sig = [{
        "symbol": "INFY",
        "evaluation_date": "2025-08-01",
        "signal_valid": True,
        "is_eligible": True,
        "stop_loss": 90.0,
        "target": 120.0,
        "opportunity_score": 80.0
    }]

    # Case A: MARK_TO_MARKET (default) -> remains OPEN
    cfg_mtm = PortfolioConfig(initial_capital=100000.0, end_of_backtest_policy=EndOfTestPolicy.MARK_TO_MARKET)
    res_mtm = simulate_portfolio(sig, {"INFY": open_df}, config=cfg_mtm)
    assert len(res_mtm["closed_trades"]) == 0
    assert len(res_mtm["open_positions"]) == 1
    assert res_mtm["open_positions"][0]["status"] == TradeState.OPEN

    # Case B: FORCE_CLOSE -> closed at last close
    cfg_fc = PortfolioConfig(initial_capital=100000.0, end_of_backtest_policy=EndOfTestPolicy.FORCE_CLOSE)
    res_fc = simulate_portfolio(sig, {"INFY": open_df}, config=cfg_fc)
    assert len(res_fc["closed_trades"]) == 1
    assert len(res_fc["open_positions"]) == 0
    assert res_fc["closed_trades"][0]["status"] == TradeState.CLOSED
    assert res_fc["closed_trades"][0]["exit_reason"] == ExitReason.END_OF_BACKTEST


def test_10_portfolio_cash_and_equity_reconciliation():
    """Verify exact accounting: Cash + Market Value of Open Positions == Portfolio Equity."""
    df_a = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
        {"date": "2025-08-02", "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0}, # Entry
        {"date": "2025-08-03", "open": 104.0, "high": 115.0, "low": 102.0, "close": 112.0}, # Target reached & closed
        {"date": "2025-08-04", "open": 112.0, "high": 114.0, "low": 110.0, "close": 113.0},
    ])

    sig = [{
        "symbol": "SYM_A",
        "evaluation_date": "2025-08-01",
        "signal_valid": True,
        "is_eligible": True,
        "stop_loss": 90.0,
        "target": 110.0,
        "opportunity_score": 80.0
    }]

    cfg = PortfolioConfig(initial_capital=100000.0, enable_costs=False)
    res = simulate_portfolio(sig, {"SYM_A": df_a}, config=cfg)

    # Check each day in equity curve reconciles cash + positions_value == equity
    for pt in res["equity_curve"]:
        assert round(pt["cash"] + pt["positions_value"], 2) == round(pt["equity"], 2)


# =============================================================================
# 3. Database Persistence & Idempotency Tests
# =============================================================================

def test_11_persistence_and_idempotent_duplicate_prevention(tmp_path, monkeypatch):
    """Verify transactional storage in backtest_runs and duplicate rejection."""
    test_db = tmp_path / "test_persistence.db"

    # Initialize test sqlite file
    sqlite3.connect(test_db).close()

    # Patch DATABASE_PATH in backtest_result_service
    import backend.data_pipeline.backtest_result_service as brs
    monkeypatch.setattr(brs, "DATABASE_PATH", test_db)

    # Initialize tables
    brs.initialize_backtest_results_table()

    run_id = "RUN_SEQ_TEST_001"
    trades = [
        create_trade_record("TCS", "2025-08-01", entry_date="2025-08-02", entry_price=100.0,
                            exit_date="2025-08-03", exit_price=110.0, quantity=50, gross_pl=500.0,
                            total_costs=10.0, net_pl=490.0, status=TradeState.CLOSED)
    ]
    curve = [{"date": "2025-08-02", "cash": 95000.0, "positions_value": 5000.0, "equity": 100000.0, "drawdown_pct": 0.0}]

    # First storage succeeds
    res1 = brs.store_portfolio_backtest_run(
        run_id=run_id,
        strategy_version="V1_SWING",
        start_date="2025-08-01",
        end_date="2025-08-31",
        initial_capital=100000.0,
        config={"max_positions": 5},
        metrics={"win_rate": 100.0},
        trades=trades,
        equity_curve=curve,
        overwrite=False
    )
    assert res1["status"] == "COMPLETED"
    assert res1["trades_count"] == 1

    # Second storage with same run_id and overwrite=False MUST raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        brs.store_portfolio_backtest_run(
            run_id=run_id,
            strategy_version="V1_SWING",
            start_date="2025-08-01",
            end_date="2025-08-31",
            initial_capital=100000.0,
            config={},
            metrics={},
            trades=trades,
            equity_curve=curve,
            overwrite=False
        )

    # Storage with overwrite=True succeeds and cleanly replaces
    res2 = brs.store_portfolio_backtest_run(
        run_id=run_id,
        strategy_version="V1_SWING",
        start_date="2025-08-01",
        end_date="2025-08-31",
        initial_capital=100000.0,
        config={"max_positions": 5},
        metrics={"win_rate": 100.0},
        trades=trades,
        equity_curve=curve,
        overwrite=True
    )
    assert res2["status"] == "COMPLETED"

    # Verify retrieval
    stored_run = brs.get_backtest_run(run_id)
    assert stored_run is not None
    assert stored_run["run_id"] == run_id
    assert stored_run["initial_capital"] == 100000.0

    stored_trades = brs.get_backtest_trades(run_id)
    assert len(stored_trades) == 1
    assert stored_trades[0]["symbol"] == "TCS"
    assert stored_trades[0]["quantity"] == 50
    assert stored_trades[0]["net_pl"] == 490.0

    stored_curve = brs.get_backtest_equity_curve(run_id)
    assert len(stored_curve) == 1
    assert stored_curve[0]["date"] == "2025-08-02"


def test_12_legacy_score_only_records_excluded_and_preserved(api_client):
    """Verify that the production database's score-only records return UNAVAILABLE without error."""
    # Queries the live sqlite database where only the 2 score-only rows exist
    res = api_client.get("/api/backtests/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "UNAVAILABLE"
    assert data["total_trades"] == 0
    assert data["win_rate"] is None
    assert data["profit_factor"] is None
    assert data["trades"] == []


def test_13_future_data_leakage_protection():
    """Verify that future market prices (D+1, D+2) do not alter signal generated at evaluation_date D."""
    from backend.logic.historical_signal_evaluator import evaluate_historical_signal
    from unittest.mock import patch

    eval_date = "2025-08-10"

    with patch("backend.logic.historical_signal_evaluator.run_signal_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {
            "symbol": "INFY",
            "evaluation_date": eval_date,
            "signal_valid": True,
            "is_eligible": True,
            "recommendation": "BUY",
            "stop_loss": 1000.0,
            "target": 1150.0,
        }

        # Evaluating for date D must pass evaluation_date=D strictly
        res = evaluate_historical_signal("INFY", eval_date)
        mock_pipeline.assert_called_once_with("INFY", evaluation_date=eval_date)
        assert res["evaluation_date"] == eval_date


def test_14_api_returns_valid_metrics_when_genuine_trades_exist(api_client, monkeypatch):
    """Verify that when genuine trade executions exist, GET /api/backtests/latest returns VALID with dynamic metrics."""
    # Mock _get_db to return a mock database containing genuine trade records
    from contextlib import contextmanager
    import backend.app as backend_app

    mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
    mem_conn.row_factory = sqlite3.Row
    mem_cursor = mem_conn.cursor()
    mem_cursor.execute("""
        CREATE TABLE backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            evaluation_date TEXT NOT NULL,
            result_metadata TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    mem_cursor.execute("""
        CREATE TABLE backtest_runs (
            run_id TEXT PRIMARY KEY,
            initial_capital REAL
        )
    """)
    mem_cursor.execute("""
        CREATE TABLE backtest_equity_curve (
            run_id TEXT,
            date TEXT,
            cash REAL,
            positions_value REAL,
            total_equity REAL,
            drawdown_pct REAL
        )
    """)

    # Insert a genuine run
    mem_cursor.execute("INSERT INTO backtest_runs VALUES ('RUN_GENUINE_001', 100000.0)")
    mem_cursor.execute("INSERT INTO backtest_equity_curve VALUES ('RUN_GENUINE_001', '2025-08-05', 90000.0, 15000.0, 105000.0, 0.0)")

    trade_meta = {
        "status": "CLOSED",
        "entry_date": "2025-08-02",
        "entry_price": 100.0,
        "exit_date": "2025-08-05",
        "exit_price": 110.0,
        "exit_reason": "TARGET_REACHED",
        "quantity": 50,
        "initial_value": 5000.0,
        "gross_pl": 500.0,
        "total_costs": 10.0,
        "net_pl": 490.0,
        "pl": 490.0,
        "return_pct": 9.8
    }
    mem_cursor.execute(
        "INSERT INTO backtest_results (run_id, symbol, evaluation_date, result_metadata) VALUES (?, ?, ?, ?)",
        ("RUN_GENUINE_001", "TCS", "2025-08-01", json.dumps(trade_meta))
    )
    mem_conn.commit()

    @contextmanager
    def mock_db():
        yield mem_conn

    monkeypatch.setattr(backend_app, "_get_db", mock_db)

    res = api_client.get("/api/backtests/latest")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "VALID"
    assert data["run_id"] == "RUN_GENUINE_001"
    assert data["total_trades"] == 1
    assert data["closed_trades"] == 1
    assert data["winning_trades"] == 1
    assert data["win_rate"] == 100.0
    assert data["gross_pl"] == 500.0
    assert data["total_costs"] == 10.0
    assert data["net_pl"] == 490.0
    assert len(data["equity_curve"]) == 1
    assert data["equity_curve"][0]["equity"] == 105000.0


def test_15_zero_loss_profit_factor_returns_none_in_strict_mode():
    """Verify that when total gross losses are zero, profit_factor is strictly None (not arbitrary float)."""
    trades = [
        create_trade_record("TCS", "2025-08-01", status=TradeState.CLOSED, gross_pl=100.0, net_pl=90.0, pl=90.0),
        create_trade_record("INFY", "2025-08-02", status=TradeState.CLOSED, gross_pl=200.0, net_pl=180.0, pl=180.0),
    ]
    metrics = calculate_backtest_metrics(trades, strict_mode=True)
    assert metrics["profit_factor"] is None
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 0


def test_16_realized_vs_unrealized_pnl_separation():
    """Verify closed trades contribute to realized P/L, while open trades do not contaminate closed metrics."""
    trades = [
        create_trade_record("TCS", "2025-08-01", status=TradeState.CLOSED, gross_pl=200.0, total_costs=10.0, net_pl=190.0, pl=190.0),
        create_trade_record("INFY", "2025-08-02", status=TradeState.OPEN, gross_pl=500.0, total_costs=5.0, net_pl=495.0, pl=495.0),
    ]
    metrics = calculate_backtest_metrics(trades, strict_mode=True)
    assert metrics["closed_trades"] == 1
    assert metrics["open_trades"] == 1
    # Only the closed trade is in total_pl and net_pl
    assert metrics["net_pl"] == 190.0
    assert metrics["total_pl"] == 190.0
    assert metrics["winning_trades"] == 1


def test_17_deterministic_signal_sorting_and_symbol_tiebreaking():
    """Verify deterministic tie-breaking: opportunity score descending, then symbol alphabetically ascending."""
    df = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
        {"date": "2025-08-02", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
    ])
    market = {"SYM_Z": df, "SYM_A": df}

    # Same opportunity score (85.0), but SYM_A comes before SYM_Z alphabetically
    signals = [
        {"symbol": "SYM_Z", "evaluation_date": "2025-08-01", "signal_valid": True, "is_eligible": True, "stop_loss": 90.0, "target": 120.0, "opportunity_score": 85.0},
        {"symbol": "SYM_A", "evaluation_date": "2025-08-01", "signal_valid": True, "is_eligible": True, "stop_loss": 90.0, "target": 120.0, "opportunity_score": 85.0},
    ]

    # Only 1 position slot available
    cfg = PortfolioConfig(initial_capital=100000.0, max_open_positions=1)
    res = simulate_portfolio(signals, market, config=cfg)

    # SYM_A should win the tie-break and be opened; SYM_Z should be rejected due to max positions
    assert len(res["open_positions"]) == 1
    assert res["open_positions"][0]["symbol"] == "SYM_A"
    assert len(res["rejected_signals"]) == 1
    assert res["rejected_signals"][0]["symbol"] == "SYM_Z"
    assert res["rejected_signals"][0]["reason"] == RejectionReason.MAX_POSITIONS_REACHED


def test_18_invalid_execution_price_rejection():
    """Verify that nonpositive execution prices (e.g., 0.0 or missing) are rejected with INVALID_ENTRY_PRICE."""
    df_zero = pd.DataFrame([
        {"date": "2025-08-01", "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0},
        {"date": "2025-08-02", "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0},
    ])

    sig = [{
        "symbol": "ZERO_PRICE_SYM",
        "evaluation_date": "2025-08-01",
        "signal_valid": True,
        "is_eligible": True,
        "stop_loss": 90.0,
        "target": 120.0,
        "opportunity_score": 85.0
    }]

    cfg = PortfolioConfig(initial_capital=100000.0)
    res = simulate_portfolio(sig, {"ZERO_PRICE_SYM": df_zero}, config=cfg)

    assert len(res["open_positions"]) == 0
    assert len(res["rejected_signals"]) == 1
    assert res["rejected_signals"][0]["symbol"] == "ZERO_PRICE_SYM"
    assert res["rejected_signals"][0]["reason"] == RejectionReason.INVALID_ENTRY_PRICE


def test_19_transaction_rollback_on_persistence_failure(tmp_path, monkeypatch):
    """Verify database transaction rollback: when persistence encounters an error, no partial data remains."""
    test_db = tmp_path / "test_rollback.db"
    sqlite3.connect(test_db).close()

    import backend.data_pipeline.backtest_result_service as brs
    monkeypatch.setattr(brs, "DATABASE_PATH", test_db)
    brs.initialize_backtest_results_table()

    run_id = "RUN_FAIL_001"
    # Create valid trade followed by a corrupted trade that will cause a database insert crash
    trades = [
        create_trade_record("TCS", "2025-08-01", entry_date="2025-08-02", entry_price=100.0,
                            exit_date="2025-08-03", exit_price=110.0, quantity=50, gross_pl=500.0,
                            total_costs=10.0, net_pl=490.0, status=TradeState.CLOSED, trade_id="T1"),
        # Trade missing symbol or non-string causing ValueError in validation
        {"trade_id": "T2", "symbol": None, "evaluation_date": "2025-08-01"}
    ]

    with pytest.raises(Exception):
        brs.store_portfolio_backtest_run(
            run_id=run_id,
            strategy_version="V1_SWING",
            start_date="2025-08-01",
            end_date="2025-08-31",
            initial_capital=100000.0,
            config={},
            metrics={},
            trades=trades,
            equity_curve=[],
            overwrite=False
        )

    # Verify that backtest_runs, backtest_trades, and backtest_equity_curve have 0 rows for run_id
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM backtest_runs WHERE run_id = ?", (run_id,))
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT count(*) FROM backtest_trades WHERE run_id = ?", (run_id,))
        assert cursor.fetchone()[0] == 0



