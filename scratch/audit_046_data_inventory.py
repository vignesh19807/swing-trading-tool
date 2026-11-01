import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('database/swing_trading.db')

# 1. Company coverage
companies_df = pd.read_sql_query("SELECT * FROM companies", conn)
print(f"Total Companies: {len(companies_df)}")
print(f"Unique Symbols: {companies_df['symbol'].nunique()}")
print(f"Exchanges: {companies_df['exchange'].value_counts().to_dict()}")

# 2. Daily prices coverage
prices_df = pd.read_sql_query("SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id", conn)
print(f"\nDaily Prices Total Rows: {len(prices_df)}")
print(f"Date Range: {prices_df['date'].min()} to {prices_df['date'].max()}")
print(f"Unique Trading Dates: {prices_df['date'].nunique()}")
print(f"Unique Symbols in Prices: {prices_df['symbol'].nunique()}")

# Missing values in daily_prices
null_counts = prices_df.isnull().sum().to_dict()
print(f"Null counts in daily_prices: {null_counts}")

# Check per-symbol bar counts
bars_per_sym = prices_df.groupby('symbol')['date'].count()
print(f"Bars per symbol: min={bars_per_sym.min()}, max={bars_per_sym.max()}, mean={bars_per_sym.mean():.2f}")
if bars_per_sym.min() != bars_per_sym.max():
    print(f"Symbols with non-max bars: {bars_per_sym[bars_per_sym < bars_per_sym.max()].to_dict()}")

# Check invalid OHLC relationships
invalid_high = prices_df[prices_df['high'] < prices_df['low']]
invalid_open = prices_df[(prices_df['open'] > prices_df['high']) | (prices_df['open'] < prices_df['low'])]
invalid_close = prices_df[(prices_df['close'] > prices_df['high']) | (prices_df['close'] < prices_df['low'])]
non_positive = prices_df[(prices_df['open'] <= 0) | (prices_df['high'] <= 0) | (prices_df['low'] <= 0) | (prices_df['close'] <= 0)]
zero_vol = prices_df[prices_df['volume'] == 0]
negative_vol = prices_df[prices_df['volume'] < 0]

print(f"Invalid High < Low: {len(invalid_high)}")
print(f"Invalid Open outside High/Low: {len(invalid_open)}")
print(f"Invalid Close outside High/Low: {len(invalid_close)}")
print(f"Non-positive prices: {len(non_positive)}")
print(f"Zero volume rows: {len(zero_vol)}")
print(f"Negative volume rows: {len(negative_vol)}")

# Adjusted close vs close
diff_adj = prices_df[prices_df['adjusted_close'] != prices_df['close']]
print(f"Rows where adjusted_close != close: {len(diff_adj)}")

# Check duplicates
dup_prices = prices_df.duplicated(subset=['company_id', 'date']).sum()
print(f"Duplicate (company_id, date) pairs: {dup_prices}")

# 3. Quarterly results coverage
qr_df = pd.read_sql_query("SELECT qr.*, c.symbol FROM quarterly_results qr JOIN companies c ON qr.company_id = c.id", conn)
print(f"\nQuarterly Results Total Rows: {len(qr_df)}")
print(f"Unique Symbols in QR: {qr_df['symbol'].nunique()}")
print(f"Quarters represented: {sorted(qr_df['quarter'].unique())}")
qr_per_sym = qr_df.groupby('symbol')['quarter'].count()
print(f"Quarters per symbol: min={qr_per_sym.min()}, max={qr_per_sym.max()}")
print(f"Publication dates null count: {qr_df['publication_date'].isnull().sum()} out of {len(qr_df)}")
print(f"Publication dates non-null values: {qr_df['publication_date'].dropna().tolist()}")

# Missing values in financial metrics
qr_nulls = qr_df.isnull().sum().to_dict()
print(f"Null counts in quarterly_results: {qr_nulls}")

# Zero values in financial metrics
for col in ['revenue', 'net_profit', 'eps', 'roe', 'roce', 'debt_equity', 'operating_margin', 'net_margin']:
    zero_cnt = (qr_df[col] == 0).sum()
    print(f"Zero count for {col}: {zero_cnt}")

# 4. Technical indicators
ti_df = pd.read_sql_query("SELECT * FROM technical_indicators", conn)
print(f"\nTechnical Indicators Total Rows: {len(ti_df)}")
print(f"Null counts in technical_indicators: {ti_df.isnull().sum().to_dict()}")

conn.close()

