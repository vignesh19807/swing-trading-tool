"""
Regression and verification test suite for AUDIT-002:
Eliminate Hardcoded Backtesting Performance Metrics.

Verifies:
1. No backtest record exists (empty database / table missing).
2. A backtest summary exists but no genuine trades exist (ranking scores only).
3. All eligible closed trades are winners (win_rate = 100.0, profit_factor = None due to zero loss).
4. A mixture of winning, losing, and breakeven trades.
5. Profit factor with both winning and losing trades (gross_profits / gross_losses).
6. Profit factor when gross losses are zero (profit_factor = None, mathematically undefined).
7. No eligible closed trades (e.g. only OPEN trades).
8. Drawdown calculated from a chronological equity curve using running equity peaks.
9. Different trade outcomes produce different calculated metrics (dynamic calculation).
10. Missing, invalid, or inconsistent trade data handled safely.
11. Open trades are excluded from closed-trade metrics.
12. The API returns the correct unavailable status (UNAVAILABLE) and response shape.
"""

import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.app import app, _is_genuine_trade_record
from backend.logic.backtest_metrics import calculate_backtest_metrics
from backend.logic.backtest_specification import TradeState, ExitReason, create_trade_record


@pytest.fixture
def api_client():
    return TestClient(app)


# =============================================================================
# 1. Unit Tests for calculate_backtest_metrics (Strict Mode)
# =============================================================================

def test_01_empty_trades_list():
    """Requirement 1 & 7: Zero trades returns None for undefined metrics under strict_mode."""
    m = calculate_backtest_metrics([], strict_mode=True)
    assert m["total_trades"] == 0
    assert m["closed_trades"] == 0
    assert m["open_trades"] == 0
    assert m["win_rate"] is None
    assert m["profit_factor"] is None
    assert m["max_drawdown_pct"] is None
    assert m["equity_curve"] == []


def test_02_all_open_trades_excluded_from_closed_metrics():
    """Requirement 7 & 11: Open trades are excluded from closed-trade metrics."""
    trades = [
        create_trade_record("TCS", "2025-08-01", status=TradeState.OPEN, entry_price=100.0, pl=5.0, return_pct=5.0),
        create_trade_record("INFY", "2025-08-02", status=TradeState.OPEN, entry_price=200.0, pl=-2.0, return_pct=-1.0),
    ]
    m = calculate_backtest_metrics(trades, strict_mode=True)
    assert m["total_trades"] == 2
    assert m["closed_trades"] == 0
    assert m["open_trades"] == 2
    assert m["winning_trades"] == 0
    assert m["losing_trades"] == 0
    assert m["win_rate"] is None
    assert m["profit_factor"] is None
    assert m["max_drawdown_pct"] is None


def test_03_all_winners_zero_gross_losses():
    """Requirement 3 & 6: All winning trades -> win_rate 100%, profit_factor is None (undefined division by zero)."""
    trades = [
        create_trade_record("TCS", "2025-08-01", exit_date="2025-08-05", status=TradeState.CLOSED, pl=150.0, return_pct=5.0),
        create_trade_record("INFY", "2025-08-02", exit_date="2025-08-06", status=TradeState.CLOSED, pl=250.0, return_pct=8.0),
    ]
    m = calculate_backtest_metrics(trades, strict_mode=True)
    assert m["total_trades"] == 2
    assert m["closed_trades"] == 2
    assert m["winning_trades"] == 2
    assert m["losing_trades"] == 0
    assert m["breakeven_trades"] == 0
    assert m["win_rate"] == 100.0
    # Crucial: profit factor is NOT reported as an arbitrary finite number when losses == 0
    assert m["profit_factor"] is None
    assert m["max_drawdown_pct"] == 0.0


def test_04_mixture_of_winning_losing_and_breakeven_trades():
    """Requirement 4 & 5: Mixture of winners, losers, and breakeven trades."""
    trades = [
        create_trade_record("TCS", "2025-08-01", exit_date="2025-08-03", status=TradeState.CLOSED, pl=100.0, return_pct=10.0),
        create_trade_record("INFY", "2025-08-02", exit_date="2025-08-04", status=TradeState.CLOSED, pl=-50.0, return_pct=-5.0),
        create_trade_record("RELIANCE", "2025-08-03", exit_date="2025-08-05", status=TradeState.CLOSED, pl=0.0, return_pct=0.0),
        create_trade_record("HDFCBANK", "2025-08-04", exit_date="2025-08-06", status=TradeState.OPEN, pl=30.0, return_pct=3.0),
    ]
    m = calculate_backtest_metrics(trades, strict_mode=True)
    assert m["total_trades"] == 4
    assert m["closed_trades"] == 3
    assert m["open_trades"] == 1
    assert m["winning_trades"] == 1
    assert m["losing_trades"] == 1
    assert m["breakeven_trades"] == 1

    # Win rate: 1 winning / 3 eligible closed trades = 33.3333%
    assert round(m["win_rate"], 2) == 33.33

    # Profit factor: gross profits (100) / gross losses (50) = 2.0
    assert m["profit_factor"] == 2.0


def test_05_chronological_equity_curve_and_drawdown():
    """Requirement 8: Drawdown calculated strictly from chronological equity curve using running peaks."""
    # Trades provided out of chronological order to verify chronological sorting
    trades = [
        create_trade_record("TCS", "2025-08-03", exit_date="2025-08-05", status=TradeState.CLOSED, pl=10.0, return_pct=10.0),
        create_trade_record("INFY", "2025-08-01", exit_date="2025-08-02", status=TradeState.CLOSED, pl=20.0, return_pct=20.0),
        create_trade_record("RELIANCE", "2025-08-02", exit_date="2025-08-04", status=TradeState.CLOSED, pl=-15.0, return_pct=-15.0),
    ]
    # Chronological order of exit_date:
    # 1. 2025-08-02: return +20% -> cum 20%, peak 20%, dd 0%
    # 2. 2025-08-04: return -15% -> cum 5%, peak 20%, dd 15%
    # 3. 2025-08-05: return +10% -> cum 15%, peak 20%, dd 5%
    # Max drawdown = 15.0%
    m = calculate_backtest_metrics(trades, strict_mode=True)
    assert m["max_drawdown_pct"] == 15.0
    assert len(m["equity_curve"]) == 3
    assert m["equity_curve"][0]["date"] == "2025-08-02"
    assert m["equity_curve"][0]["drawdown_pct"] == 0.0
    assert m["equity_curve"][1]["date"] == "2025-08-04"
    assert m["equity_curve"][1]["drawdown_pct"] == 15.0
    assert m["equity_curve"][2]["date"] == "2025-08-05"
    assert m["equity_curve"][2]["drawdown_pct"] == 5.0


def test_06_dynamic_outcomes_produce_different_metrics():
    """Requirement 9: Different trade outcomes produce different calculated metrics (not hardcoded)."""
    outcome_a = [
        create_trade_record("TCS", "2025-08-01", exit_date="2025-08-02", status=TradeState.CLOSED, pl=100.0, return_pct=10.0),
        create_trade_record("TCS", "2025-08-02", exit_date="2025-08-03", status=TradeState.CLOSED, pl=-50.0, return_pct=-5.0),
    ]
    outcome_b = [
        create_trade_record("TCS", "2025-08-01", exit_date="2025-08-02", status=TradeState.CLOSED, pl=300.0, return_pct=30.0),
        create_trade_record("TCS", "2025-08-02", exit_date="2025-08-03", status=TradeState.CLOSED, pl=-20.0, return_pct=-2.0),
    ]
    m_a = calculate_backtest_metrics(outcome_a, strict_mode=True)
    m_b = calculate_backtest_metrics(outcome_b, strict_mode=True)

    assert m_a["profit_factor"] == 2.0
    assert m_b["profit_factor"] == 15.0
    assert m_a["total_pl"] == 50.0
    assert m_b["total_pl"] == 280.0
    assert m_a["profit_factor"] != m_b["profit_factor"]


def test_07_missing_invalid_inconsistent_trade_data():
    """Requirement 10: Missing, invalid, or inconsistent trade data handled safely."""
    inconsistent_trades = [
        {"symbol": "TCS"},  # Missing status, pl, dates
        {"status": "INVALID", "pl": None},
        {"status": "CLOSED", "pl": "not_a_number", "return_pct": None},
        None,  # None object
        {},  # Empty dict
    ]
    # Filter out None objects as expected by list input
    cleaned = [t for t in inconsistent_trades if isinstance(t, dict)]
    m = calculate_backtest_metrics(cleaned, strict_mode=True)
    assert m["total_trades"] == len(cleaned)
    assert m["closed_trades"] == 1  # 1 has status CLOSED
    assert m["win_rate"] == 0.0     # 0 winners / 1 closed
    assert m["profit_factor"] is None


# =============================================================================
# 2. API Contract & Database State Tests (FastAPI Client)
# =============================================================================

def test_08_api_production_db_returns_unavailable(api_client):
    """
    Requirement 2 & 12: Production database containing opportunity score records
    (not genuine simulated trades) returns status=UNAVAILABLE with null metrics.
    """
    res = api_client.get("/api/backtests/latest")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "UNAVAILABLE"
    assert "No genuine simulated trade execution records" in data["reason"]
    assert data["total_trades"] == 0
    assert data["win_rate"] is None
    assert data["profit_factor"] is None
    assert data["max_drawdown"] is None
    assert data["trades"] == []
    assert data["equity_curve"] == []


def test_09_api_empty_table_returns_unavailable(api_client, monkeypatch, tmp_path):
    """Requirement 1: When backtest_results table is completely empty, returns UNAVAILABLE."""
    db_file = tmp_path / "empty_backtest.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            evaluation_date TEXT NOT NULL,
            result_metadata TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    def get_test_db():
        c = sqlite3.connect(str(db_file), check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("backend.app._get_db", get_test_db)

    res = api_client.get("/api/backtests/latest")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "UNAVAILABLE"
    assert data["win_rate"] is None
    assert data["profit_factor"] is None
    assert data["max_drawdown"] is None
    assert data["total_trades"] == 0


def test_10_api_genuine_simulated_trades_calculates_dynamically(api_client, monkeypatch, tmp_path):
    """
    Requirement 9 & Case A: When genuine trade execution records exist in the database,
    the API dynamically calculates real performance metrics from executed trades.
    """
    db_file = tmp_path / "genuine_backtest.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            evaluation_date TEXT NOT NULL,
            result_metadata TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert 3 genuine simulated trade executions
    trades_to_insert = [
        {
            "run_id": "RUN_GENUINE_001",
            "symbol": "INFY",
            "date": "2025-08-01",
            "meta": {
                "status": "CLOSED",
                "entry_date": "2025-08-02",
                "entry_price": 1000.0,
                "exit_date": "2025-08-10",
                "exit_price": 1100.0,
                "exit_reason": "TARGET_REACHED",
                "pl": 100.0,
                "return_pct": 10.0
            }
        },
        {
            "run_id": "RUN_GENUINE_001",
            "symbol": "TCS",
            "date": "2025-08-02",
            "meta": {
                "status": "CLOSED",
                "entry_date": "2025-08-03",
                "entry_price": 3000.0,
                "exit_date": "2025-08-12",
                "exit_price": 2850.0,
                "exit_reason": "STOP_LOSS",
                "pl": -150.0,
                "return_pct": -5.0
            }
        },
        {
            "run_id": "RUN_GENUINE_001",
            "symbol": "RELIANCE",
            "date": "2025-08-03",
            "meta": {
                "status": "OPEN",
                "entry_date": "2025-08-04",
                "entry_price": 2500.0,
                "exit_date": None,
                "exit_price": None,
                "exit_reason": "END_OF_BACKTEST",
                "pl": 50.0,
                "return_pct": 2.0
            }
        }
    ]

    for t in trades_to_insert:
        conn.execute(
            "INSERT INTO backtest_results (run_id, symbol, evaluation_date, result_metadata) VALUES (?, ?, ?, ?)",
            (t["run_id"], t["symbol"], t["date"], json.dumps(t["meta"]))
        )
    conn.commit()
    conn.close()

    def get_test_db():
        c = sqlite3.connect(str(db_file), check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("backend.app._get_db", get_test_db)

    res = api_client.get("/api/backtests/latest")
    assert res.status_code == 200
    data = res.json()

    # Must be VALID and calculated from the 3 genuine trades
    assert data["status"] == "VALID"
    assert data["backtest_run_id"] == "RUN_GENUINE_001"
    assert data["total_trades"] == 3
    assert data["closed_trades"] == 2
    assert data["open_trades"] == 1
    assert data["winning_trades"] == 1
    assert data["losing_trades"] == 1

    # Win rate: 1 win / 2 closed = 50.0%
    assert data["win_rate"] == 50.0

    # Profit factor: gross profit 100 / gross loss 150 = 0.6667
    assert round(data["profit_factor"], 4) == 0.6667

    # Max Drawdown from chronological curve:
    # 2025-08-10: +10% -> peak 10%, dd 0%
    # 2025-08-12: -5% -> cum 5%, peak 10%, dd 5%
    # Max DD = 5.0%
    assert data["max_drawdown"] == 5.0
    assert len(data["equity_curve"]) == 2

    # Verify no hardcoded 0.62, 1.85, 0.124
    assert data["win_rate"] != 0.62
    assert data["profit_factor"] != 1.85
    assert data["max_drawdown"] != 0.124


def test_11_is_genuine_trade_record_classifier():
    """Verify classification of genuine trade records vs non-trade score rows."""
    # Score ranking row from database
    score_row = {"score": 60}
    assert _is_genuine_trade_record(score_row) is False

    score_ranking_row = {"score": 80, "rank": 1, "opportunity_score": 85.0}
    assert _is_genuine_trade_record(score_ranking_row) is False

    # Genuine executed trade
    trade_closed = {"status": "CLOSED", "entry_price": 100.0, "exit_price": 110.0, "pl": 10.0}
    assert _is_genuine_trade_record(trade_closed) is True

    trade_open = {"status": "OPEN", "entry_price": 500.0, "entry_date": "2025-08-01"}
    assert _is_genuine_trade_record(trade_open) is True

    # Empty / None
    assert _is_genuine_trade_record({}) is False
    assert _is_genuine_trade_record(None) is False
    assert _is_genuine_trade_record("invalid string") is False
