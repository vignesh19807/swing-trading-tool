import sqlite3

c1 = sqlite3.connect("database/swing_trading.db")
c2 = sqlite3.connect("database/swing_trading.db.bak_audit_019")

tables = [r[0] for r in c1.execute("SELECT name FROM sqlite_master WHERE type='table'")]
for t in sorted(tables):
    cnt1 = c1.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    cnt2 = c2.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    if cnt1 != cnt2:
        print(f"Count diff in {t}: {cnt1} vs {cnt2}")
    else:
        rows1 = c1.execute(f"SELECT * FROM {t}").fetchall()
        rows2 = c2.execute(f"SELECT * FROM {t}").fetchall()
        if repr(rows1) != repr(rows2):
            print(f"Row content diff in {t}")
print("Comparison complete.")

