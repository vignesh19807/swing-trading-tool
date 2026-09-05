import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "database/swing_trading.db"

def audit():
    conn = sqlite3.connect(DB_PATH)
    
    print("--- 1. Stock Universe (companies) ---")
    df_comp = pd.read_sql_query("SELECT count(*) as cnt FROM companies", conn)
    print(df_comp)
    
    print("\n--- 2. Market Data (daily_prices) ---")
    df_mkt = pd.read_sql_query("SELECT company_id, count(*) as price_cnt FROM daily_prices GROUP BY company_id", conn)
    print(f"Total symbols with market data: {len(df_mkt)}")
    print(f"Total market data records: {df_mkt['price_cnt'].sum()}")
    if len(df_mkt) < 100:
        missing = pd.read_sql_query("SELECT symbol FROM companies WHERE id NOT IN (SELECT company_id FROM daily_prices)", conn)
        print("Missing symbols in market data:", len(missing))

    print("\n--- 3. Financial Data (quarterly_results) ---")
    df_fin = pd.read_sql_query("SELECT company_id, count(*) as fin_cnt FROM quarterly_results GROUP BY company_id", conn)
    print(f"Total symbols with financial data: {len(df_fin)}")
    print(f"Total financial records: {df_fin['fin_cnt'].sum()}")
    missing_fin = pd.read_sql_query("SELECT symbol FROM companies WHERE id NOT IN (SELECT company_id FROM quarterly_results)", conn)
    print(f"Missing symbols in financial data: {len(missing_fin)}")

    print("\n--- 4. Technical Data (technical_indicators) ---")
    df_tech = pd.read_sql_query("SELECT company_id, count(*) as tech_cnt FROM technical_indicators GROUP BY company_id", conn)
    print(f"Total symbols with technical data: {len(df_tech)}")
    print(f"Total technical records: {df_tech['tech_cnt'].sum()}")
    missing_tech = pd.read_sql_query("SELECT symbol FROM companies WHERE id NOT IN (SELECT company_id FROM technical_indicators)", conn)
    print(f"Missing symbols in technical data: {len(missing_tech)}")

    conn.close()

if __name__ == "__main__":
    audit()
