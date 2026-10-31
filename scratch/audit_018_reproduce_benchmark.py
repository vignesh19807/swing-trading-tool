import os
import sys
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "database/swing_trading.db"

conn = sqlite3.connect(DB_PATH)

# Fetch 52 symbols
symbols = [r[0] for r in conn.execute("SELECT symbol FROM companies ORDER BY symbol").fetchall()]
print(f"Total symbols in benchmark: {len(symbols)}")

# Load daily prices for each symbol between 2025-10-01 and 2026-03-31
query = """
SELECT dp.date, c.symbol, dp.open, dp.close
FROM daily_prices dp
JOIN companies c ON c.id = dp.company_id
WHERE dp.date >= '2025-10-01' AND dp.date <= '2026-03-31'
ORDER BY dp.date ASC
"""
df = pd.read_sql_query(query, conn)
conn.close()

# Pivot close and open prices
df_close = df.pivot(index="date", columns="symbol", values="close")
df_open = df.pivot(index="date", columns="symbol", values="open")

print(f"Total trading days: {len(df_close)}")
start_date = df_close.index[0]
end_date = df_close.index[-1]
print(f"Start date: {start_date}, End date: {end_date}")

# 1. Close-to-Close Equal-Weight Return:
# For each stock: (Close_end - Close_start) / Close_start
c_start = df_close.iloc[0]
c_end = df_close.iloc[-1]
stock_returns_c2c = (c_end - c_start) / c_start
ew_return_c2c = stock_returns_c2c.mean()

# 2. Open-to-Close Return (Buying at start date open, selling at end date close):
o_start = df_open.iloc[0]
stock_returns_o2c = (c_end - o_start) / o_start
ew_return_o2c = stock_returns_o2c.mean()

# 3. Daily rebalanced Equal-Weight Return (Cumulative daily mean return):
daily_returns = df_close.pct_change().dropna()
daily_ew_returns = daily_returns.mean(axis=1)
cum_ew_rebalanced = (1.0 + daily_ew_returns).prod() - 1.0

print("\n=== Benchmark Calculation Results ===")
print(f"1. Close-to-Close Equal-Weight Buy-and-Hold Return: {ew_return_c2c * 100:.4f}% ({ew_return_c2c*100:.2f}%)")
print(f"2. Open-to-Close Equal-Weight Buy-and-Hold Return:  {ew_return_o2c * 100:.4f}% ({ew_return_o2c*100:.2f}%)")
print(f"3. Daily-Rebalanced Equal-Weight Return:            {cum_ew_rebalanced * 100:.4f}% ({cum_ew_rebalanced*100:.2f}%)")

print("\nSummary Statistics of Constituent Returns (Close-to-Close):")
print(f"  Mean:   {stock_returns_c2c.mean()*100:.2f}%")
print(f"  Median: {stock_returns_c2c.median()*100:.2f}%")
print(f"  Min:    {stock_returns_c2c.min()*100:.2f}% ({stock_returns_c2c.idxmin()})")
print(f"  Max:    {stock_returns_c2c.max()*100:.2f}% ({stock_returns_c2c.idxmax()})")
print(f"  Std:    {stock_returns_c2c.std()*100:.2f}%")

# Positive vs Negative performers
pos_count = (stock_returns_c2c > 0).sum()
neg_count = (stock_returns_c2c < 0).sum()
print(f"  Positive stocks: {pos_count}/{len(symbols)} ({pos_count/len(symbols)*100:.1f}%)")
print(f"  Negative stocks: {neg_count}/{len(symbols)} ({neg_count/len(symbols)*100:.1f}%)")

