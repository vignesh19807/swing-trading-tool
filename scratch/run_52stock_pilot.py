"""
AUDIT-017: Phase 5 - Execute controlled 52-stock historical backtest
Runs in manageable batches on isolated temp_pilot_audit_017.db.
"""

import os
import sys
import json
import shutil
import sqlite3
import pandas as pd
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))

PROD_DB = Path("database/swing_trading.db").resolve()
TEMP_DB = Path("docs/audit_artifacts/temp_pilot_audit_017.db").resolve()

# 1. Fresh isolated copy
shutil.copyfile(PROD_DB, TEMP_DB)

import backend.data_pipeline.financial_service as fin_svc
import backend.data_pipeline.data_service as data_svc
import backend.data_pipeline.classification_service as class_svc
import backend.data_pipeline.backtest_result_service as backtest_svc
from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig

# Patch database paths
patch.object(fin_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(data_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(class_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(backtest_svc, "DATABASE_PATH", TEMP_DB).start()

conn = sqlite3.connect(TEMP_DB)
cur = conn.cursor()

# Get 52 symbols
cur.execute("SELECT symbol FROM companies ORDER BY symbol")
symbols = [r[0] for r in cur.fetchall()]

# Get 122 trading dates
cur.execute("""
    SELECT DISTINCT date FROM daily_prices
    WHERE date >= '2025-10-01' AND date <= '2026-03-31'
    ORDER BY date
""")
trading_dates = [r[0] for r in cur.fetchall()]

# Load market data by symbol
print("Loading market data for all 52 stocks...")
market_data_by_symbol = {}
for sym in symbols:
    df = pd.read_sql("""
        SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
        FROM daily_prices dp
        JOIN companies c ON c.id = dp.company_id
        WHERE c.symbol = ? AND dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
        ORDER BY dp.date ASC
    """, conn, params=(sym,))
    market_data_by_symbol[sym] = df

conn.close()

print(f"Total symbols: {len(symbols)}")
print(f"Total trading days: {len(trading_dates)}")
print(f"Total stock-sessions: {len(symbols) * len(trading_dates)}")

# Batch symbols into 5 batches
batch_size = 11
batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
print(f"Batches: {len(batches)}")

all_signals = []
raw_buys = []
eligible_signals = []

start_time = datetime.now()

for batch_idx, batch_syms in enumerate(batches, 1):
    print(f"\n--- Processing Batch {batch_idx}/{len(batches)}: {len(batch_syms)} stocks ---")
    for date_str in trading_dates:
        for sym in batch_syms:
            try:
                sig = run_signal_pipeline(sym, evaluation_date=date_str)
                all_signals.append(sig)
                if sig.get("recommendation") == "BUY":
                    raw_buys.append(sig)
                    print(f"  [RAW BUY] {sym} on {date_str}: eligible={sig.get('is_eligible')} reason={sig.get('reason') or sig.get('trade_quality', {}).get('eligibility_reason')}")
                if sig.get("is_eligible"):
                    eligible_signals.append(sig)
            except Exception as e:
                pass
    print(f"Batch {batch_idx} complete. Cumulative signals: {len(all_signals)}, Raw BUYs: {len(raw_buys)}, Eligible: {len(eligible_signals)}")

elapsed = (datetime.now() - start_time).total_seconds()
print(f"\nSignal generation finished in {elapsed:.1f}s.")
print(f"Total Evaluated Signals: {len(all_signals)}")
print(f"Total Raw BUY Recommendations: {len(raw_buys)}")
print(f"Total Eligible BUY Signals: {len(eligible_signals)}")

# 6. Run Portfolio Simulation
print("\nRunning Portfolio Simulation...")
cfg = PortfolioConfig(
    initial_capital=100000.0,
    max_position_allocation=0.20,
    slippage_pct=0.0005,
    brokerage_pct=0.0003,
    brokerage_cap=20.0,
    stt_pct=0.0010,
    exchange_charges_pct=0.0000345,
    sebi_charges_pct=0.000001,
    stamp_duty_pct=0.00015,
    gst_pct=0.18
)

run_id = "pilot_audit_017_52stock"
sim_res = simulate_portfolio(
    signals=all_signals,
    market_data_by_symbol=market_data_by_symbol,
    config=cfg,
    run_id=run_id
)

portfolio_summary = sim_res["portfolio_summary"]
closed_trades = sim_res["closed_trades"]
open_positions = sim_res["open_positions"]
equity_curve = sim_res["equity_curve"]
rejected_signals = sim_res["rejected_signals"]

print("\n--- Portfolio Simulation Results ---")
print(f"Initial Capital    : INR {portfolio_summary['initial_capital']:,.2f}")
print(f"Final Capital      : INR {portfolio_summary['final_equity']:,.2f}")
print(f"Total Net P/L      : INR {portfolio_summary['total_net_pl']:,.2f}")
print(f"Net Return         : {(portfolio_summary['final_equity'] - portfolio_summary['initial_capital']) / portfolio_summary['initial_capital'] * 100:.2f}%")
print(f"Max Drawdown       : {portfolio_summary['max_drawdown_pct']:.2f}%")
print(f"Closed Trades      : {len(closed_trades)}")
print(f"Open Positions     : {len(open_positions)}")
print(f"Total Costs        : INR {portfolio_summary['total_costs']:,.2f}")

# 7. Persist to isolated database
print(f"\nPersisting run '{run_id}' to {TEMP_DB}...")
run_metadata = {
    "run_id": run_id,
    "strategy_name": "AUDIT_017_52_STOCK_PILOT",
    "symbols": symbols,
    "start_date": "2025-10-01",
    "end_date": "2026-03-31",
    "initial_capital": portfolio_summary["initial_capital"],
    "final_equity": portfolio_summary["final_equity"],
    "total_gross_pl": portfolio_summary["total_gross_pl"],
    "total_costs": portfolio_summary["total_costs"],
    "total_net_pl": portfolio_summary["total_net_pl"],
    "max_drawdown_pct": portfolio_summary["max_drawdown_pct"],
    "total_trades": len(closed_trades) + len(open_positions),
    "win_rate": None,
    "profit_factor": None
}

persist_res = backtest_svc.store_portfolio_backtest_run(
    run_metadata=run_metadata,
    closed_trades=closed_trades,
    equity_curve=equity_curve
)
print("Persistence result:", persist_res)

# Save full results JSON
output_data = {
    "run_id": run_id,
    "total_evaluated_sessions": len(all_signals),
    "total_raw_buys": len(raw_buys),
    "total_eligible_buys": len(eligible_signals),
    "raw_buys_details": raw_buys,
    "portfolio_summary": portfolio_summary,
    "closed_trades": closed_trades,
    "open_positions": open_positions,
    "equity_curve_length": len(equity_curve),
    "persistence_result": persist_res
}

with open("scratch/audit_017_52stock_results.json", "w") as f:
    json.dump(output_data, f, indent=2, default=str)

print("Saved scratch/audit_017_52stock_results.json")

