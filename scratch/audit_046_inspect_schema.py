import sqlite3
import json

def inspect_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name;")
    tables = cursor.fetchall()
    info = {}
    for name, t_type in tables:
        cursor.execute(f"PRAGMA table_info({name});")
        cols = [{"cid": c[0], "name": c[1], "type": c[2], "notnull": c[3], "dflt_value": c[4], "pk": c[5]} for c in cursor.fetchall()]
        cursor.execute(f"SELECT COUNT(*) FROM {name};")
        cnt = cursor.fetchone()[0]
        info[name] = {"type": t_type, "row_count": cnt, "columns": cols}
    conn.close()
    return info

prod_info = inspect_db('database/swing_trading.db')
print("PROD_DB TABLES:")
for t, d in prod_info.items():
    col_names = [c["name"] for c in d["columns"]]
    print(f"  {t} ({d['type']}): {d['row_count']} rows | cols: {col_names}")

stage_info = inspect_db('database/staging_financial_expansion.db')
print("\nSTAGE_DB TABLES:")
for t, d in stage_info.items():
    col_names = [c["name"] for c in d["columns"]]
    print(f"  {t} ({d['type']}): {d['row_count']} rows | cols: {col_names}")

