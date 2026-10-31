"""
Synthetic Complete Trade Lifecycle Test
======================================
Exercises the complete swing trading pipeline end-to-end with deterministic synthetic fixtures:
1. Raw BUY recommendation
2. Signal eligibility & risk gate
3. Portfolio constraints & whole-share sizing
4. Next-day open entry & entry friction
5. Subsequent price progression & exit execution
6. Cost model (brokerage, STT, NSE, SEBI, stamp duty, GST, slippage)
7. Net realized P/L and portfolio cash/equity reconciliation
8. Multi-table transactional database persistence
9. REST API retrieval of the persisted run & equity curve
"""

import os
import sqlite3
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.app import app
import backend.config as cfg
import backend.data_pipeline.backtest_result_service as brs
from backend.logic.backtest_specification import (
    TradeState,
    ExitReason,
    PortfolioConfig,
    CostModelConfig,
    EndOfTestPolicy,
    create_trade_record,
)
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.cost_model import calculate_trade_costs, apply_slippage
from backend.data_pipeline.backtest_result_service import (
    store_portfolio_backtest_run,
    get_backtest_run,
    get_backtest_equity_curve,
    initialize_backtest_results_table,
    get_connection,
)


@pytest.fixture
def test_client():
    return TestClient(app)


def test_complete_synthetic_trade_lifecycle_and_api_retrieval(test_client, tmp_path, monkeypatch):
    run_id = "synthetic_audit_010_complete_run"
    initial_cash = 100000.0

    # 0. Strict Database Isolation via Temporary Database
    test_db = tmp_path / "test_synthetic_backtest.db"
    sqlite3.connect(test_db).close()

    monkeypatch.setattr(brs, "DATABASE_PATH", test_db)
    monkeypatch.setattr(cfg, "DATABASE_PATH", test_db)
    monkeypatch.setattr("backend.app.DATABASE_PATH", test_db)
    initialize_backtest_results_table()

    # 1. Deterministic Synthetic Market Data (INFY-like stock)
    # Days:
    # 2026-01-01: Signal generation date
    # 2026-01-02: Next-day Entry session (Open = 1000.0, Low = 995.0, High = 1020.0, Close = 1015.0)
    # 2026-01-05: Exit session hitting target (Open = 1020.0, High = 1060.0, Low = 1015.0, Close = 1055.0)
    market_df = pd.DataFrame([
        {"date": "2026-01-01", "open": 990.0, "high": 1005.0, "low": 985.0, "close": 1000.0, "volume": 1000000},
        {"date": "2026-01-02", "open": 1000.0, "high": 1020.0, "low": 995.0, "close": 1015.0, "volume": 1200000},
        {"date": "2026-01-05", "open": 1020.0, "high": 1060.0, "low": 1015.0, "close": 1055.0, "volume": 1500000},
    ])

    # 2. Synthetic Eligible Signal on 2026-01-01
    signals = [{
        "symbol": "SYNTH_STOCK",
        "evaluation_date": "2026-01-01",
        "recommendation": "BUY",
        "signal_valid": True,
        "is_eligible": True,
        "opportunity_score": 85.0,
        "stop_loss": 960.0,
        "target": 1050.0,
        "risk": 40.0,
        "reward": 50.0,
        "risk_reward_ratio": 1.25,
        "trade_quality": {"is_eligible": True, "trade_score": 85.0}
    }]

    # 3. Portfolio Config
    cost_cfg = CostModelConfig(
        brokerage_pct=0.0,
        brokerage_flat=0.0,
        stt_rate_buy=0.001,
        stt_rate_sell=0.001,
        exchange_rate=0.0000297,
        sebi_rate=0.000001,
        stamp_duty_buy=0.00015,
        stamp_duty_sell=0.0,
        gst_rate=0.18,
        slippage_pct=0.0005
    )
    p_cfg = PortfolioConfig(
        initial_capital=initial_cash,
        max_open_positions=5,
        max_allocation_per_position=0.20,
        end_of_backtest_policy=EndOfTestPolicy.MARK_TO_MARKET,
        cost_model=cost_cfg,
        enable_costs=True
    )

    # 4. Execute Portfolio Simulation
    sim_res = simulate_portfolio(
        signals=signals,
        market_data_by_symbol={"SYNTH_STOCK": market_df},
        config=p_cfg,
        run_id=run_id
    )

    # 5. Verify Trade Execution & Sizing
    assert len(sim_res["closed_trades"]) == 1
    trade = sim_res["closed_trades"][0]

    # Entry price with slippage: 1000.0 * 1.0005 = 1000.50
    assert trade["entry_price"] == 1000.50
    assert trade["entry_date"] == "2026-01-02"

    # Allocation limit: 20% of ₹100,000 = ₹20,000
    # Quantity: floor(20,000 / 1000.50) = 19 shares
    assert trade["quantity"] == 19
    assert trade["initial_value"] == round(19 * 1000.50, 4)

    # Exit price with slippage: target 1050.0 * (1 - 0.0005) = 1049.475
    assert trade["exit_price"] == 1049.475
    assert trade["exit_date"] == "2026-01-05"
    assert trade["exit_reason"] == ExitReason.TARGET_REACHED

    # Cost calculations: exact hand-calculation reconciliation
    entry_costs = trade["entry_costs"]
    exit_costs = trade["exit_costs"]
    total_costs = trade["total_costs"]
    assert entry_costs == 22.5495
    assert exit_costs == 20.6623
    assert total_costs == 43.2118
    assert total_costs == round(entry_costs + exit_costs, 4)

    # Gross & Net P/L: exact hand-calculation reconciliation
    gross_pl = trade["gross_pl"]
    net_pl = trade["net_pl"]
    assert gross_pl == 930.525
    assert net_pl == 887.3132
    assert net_pl == round(gross_pl - total_costs, 4)

    # Portfolio Cash & Equity Reconciliation
    summary = sim_res["portfolio_summary"]
    assert summary["total_gross_pl"] == 930.525
    assert summary["total_costs"] == 43.2118
    assert summary["total_net_pl"] == 887.3132
    assert round(summary["final_cash"], 2) == 100887.31
    assert round(summary["final_equity"], 2) == 100887.31

    # 6. Transactional Persistence Verification
    store_portfolio_backtest_run(
        run_id=run_id,
        strategy_version="SYNTHETIC_V1",
        start_date="2026-01-01",
        end_date="2026-01-05",
        initial_capital=initial_cash,
        config={"enable_costs": True},
        metrics={
            "total_trades": 1,
            "closed_trades": 1,
            "win_rate": 100.0,
            "net_pl": net_pl,
            "total_return_pct": round((net_pl / initial_cash) * 100.0, 4)
        },
        trades=sim_res["all_trades"],
        equity_curve=sim_res["equity_curve"],
        overwrite=True
    )

    # 7. Read Back & Verify Database Integrity
    persisted_run = get_backtest_run(run_id)
    assert persisted_run is not None
    assert persisted_run["run_id"] == run_id
    assert persisted_run["strategy_version"] == "SYNTHETIC_V1"

    persisted_curve = get_backtest_equity_curve(run_id)
    assert len(persisted_curve) == 3

    # 8. API Retrieval Endpoint Verification
    resp = test_client.get("/api/backtests/latest")
    assert resp.status_code == 200
    api_data = resp.json()
    assert api_data["run_id"] == run_id
    assert api_data["status"] in ("VALID", "COMPLETED")
    total_tr = api_data["metrics"]["total_trades"] if "metrics" in api_data else api_data["total_trades"]
    assert total_tr == 1

    # Clean up test run from database to maintain zero production contamination
    conn = get_connection()
    try:
        conn.execute("DELETE FROM backtest_runs WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM backtest_trades WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM backtest_equity_curve WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM backtest_results WHERE run_id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()
