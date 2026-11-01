import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
prices_df = pd.read_sql_query('SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id', conn)
conn.close()

prices_df = prices_df.sort_values(['symbol', 'date']).reset_index(drop=True)
prices_df['prev_close'] = prices_df.groupby('symbol')['close'].shift(1)
prices_df['return_pct'] = (prices_df['close'] - prices_df['prev_close']) / prices_df['prev_close'] * 100

large_moves = prices_df[prices_df['return_pct'].abs() > 25]
print(f'Large moves (|ret| > 25%): {len(large_moves)}')
if len(large_moves) > 0:
    for idx, row in large_moves.iterrows():
        print(f"  {row['symbol']} on {row['date']}: prev={row['prev_close']:.2f}, close={row['close']:.2f}, ret={row['return_pct']:.2f}%, adj_close={row['adjusted_close']:.2f}")

# Check TMPV
tmpv = prices_df[prices_df['symbol'] == 'TMPV']
print(f"TMPV price range: min={tmpv['close'].min():.2f}, max={tmpv['close'].max():.2f}")

# Check ratio of adjusted_close to close distribution
prices_df['adj_ratio'] = prices_df['adjusted_close'] / prices_df['close']
print(f"Adj ratio min: {prices_df['adj_ratio'].min():.4f}, max: {prices_df['adj_ratio'].max():.4f}")
low_ratio = prices_df[prices_df['adj_ratio'] < 0.90]
print(f"Rows with adj_ratio < 0.90: {len(low_ratio)}")
if len(low_ratio) > 0:
    print(low_ratio[['symbol', 'date', 'close', 'adjusted_close', 'adj_ratio']].head(10))

