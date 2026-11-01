import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
prices_df = pd.read_sql_query("SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id", conn)

# 1. Zero volume rows
zero_vol = prices_df[prices_df['volume'] == 0]
print(f"Zero volume rows count: {len(zero_vol)}")
print("Zero volume breakdown by symbol:")
print(zero_vol['symbol'].value_counts())
print("\nZero volume breakdown by date (top 10):")
print(zero_vol['date'].value_counts().head(10))
print("\nSample zero volume records:")
print(zero_vol[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].head(10))

# 2. Check the 495 vs 496 bars discrepancy
bars_per_sym = prices_df.groupby('symbol')['date'].count()
max_syms = bars_per_sym[bars_per_sym == 496].index.tolist()
print(f"\nSymbols with 496 bars ({len(max_syms)}): {max_syms}")
non_max_syms = bars_per_sym[bars_per_sym == 495].index.tolist()
print(f"Symbols with 495 bars ({len(non_max_syms)})")

# Which date is present in 496 but missing in 495?
dates_496 = set(prices_df[prices_df['symbol'].isin(max_syms)]['date'])
dates_495 = set(prices_df[prices_df['symbol'].isin(non_max_syms)]['date'])
diff_dates = dates_496 - dates_495
print(f"Dates in 496-bar symbols but NOT in 495-bar symbols: {diff_dates}")
diff_dates_rev = dates_495 - dates_496
print(f"Dates in 495-bar symbols but NOT in 496-bar symbols: {diff_dates_rev}")

# Let's inspect which symbols have which dates
piv = prices_df.pivot(index='date', columns='symbol', values='close')
null_in_piv = piv.isnull().sum()
print(f"Missing dates in pivot: {null_in_piv[null_in_piv > 0].to_dict()}")

# Check which dates are missing for which symbols
for s in non_max_syms[:5]:
    s_dates = set(prices_df[prices_df['symbol'] == s]['date'])
    missing_for_s = set(prices_df['date'].unique()) - s_dates
    print(f"Missing date for {s}: {missing_for_s}")

conn.close()

