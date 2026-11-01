import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
query = '''
SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.adjusted_close, dp.volume
FROM daily_prices dp
JOIN companies c ON dp.company_id = c.id
WHERE c.symbol = 'TRENT'
ORDER BY dp.date
'''
df = pd.read_sql(query, conn)
conn.close()

idx = df[df['date'] == '2026-01-01'].index[0]
surrounding = df.iloc[max(0, idx-5):min(len(df), idx+6)]
print("TRENT surrounding sessions:")
print(surrounding[['date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']])

# Check the ratio between close on 2026-01-01 and prev_close on 2025-12-31
prev_c = df.loc[idx-1, 'close']
curr_c = df.loc[idx, 'close']
ratio = curr_c / prev_c
print(f"\n2025-12-31 close: {prev_c}")
print(f"2026-01-01 close: {curr_c}")
print(f"Ratio curr/prev: {ratio:.6f}")
print(f"2/3 ratio: {2.0/3.0:.6f}")
print(f"Diff from 2/3: {abs(ratio - 2.0/3.0):.6f}")

# Check adjusted close
prev_adj = df.loc[idx-1, 'adjusted_close']
curr_adj = df.loc[idx, 'adjusted_close']
adj_ratio = curr_adj / prev_adj
print(f"\n2025-12-31 adjusted_close: {prev_adj}")
print(f"2026-01-01 adjusted_close: {curr_adj}")
print(f"Ratio adj_curr/adj_prev: {adj_ratio:.6f}")

