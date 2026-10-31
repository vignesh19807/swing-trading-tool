import sqlite3
import hashlib

c1 = sqlite3.connect('database/swing_trading.db')
c2 = sqlite3.connect('database/swing_trading.db.bak_audit_017')

tables = [r[0] for r in c1.execute("SELECT name FROM sqlite_master WHERE type='table'")]

for t in sorted(tables):
    rows1 = c1.execute(f"SELECT * FROM {t}").fetchall()
    rows2 = c2.execute(f"SELECT * FROM {t}").fetchall()
    h1 = hashlib.sha256(repr(rows1).encode()).hexdigest()
    h2 = hashlib.sha256(repr(rows2).encode()).hexdigest()
    if h1 != h2:
        print(f"Mismatch in table {t}!")
    else:
        print(f"Table {t} identical ({len(rows1)} rows)")

