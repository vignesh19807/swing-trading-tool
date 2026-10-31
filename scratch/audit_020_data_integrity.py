import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect("database/swing_trading.db")

print("=== 1. Universe & Symbol Normalization ===")
df_companies = pd.read_sql("SELECT * FROM companies ORDER BY symbol", conn)
print(f"Total Companies: {len(df_companies)}")
print("Null or empty symbols:", df_companies["symbol"].isna().sum() + (df_companies["symbol"] == "").sum())
print("Unique symbols:", df_companies["symbol"].nunique())
symbols_with_dot = df_companies[df_companies["symbol"].str.contains(r"\.")]["symbol"].tolist()
print("Symbols containing dot / suffix:", symbols_with_dot)

print("\n=== 2. Daily Prices Integrity ===")
df_prices = pd.read_sql("""
    SELECT dp.id, c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
    FROM daily_prices dp
    JOIN companies c ON c.id = dp.company_id
    ORDER BY c.symbol, dp.date
""", conn)
total_bars = len(df_prices)
print(f"Total Daily Price Bars: {total_bars}")

# Check duplicates
dups = df_prices.duplicated(subset=["symbol", "date"]).sum()
print(f"Duplicate (symbol, date) bars: {dups}")

# Check non-positive prices
non_pos_open = (df_prices["open"] <= 0).sum()
non_pos_high = (df_prices["high"] <= 0).sum()
non_pos_low = (df_prices["low"] <= 0).sum()
non_pos_close = (df_prices["close"] <= 0).sum()
neg_volume = (df_prices["volume"] < 0).sum()
zero_volume = (df_prices["volume"] == 0).sum()
print(f"Non-positive prices: Open={non_pos_open}, High={non_pos_high}, Low={non_pos_low}, Close={non_pos_close}")
print(f"Negative Volume: {neg_volume}, Zero Volume: {zero_volume}")

# Check OHLC geometric consistency:
# High >= Low, High >= Open, High >= Close, Low <= Open, Low <= Close
# Use a tiny tolerance for floating point representations (1e-4)
tol = 1e-4
bad_hl = (df_prices["high"] < df_prices["low"] - tol).sum()
bad_ho = (df_prices["high"] < df_prices["open"] - tol).sum()
bad_hc = (df_prices["high"] < df_prices["close"] - tol).sum()
bad_lo = (df_prices["low"] > df_prices["open"] + tol).sum()
bad_lc = (df_prices["low"] > df_prices["close"] + tol).sum()
print(f"OHLC Geometric Inconsistencies: High < Low: {bad_hl}, High < Open: {bad_ho}, High < Close: {bad_hc}, Low > Open: {bad_lo}, Low > Close: {bad_lc}")

# Calendar alignment
dates_per_symbol = df_prices.groupby("symbol")["date"].agg(["min", "max", "count"])
print(f"Date ranges per symbol: Min count={dates_per_symbol['count'].min()}, Max count={dates_per_symbol['count'].max()}")
all_dates = df_prices["date"].unique()
print(f"Unique trading dates across universe: {len(all_dates)} (From {all_dates.min()} to {all_dates.max()})")

# Check if any symbol has missing dates relative to universe trading calendar
date_set = set(all_dates)
symbols_with_gaps = []
for sym, group in df_prices.groupby("symbol"):
    sym_dates = set(group["date"])
    diff = date_set - sym_dates
    if diff:
        symbols_with_gaps.append((sym, len(diff)))
print(f"Symbols with missing trading calendar dates: {len(symbols_with_gaps)}")

print("\n=== 3. Extreme Price Movement & Split Anomaly Check ===")
df_prices["daily_return"] = df_prices.groupby("symbol")["close"].pct_change()
extreme_jumps = df_prices[df_prices["daily_return"].abs() > 0.50][["symbol", "date", "close", "daily_return"]]
print(f"Extreme single-day returns (> 50% absolute): {len(extreme_jumps)}")
if not extreme_jumps.empty:
    print(extreme_jumps.to_string())

print("\n=== 4. Technical Indicators Integrity ===")
df_ti = pd.read_sql("""
    SELECT count(*) as total_ti, 
           sum(CASE WHEN ema_20 IS NULL THEN 1 ELSE 0 END) as null_ema20,
           sum(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as null_rsi,
           sum(CASE WHEN macd IS NULL THEN 1 ELSE 0 END) as null_macd,
           sum(CASE WHEN atr_14 IS NULL THEN 1 ELSE 0 END) as null_atr,
           sum(CASE WHEN technical_score IS NULL THEN 1 ELSE 0 END) as null_score
    FROM technical_indicators
""", conn)
print(df_ti.to_string())

print("\n=== 5. Quarterly Results Integrity ===")
df_q = pd.read_sql("""
    SELECT count(*) as total_q,
           sum(CASE WHEN revenue IS NULL OR revenue <= 0 THEN 1 ELSE 0 END) as non_pos_rev,
           sum(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) as null_np,
           sum(CASE WHEN publication_date IS NULL THEN 1 ELSE 0 END) as null_pub
    FROM quarterly_results
""", conn)
print(df_q.to_string())

conn.close()
