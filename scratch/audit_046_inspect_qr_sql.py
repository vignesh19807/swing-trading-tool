import sqlite3

def print_table_sql(db_path, table_name):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT sql FROM sqlite_master WHERE name=?", (table_name,))
    row = c.fetchone()
    print(f"=== {db_path} :: {table_name} ===")
    if row:
        print(row[0])
    else:
        print("Not found")
    conn.close()

print_table_sql('database/swing_trading.db', 'quarterly_results')
print_table_sql('database/staging_financial_expansion.db', 'quarterly_results')

