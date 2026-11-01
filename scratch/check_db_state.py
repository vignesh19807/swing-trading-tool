import os
import hashlib
import sqlite3
import datetime

db_path = os.path.abspath('database/swing_trading.db')
with open(db_path, 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest().upper()

stat = os.stat(db_path)
size = stat.st_size
mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()

print(f"DB Path: {db_path}")
print(f"SHA-256: {h}")
print(f"Size: {size} bytes")
print(f"MTime: {mtime}")

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("PRAGMA integrity_check")
integrity = c.fetchone()[0]
print(f"Integrity: {integrity}")

c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall()]
print(f"Tables ({len(tables)}):")
for t in tables:
    c.execute(f"SELECT count(*) FROM [{t}]")
    cnt = c.fetchone()[0]
    print(f"  {t:30}: {cnt}")

conn.close()

