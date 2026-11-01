import sys
sys.path.insert(0, '.')
from backend.engines.financial_engine import analyze_financial_health
import sqlite3

conn = sqlite3.connect('database/swing_trading.db')
c = conn.cursor()
c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2026-02-01' AND date <= '2026-02-28' ORDER BY date")
dates = [r[0] for r in c.fetchall()]
conn.close()

print("Testing financial health availability across February 2026 dates for ABB and SUNPHARMA:")
for dt in dates:
    res_abb = analyze_financial_health('ABB', evaluation_date=dt)
    res_sun = analyze_financial_health('SUNPHARMA', evaluation_date=dt)
    print(f"Date {dt}: ABB score = {res_abb.get('overall_score')}, SUNPHARMA score = {res_sun.get('overall_score')}")

