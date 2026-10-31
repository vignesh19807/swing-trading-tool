import sqlite3

c1 = sqlite3.connect('database/swing_trading.db')
c2 = sqlite3.connect('database/swing_trading.db.bak_audit_017')

r1 = c1.execute("SELECT * FROM backtest_results").fetchall()
r2 = c2.execute("SELECT * FROM backtest_results").fetchall()

print(f"c1 count: {len(r1)}, c2 count: {len(r2)}")
for row1, row2 in zip(r1, r2):
    if row1 != row2:
        print("Diff:", row1, "vs", row2)

