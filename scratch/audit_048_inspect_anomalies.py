import sqlite3
import pandas as pd

conn = sqlite3.connect('database/swing_trading.db')
c = pd.read_sql_query("SELECT * FROM companies WHERE symbol IN ('TMPV', 'TRENT')", conn)
print("Companies:")
print(c)

p_tmpv = pd.read_sql_query("SELECT dp.* FROM daily_prices dp JOIN companies c ON dp.company_id = c.id WHERE c.symbol='TMPV' AND dp.date BETWEEN '2025-10-08' AND '2025-10-22'", conn)
print("\nTMPV prices around 2025-10-14:")
print(p_tmpv[['date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']])

p_trent = pd.read_sql_query("SELECT dp.* FROM daily_prices dp JOIN companies c ON dp.company_id = c.id WHERE c.symbol='TRENT' AND dp.date BETWEEN '2025-12-24' AND '2026-01-08'", conn)
print("\nTRENT prices around 2026-01-01:")
print(p_trent[['date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']])
conn.close()

