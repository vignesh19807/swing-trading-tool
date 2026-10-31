import sqlite3

conn = sqlite3.connect('database/swing_trading.db')
cursor = conn.cursor()
tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
for t in tables:
    count = cursor.execute(f"SELECT COUNT(1) FROM {t}").fetchone()[0]
    print(f"{t}: {count}")
conn.close()

