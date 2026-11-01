import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
prices_df = pd.read_sql_query("SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id", conn)

dates_to_check = ['2025-03-18', '2026-01-15']
for d in dates_to_check:
    sub = prices_df[prices_df['date'] == d]
    print(f"\nDate {d}: {len(sub)} rows")
    flat_bars = sub[(sub['open'] == sub['high']) & (sub['high'] == sub['low']) & (sub['low'] == sub['close'])]
    print(f"Flat bars (O=H=L=C) on {d}: {len(flat_bars)}")
    print(f"Volume = 0 on {d}: {(sub['volume'] == 0).sum()}")
    prev_dates = sorted([dt for dt in prices_df['date'].unique() if dt < d])
    if prev_dates:
        prev_d = prev_dates[-1]
        prev_sub = prices_df[prices_df['date'] == prev_d].set_index('symbol')['close']
        curr_sub = sub.set_index('symbol')['close']
        matching_prev = (prev_sub == curr_sub).sum()
        print(f"Matching previous day's close exactly on {d}: {matching_prev} of {len(sub)}")

conn.close()

