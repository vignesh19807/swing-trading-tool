import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
query = '''
SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume, dp.adjusted_close
FROM daily_prices dp
JOIN companies c ON dp.company_id = c.id
ORDER BY c.symbol, dp.date
'''
df = pd.read_sql(query, conn)
conn.close()

df['prev_close'] = df.groupby('symbol')['close'].shift(1)
df['pct_change'] = (df['close'] - df['prev_close']) / df['prev_close'] * 100.0

large_disc = df[df['pct_change'].abs() >= 25.0]
for _, r in large_disc.iterrows():
    p_change = float(r['pct_change'])
    print(f"{r['symbol']} on {r['date']}: prev_close={r['prev_close']}, open={r['open']}, high={r['high']}, low={r['low']}, close={r['close']}, adj_close={r['adjusted_close']}, volume={r['volume']}, pct={p_change:.2f}%")

