import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
prices_df = pd.read_sql_query("SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id", conn)

diff = prices_df[prices_df['close'] != prices_df['adjusted_close']]
print(f"Total rows where close != adjusted_close: {len(diff)}")
print(f"Symbols with adjusted_close != close: {diff['symbol'].nunique()}")
print("Sample difference rows:")
print(diff[['symbol', 'date', 'close', 'adjusted_close']].head(10))

# Ratio of adjusted_close / close
diff['ratio'] = diff['adjusted_close'] / diff['close']
print("\nRatio summary:")
print(diff['ratio'].describe())

conn.close()

