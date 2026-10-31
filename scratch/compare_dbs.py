import sqlite3

c1 = sqlite3.connect('database/swing_trading.db')
c2 = sqlite3.connect('database/swing_trading.db.bak_audit_017')

tables1 = set(r[0] for r in c1.execute("SELECT name FROM sqlite_master WHERE type='table'"))
tables2 = set(r[0] for r in c2.execute("SELECT name FROM sqlite_master WHERE type='table'"))

print('Tables diff:', tables1 ^ tables2)

for t in sorted(tables1 & tables2):
    cnt1 = c1.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    cnt2 = c2.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    if cnt1 != cnt2:
        print(f"Table {t} count diff: db={cnt1}, bak={cnt2}")
    else:
        # Check if rows changed
        pass
print("Comparison done.")

