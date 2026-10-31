"""
Inspect SUNPHARMA trade execution on subsequent bars.
"""

import os
import sys
import sqlite3
import json
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.trade_simulator import simulate_trade
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig

DB_PATH = Path("database/swing_trading.db").resolve()
conn = sqlite3.connect(DB_PATH)

sun_bars = pd.read_sql("""
    SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
    FROM daily_prices dp
    JOIN companies c ON c.id = dp.company_id
    WHERE c.symbol = 'SUNPHARMA' AND dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
    ORDER BY dp.date ASC
""", conn)
conn.close()

sig = run_signal_pipeline("SUNPHARMA", evaluation_date="2026-02-27")
print("Signal:")
print(json.dumps(sig, indent=2))

trade_rec = simulate_trade(sig, sun_bars)
print("\nSimulated Trade Record:")
print(json.dumps(trade_rec, indent=2))

# Now test portfolio simulation
market_dict = {"SUNPHARMA": sun_bars}
cfg = PortfolioConfig(initial_capital=100000.0)
sim_res = simulate_portfolio([sig], market_dict, config=cfg, run_id="test_sunpharma")
print("\nPortfolio Summary:")
print(json.dumps(sim_res["portfolio_summary"], indent=2))
print("\nClosed Trades:")
print(json.dumps(sim_res["closed_trades"], indent=2))
print("\nOpen Positions:")
print(json.dumps(sim_res["open_positions"], indent=2))

