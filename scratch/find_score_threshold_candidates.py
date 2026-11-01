import sys
sys.path.insert(0, '.')
from backend.engines.decision_engine import calculate_opportunity_score
import sqlite3

conn = sqlite3.connect('database/swing_trading.db')
c = conn.cursor()
c.execute("SELECT DISTINCT symbol FROM companies LIMIT 10")
symbols = [r[0] for r in c.fetchall()]
conn.close()

# Evaluate some dates to find near-threshold and insufficient data candidates
dates = ['2025-05-15', '2025-08-20', '2026-01-15', '2026-04-10']
near_thresh = []
insufficient = []

for dt in dates:
    for sym in symbols:
        try:
            res = calculate_opportunity_score(sym, evaluation_date=dt)
            opp = res.get('opportunity_score')
            rec = res.get('recommendation')
            if opp is not None and 70.0 <= opp < 75.0:
                near_thresh.append((sym, dt, opp, rec))
            elif rec == 'INSUFFICIENT_DATA':
                insufficient.append((sym, dt, res))
        except Exception as e:
            pass

print(f"Near threshold (70 <= opp < 75): {len(near_thresh)}")
for item in near_thresh[:3]:
    print(f"  {item[0]} on {item[1]}: Opp Score = {item[2]:.2f}, Rec = {item[3]}")

print(f"Insufficient data count: {len(insufficient)}")
for item in insufficient[:3]:
    print(f"  {item[0]} on {item[1]}: Status = {item[2].get('status')}")
