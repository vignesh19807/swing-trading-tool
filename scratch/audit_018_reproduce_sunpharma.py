import os
import sys
import json
import sqlite3
import pandas as pd
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("."))

DB_PATH = Path("docs/audit_artifacts/temp_pilot_audit_018.db").resolve()

import backend.data_pipeline.financial_service as financial_service
import backend.data_pipeline.data_service as data_service
import backend.data_pipeline.classification_service as classification_service
import backend.data_pipeline.backtest_result_service as backtest_svc
from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig
from backend.logic.cost_model import calculate_trade_costs, apply_slippage

patch.object(financial_service, "DATABASE_PATH", DB_PATH).start()
patch.object(data_service, "DATABASE_PATH", DB_PATH).start()
patch.object(classification_service, "DATABASE_PATH", DB_PATH).start()
patch.object(backtest_svc, "DATABASE_PATH", DB_PATH).start()

conn = sqlite3.connect(DB_PATH)

print("=== 1. Historical OHLCV for SUNPHARMA ===")
df_ohlcv = pd.read_sql("""
    SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
    FROM daily_prices dp
    JOIN companies c ON c.id = dp.company_id
    WHERE c.symbol = 'SUNPHARMA' AND dp.date >= '2026-02-25' AND dp.date <= '2026-03-12'
    ORDER BY dp.date ASC
""", conn)
print(df_ohlcv.to_string(index=False))

print("\n=== 2. Eligible Quarterly Financial Data as of 2026-02-27 ===")
df_q = pd.read_sql("""
    SELECT qr.quarter, qr.publication_date,
           qr.revenue, qr.net_profit, qr.operating_margin, qr.roe, qr.roce, qr.debt_equity
    FROM quarterly_results qr
    JOIN companies c ON c.id = qr.company_id
    WHERE c.symbol = 'SUNPHARMA'
    ORDER BY qr.quarter ASC
""", conn)
print(df_q.to_string(index=False))

fin_data = financial_service.get_financial_data("SUNPHARMA", evaluation_date="2026-02-27")
print("\nReturned financial data for SUNPHARMA as of 2026-02-27:")
for k, v in fin_data.items():
    if k != "history":
        print(f"  {k}: {v}")
print("Historical quarters in financial data:", len(fin_data.get("history", [])))

# Load all market data for SUNPHARMA
df_sun_full = pd.read_sql("""
    SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
    FROM daily_prices dp
    JOIN companies c ON c.id = dp.company_id
    WHERE c.symbol = 'SUNPHARMA' AND dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
    ORDER BY dp.date ASC
""", conn)

market_data = {"SUNPHARMA": df_sun_full}

conn.close()

print("\n=== 3. Signal Generation on 2026-02-27 ===")
signal = run_signal_pipeline("SUNPHARMA", evaluation_date="2026-02-27")
print(f"Signal Date: {signal.get('date') or signal.get('evaluation_date')}")
print(f"Action / Recommendation: {signal.get('action') or signal.get('recommendation')}")
print(f"Signal Dict Keys: {list(signal.keys())}")
if "risk_reward" in signal:
    print(f"Risk/Reward: {signal['risk_reward']}")
if "opportunity_score" in signal:
    print(f"Opportunity Score: {signal['opportunity_score']}")
if "eligibility" in signal:
    print(f"Eligibility: {signal['eligibility']}")

print("\n=== 4. Portfolio Simulation Execution ===")
cfg = PortfolioConfig(
    initial_capital=100000.0,
    max_open_positions=5,
    max_allocation_per_position=0.20
)

sim_res = simulate_portfolio(
    signals=[signal],
    market_data_by_symbol=market_data,
    config=cfg,
    run_id="audit_018_sunpharma_verify"
)

trades = sim_res["closed_trades"]
print(f"Executed Closed Trades Count: {len(trades)}")
if trades:
    t = trades[0]
    print("\nTrade Record Raw Dict:")
    for k, v in t.items():
        print(f"  {k}: {v}")

    print("\n=== 5. Independent Accounting Breakdown ===")
    qty = t["quantity"]
    raw_entry_px = 1712.00 # Open on 2026-03-02
    entry_px = t["entry_price"]
    exit_px = t["exit_price"]
    
    # Cost calculations
    entry_costs = calculate_trade_costs(entry_px, qty, is_buy=True, config=cfg.cost_model)
    exit_costs = calculate_trade_costs(exit_px, qty, is_buy=False, config=cfg.cost_model)
    
    gross_pnl = (exit_px - entry_px) * qty
    total_costs = entry_costs["total_costs"] + exit_costs["total_costs"]
    net_pnl = gross_pnl - total_costs
    
    print(f"Quantity: {qty} shares")
    print(f"Entry Price (with slippage): {entry_px}")
    print(f"Exit Price (with slippage): {exit_px}")
    print(f"Gross P/L: {gross_pnl:.6f}")
    print(f"Entry Costs: {entry_costs}")
    print(f"Exit Costs: {exit_costs}")
    print(f"Total Costs: {total_costs:.6f}")
    print(f"Net P/L: {net_pnl:.6f}")
    print(f"Trade Return: {net_pnl / (entry_px * qty) * 100:.4f}%")
    
    summary = sim_res["portfolio_summary"]
    print("\nPortfolio Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
