import sqlite3
import pandas as pd

con = sqlite3.connect("database/swing_trading.db")
cid = pd.read_sql("SELECT id FROM companies WHERE symbol='MAXHEALTH'", con).iloc[0, 0]
df = pd.read_sql(f"SELECT date, open, high, low, close FROM daily_prices WHERE company_id={cid} AND date IN ('2026-08-07', '2026-08-10', '2026-08-11') ORDER BY date", con)
print(df)
con.close()

