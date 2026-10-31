import os
import sys
import json
import sqlite3
import pandas as pd
from datetime import date
from pathlib import Path
from unittest.mock import patch
from collections import Counter

sys.path.insert(0, os.path.abspath("."))

DB_PATH = Path("docs/audit_artifacts/temp_pilot_audit_018.db").resolve()

import backend.data_pipeline.financial_service as financial_service
import backend.data_pipeline.data_service as data_service
import backend.data_pipeline.classification_service as classification_service
import backend.data_pipeline.backtest_result_service as backtest_svc
from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig

patch.object(financial_service, "DATABASE_PATH", DB_PATH).start()
patch.object(data_service, "DATABASE_PATH", DB_PATH).start()
patch.object(classification_service, "DATABASE_PATH", DB_PATH).start()
patch.object(backtest_svc, "DATABASE_PATH", DB_PATH).start()

conn = sqlite3.connect(DB_PATH)

# Fetch 52 symbols
symbols = [r[0] for r in conn.execute("SELECT symbol FROM companies ORDER BY symbol").fetchall()]
print(f"Total symbols: {len(symbols)}")

# Fetch trading dates between 2025-10-01 and 2026-03-31
trading_dates = [r[0] for r in conn.execute("""
    SELECT DISTINCT date FROM daily_prices 
    WHERE date >= '2025-10-01' AND date <= '2026-03-31'
    ORDER BY date ASC
""").fetchall()]
print(f"Total trading dates: {len(trading_dates)}")

# Market data dictionary
market_data = {}
for sym in symbols:
    df = pd.read_sql("""
        SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
        FROM daily_prices dp
        JOIN companies c ON c.id = dp.company_id
        WHERE c.symbol = ? AND dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
        ORDER BY dp.date ASC
    """, conn, params=(sym,))
    market_data[sym] = df

conn.close()

# Evaluate signals across all 52 stocks and all trading dates
total_sessions = 0
raw_buys = 0
rejection_counter = Counter()
eligible_signals = []
buy_signals_all = []

print("Evaluating 52 stocks across 122 sessions...")
for sym in symbols:
    df_sym = market_data[sym]
    sym_dates = set(df_sym["date"].tolist())
    for dt in trading_dates:
        if dt not in sym_dates:
            continue
        total_sessions += 1
        
        sig = run_signal_pipeline(sym, evaluation_date=dt)
        rec = sig.get("recommendation")
        is_eligible = sig.get("is_eligible", False)
        tq = sig.get("trade_quality", {})
        reason = tq.get("eligibility_reason") or sig.get("reason")
        
        if rec == "BUY":
            raw_buys += 1
            buy_signals_all.append({
                "symbol": sym,
                "date": dt,
                "is_eligible": is_eligible,
                "reason": reason,
                "risk_reward_ratio": sig.get("risk_reward_ratio"),
                "entry_lower": sig.get("entry_lower"),
                "entry_upper": sig.get("entry_upper"),
                "stop_loss": sig.get("stop_loss"),
                "target": sig.get("target")
            })
            if is_eligible:
                eligible_signals.append(sig)
            else:
                rejection_counter[reason] += 1

print("\n=== Evaluation Results ===")
print(f"Total Stocks Evaluated: {len(symbols)}")
print(f"Total Stock Sessions: {total_sessions}")
print(f"Raw BUY Signals: {raw_buys}")
print(f"Eligible BUY Signals: {len(eligible_signals)}")
print(f"Rejected BUY Signals: {sum(rejection_counter.values())}")
print("Rejection Breakdown:")
for r, cnt in rejection_counter.items():
    pct = cnt / (raw_buys - len(eligible_signals)) * 100
    print(f"  {r}: {cnt} ({pct:.2f}%)")

# Run portfolio simulation
cfg = PortfolioConfig(
    initial_capital=100000.0,
    max_open_positions=5,
    max_allocation_per_position=0.20
)

run_id = "audit_018_52stock_reproduction"
sim_res = simulate_portfolio(
    signals=eligible_signals,
    market_data_by_symbol=market_data,
    config=cfg,
    run_id=run_id
)

summary = sim_res["portfolio_summary"]
closed_trades = sim_res["closed_trades"]
open_pos = sim_res["open_positions"]
eq_curve = sim_res["equity_curve"]

print("\n=== Portfolio Simulation Results ===")
for k, v in summary.items():
    print(f"  {k}: {v}")

print(f"Closed Trades Count: {len(closed_trades)}")
print(f"Open Positions Count: {len(open_pos)}")
print(f"Equity Curve Observations: {len(eq_curve)}")

# Persist to temp_pilot_audit_018.db
backtest_svc.store_portfolio_backtest_run(
    run_id=run_id,
    strategy_version="1.0.0-audit-018",
    start_date="2025-10-01",
    end_date="2026-03-31",
    initial_capital=100000.0,
    config=cfg,
    metrics=summary,
    trades=closed_trades,
    equity_curve=eq_curve,
    overwrite=True
)
print("Persisted simulation to temp_pilot_audit_018.db successfully.")

