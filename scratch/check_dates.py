import sqlite3

c = sqlite3.connect("docs/audit_artifacts/temp_multiyear_audit_025.db")
dates_apr = [r[0] for r in c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2025-04-01' ORDER BY date").fetchall()]
print(f"Total trading dates from 2025-04-01: {len(dates_apr)} (from {dates_apr[0]} to {dates_apr[-1]})")
dates_jan = [r[0] for r in c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2025-01-01' ORDER BY date").fetchall()]
print(f"Total trading dates from 2025-01-01: {len(dates_jan)} (from {dates_jan[0]} to {dates_jan[-1]})")
dates_oct = [r[0] for r in c.execute("SELECT DISTINCT date FROM daily_prices ORDER BY date").fetchall()]
print(f"All trading dates: {len(dates_oct)} (from {dates_oct[0]} to {dates_oct[-1]})")

