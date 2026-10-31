import sqlite3
import pandas as pd

conn = sqlite3.connect("database/swing_trading.db")

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("=== Table Counts ===")
for t in tables:
    cnt = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"{t}: {cnt}")

stock_count = conn.execute("SELECT count(*) FROM companies").fetchone()[0]
print(f"\nTotal Stock Count: {stock_count}")

date_min, date_max = conn.execute("SELECT min(date), max(date) FROM daily_prices").fetchone()
total_price_rows = conn.execute("SELECT count(*) FROM daily_prices").fetchone()[0]
print(f"Daily Price Date Range: {date_min} to {date_max} ({total_price_rows} rows)")

quarterly_total = conn.execute("SELECT count(*) FROM quarterly_results").fetchone()[0]
quarterly_null_pub = conn.execute("SELECT count(*) FROM quarterly_results WHERE publication_date IS NULL").fetchone()[0]
print(f"Quarterly Results: {quarterly_total} total rows, {quarterly_null_pub} NULL publication dates ({quarterly_null_pub/quarterly_total*100:.1f}%)")
