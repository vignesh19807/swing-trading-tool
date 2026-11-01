import sqlite3
import os

staging_db = 'database/staging_financial_expansion.db'
prod_db = 'database/swing_trading.db'

if os.path.exists(staging_db):
    os.remove(staging_db)

con_prod = sqlite3.connect(prod_db)
cur_prod = con_prod.cursor()
cur_prod.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL AND name != 'sqlite_sequence'")
table_sqls = [r[0] for r in cur_prod.fetchall()]

con_stage = sqlite3.connect(staging_db)
cur_stage = con_stage.cursor()

for sql in table_sqls:
    cur_stage.execute(sql)

# Copy base data tables
tables_to_copy = ['sectors', 'industries', 'companies', 'daily_prices', 'technical_indicators', 'quarterly_results']
for t in tables_to_copy:
    cur_prod.execute(f"SELECT * FROM {t}")
    rows = cur_prod.fetchall()
    if rows:
        placeholders = ','.join(['?'] * len(rows[0]))
        cur_stage.executemany(f"INSERT INTO {t} VALUES ({placeholders})", rows)
con_stage.commit()

cur_stage.execute("SELECT count(*) FROM quarterly_results")
print("Initial quarterly_results in staging:", cur_stage.fetchone()[0])
con_prod.close()
con_stage.close()
print("Staging DB successfully initialized from production schema and baseline data.")
