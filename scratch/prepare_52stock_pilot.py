"""
AUDIT-017: Phase 5 - Prepare 52-stock pilot specification and calculate 52-stock benchmark.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

DB_PATH = Path("database/swing_trading.db").resolve()
conn = sqlite3.connect(DB_PATH)

# 1. Fetch 52 companies
companies_df = pd.read_sql("SELECT id, symbol, company_name, sector, industry FROM companies ORDER BY symbol", conn)
print(f"Total Companies: {len(companies_df)}")

# 2. Check price coverage for 2025-10-01 to 2026-03-31
query = """
    SELECT c.symbol, MIN(dp.date) as min_date, MAX(dp.date) as max_date, COUNT(dp.id) as bar_count
    FROM companies c
    JOIN daily_prices dp ON c.id = dp.company_id
    WHERE dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
    GROUP BY c.symbol
    ORDER BY c.symbol
"""
coverage_df = pd.read_sql(query, conn)
print(f"Companies with price data in window: {len(coverage_df)}")
print(f"Min bar count per company: {coverage_df['bar_count'].min()}, Max bar count: {coverage_df['bar_count'].max()}")

# 3. Calculate 52-stock buy-and-hold returns
bh_query = """
    SELECT c.symbol, dp.date, dp.open, dp.close
    FROM companies c
    JOIN daily_prices dp ON c.id = dp.company_id
    WHERE dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
    ORDER BY c.symbol, dp.date ASC
"""
prices_df = pd.read_sql(bh_query, conn)
conn.close()

symbol_returns = []
for sym, group in prices_df.groupby("symbol"):
    group = group.sort_values("date")
    first_open = group.iloc[0]["open"]
    first_close = group.iloc[0]["close"]
    last_close = group.iloc[-1]["close"]
    
    ret_cc = (last_close - first_close) / first_close
    ret_oc = (last_close - first_open) / first_open
    symbol_returns.append({
        "symbol": sym,
        "first_close": first_close,
        "last_close": last_close,
        "return_close_to_close": ret_cc,
        "return_open_to_close": ret_oc,
    })

ret_df = pd.DataFrame(symbol_returns)
avg_cc = ret_df["return_close_to_close"].mean()
avg_oc = ret_df["return_open_to_close"].mean()
print(f"52-stock Equal-Weight Buy & Hold Return (Close-to-Close): {avg_cc*100:.2f}%")
print(f"52-stock Equal-Weight Buy & Hold Return (Open-to-Close): {avg_oc*100:.2f}%")
print(f"Best performer: {ret_df.loc[ret_df['return_close_to_close'].idxmax()]['symbol']} ({ret_df['return_close_to_close'].max()*100:.2f}%)")
print(f"Worst performer: {ret_df.loc[ret_df['return_close_to_close'].idxmin()]['symbol']} ({ret_df['return_close_to_close'].min()*100:.2f}%)")

ret_df.to_csv("scratch/audit_017_52_stock_benchmark_returns.csv", index=False)

