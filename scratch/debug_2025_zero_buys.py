import sys
sys.path.insert(0, '.')
from backend.engines.decision_engine import calculate_opportunity_score
import sqlite3

conn = sqlite3.connect('database/swing_trading.db')
c = conn.cursor()
c.execute("SELECT DISTINCT symbol FROM companies LIMIT 5")
symbols = [r[0] for r in c.fetchall()]
conn.close()

test_dates = ['2025-04-15', '2025-06-15', '2025-09-15', '2025-11-15', '2026-01-15', '2026-02-15']

for dt in test_dates:
    print(f"\n--- Testing Date: {dt} ---")
    for sym in symbols:
        res = calculate_opportunity_score(sym, evaluation_date=dt)
        print(f"  {sym:12}: Status={res.get('status')}, Tech={res.get('technical_score')}, Fin={res.get('financial_score')}, Mom={res.get('momentum_score')}, Opp={res.get('opportunity_score')}, Rec={res.get('recommendation')}")

