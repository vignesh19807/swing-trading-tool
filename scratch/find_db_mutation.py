import sqlite3
import pandas as pd

conn_prod = sqlite3.connect("database/swing_trading.db")
conn_bak = sqlite3.connect("database/swing_trading.db.bak_audit_019")

tables = [r[0] for r in conn_prod.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

diffs = []
for t in tables:
    cnt_prod = conn_prod.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    cnt_bak = conn_bak.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    if cnt_prod != cnt_bak:
        diffs.append((t, "row_count", cnt_bak, cnt_prod))
    else:
        # Check if contents differ
        df_p = pd.read_sql(f"SELECT * FROM {t}", conn_prod)
        df_b = pd.read_sql(f"SELECT * FROM {t}", conn_bak)
        if not df_p.equals(df_b):
            diffs.append((t, "content_mismatch", len(df_b), len(df_p)))

print("=== Table Differences ===")
for d in diffs:
    print(d)

# Check sqlite_sequence specifically
seq_p = conn_prod.execute("SELECT * FROM sqlite_sequence").fetchall()
seq_b = conn_bak.execute("SELECT * FROM sqlite_sequence").fetchall()
print("\nsqlite_sequence in bak:", seq_b)
print("sqlite_sequence in prod:", seq_p)

conn_prod.close()
conn_bak.close()

