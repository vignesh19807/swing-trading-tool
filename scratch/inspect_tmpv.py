import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
query = '''
SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.adjusted_close, dp.volume
FROM daily_prices dp
JOIN companies c ON dp.company_id = c.id
WHERE c.symbol = 'TMPV'
ORDER BY dp.date
'''
df = pd.read_sql(query, conn)
conn.close()

idx = df[df['date'] == '2025-10-14'].index[0]
surrounding = df.iloc[max(0, idx-5):min(len(df), idx+6)]
print("TMPV surrounding sessions:")
print(surrounding[['date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']])

prev_c = df.loc[idx-1, 'close']
curr_c = df.loc[idx, 'close']
ratio = curr_c / prev_c
print(f"\n2025-10-13 close: {prev_c}")
print(f"2025-10-14 close: {curr_c}")
print(f"Ratio curr/prev: {ratio:.6f}")

prev_adj = df.loc[idx-1, 'adjusted_close']
curr_adj = df.loc[idx, 'adjusted_close']
adj_ratio = curr_adj / prev_adj
print(f"\n2025-10-13 adjusted_close: {prev_adj}")
print(f"2025-10-14 adjusted_close: {curr_adj}")
print(f"Ratio adj_curr/adj_prev: {adj_ratio:.6f}")

