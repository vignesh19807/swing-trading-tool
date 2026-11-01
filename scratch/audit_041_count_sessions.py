import sqlite3

conn = sqlite3.connect('database/swing_trading.db')
c = conn.cursor()

c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2025-04-01' AND date < '2026-02-13' ORDER BY date")
dates_strictly_before = [r[0] for r in c.fetchall()]
print(f"Strictly before 2026-02-13: {len(dates_strictly_before)} dates = {len(dates_strictly_before)*52} stock-sessions")

c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2025-04-01' AND date <= '2026-02-13' ORDER BY date")
dates_through_13 = [r[0] for r in c.fetchall()]
print(f"Through 2026-02-13: {len(dates_through_13)} dates = {len(dates_through_13)*52} stock-sessions")

c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2026-02-13' AND date <= '2026-10-23' ORDER BY date")
dates_from_13 = [r[0] for r in c.fetchall()]
print(f"From 2026-02-13 onwards: {len(dates_from_13)} dates = {len(dates_from_13)*52} stock-sessions")

c.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2026-02-16' AND date <= '2026-10-23' ORDER BY date")
dates_from_16 = [r[0] for r in c.fetchall()]
print(f"From 2026-02-16 onwards: {len(dates_from_16)} dates = {len(dates_from_16)*52} stock-sessions")

conn.close()
