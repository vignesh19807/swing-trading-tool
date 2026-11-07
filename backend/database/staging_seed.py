"""
Staging Database Provisioning and Seeding Script
================================================
Provisions a staging-only SQLite database with complete schemas,
realistic Indian equities, market data bars, and point-in-time financial vintages.

STRICT INVARIANT:
Never modifies or overwrites database/swing_trading.db.
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path

from backend.config import PROJECT_ROOT

PROD_DB_NAME = "swing_trading.db"
DEFAULT_STAGING_PATH = PROJECT_ROOT / "database" / "staging_swing_trading.db"

STAGING_COMPANIES = [
    ("TCS", "Tata Consultancy Services Ltd", "Information Technology", "IT Services", "NSE", 1, "ACTIVE", "2004-08-25"),
    ("INFY", "Infosys Ltd", "Information Technology", "IT Services", "NSE", 1, "ACTIVE", "1993-02-08"),
    ("RELIANCE", "Reliance Industries Ltd", "Energy", "Oil & Gas", "NSE", 1, "ACTIVE", "1977-11-29"),
    ("HDFCBANK", "HDFC Bank Ltd", "Financial Services", "Private Sector Bank", "NSE", 1, "ACTIVE", "1995-05-19"),
    ("ICICIBANK", "ICICI Bank Ltd", "Financial Services", "Private Sector Bank", "NSE", 1, "ACTIVE", "1998-09-17"),
    ("TATAMOTORS", "Tata Motors Ltd", "Automobile and Auto Components", "Automobiles", "NSE", 1, "COLD_START", "1945-09-01"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd", "Healthcare", "Pharmaceuticals", "NSE", 1, "ACTIVE", "1994-12-26"),
    ("HINDUNILVR", "Hindustan Unilever Ltd", "Fast Moving Consumer Goods", "Personal Products", "NSE", 1, "ACTIVE", "1956-11-01"),
    ("ITC", "ITC Ltd", "Fast Moving Consumer Goods", "Cigarettes & Tobacco", "NSE", 1, "ACTIVE", "1954-08-24"),
    ("LT", "Larsen & Toubro Ltd", "Capital Goods", "Civil Construction", "NSE", 1, "ACTIVE", "1950-06-23"),
]

def provision_staging_database(target_path: Path = None, force_recreate: bool = True) -> Path:
    out_path = Path(target_path) if target_path else DEFAULT_STAGING_PATH
    out_path = out_path.resolve()

    # Safety Guard: Ensure we never touch the production database
    prod_canonical = (PROJECT_ROOT / "database" / PROD_DB_NAME).resolve()
    if out_path == prod_canonical:
        raise ValueError(
            f"CRITICAL SAFETY VIOLATION: Refusing to provision staging onto production database at {out_path}!"
        )

    if out_path.exists() and force_recreate:
        out_path.unlink()

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Set DATABASE_PATH to staging path during creation
    prev_env = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = str(out_path)

    try:
        # 1. Base DDL
        from backend.database.create_database import create_database
        create_database()

        # 1.1 Backtest Result & Portfolio DDL
        from backend.data_pipeline.backtest_result_service import initialize_backtest_results_table
        initialize_backtest_results_table()

        # 2. Master Sectors & Industries DDL
        conn = sqlite3.connect(out_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS industries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sector_id INTEGER NOT NULL,
                FOREIGN KEY (sector_id) REFERENCES sectors(id),
                UNIQUE(name, sector_id)
            )
        """)

        # Extract and insert unique sectors
        unique_sectors = sorted(list({c[2] for c in STAGING_COMPANIES}))
        for s in unique_sectors:
            cur.execute("INSERT OR IGNORE INTO sectors (name) VALUES (?)", (s,))
        cur.execute("SELECT id, name FROM sectors")
        sec_map = {r[1]: r[0] for r in cur.fetchall()}

        # Extract and insert unique industries
        unique_industries = sorted(list({(c[3], c[2]) for c in STAGING_COMPANIES if c[3]}))
        for ind_name, sec_name in unique_industries:
            cur.execute(
                "INSERT OR IGNORE INTO industries (name, sector_id) VALUES (?, ?)",
                (ind_name, sec_map[sec_name]),
            )
        cur.execute("SELECT id, name FROM industries")
        ind_map = {r[1]: r[0] for r in cur.fetchall()}

        conn.commit()
        conn.close()

        # 3. Dynamic Universe Schema Migration
        from backend.database.migrate_universe_schema import migrate_universe_schema
        migrate_universe_schema(str(out_path))

        # 4. Insert Staging Companies
        conn = sqlite3.connect(out_path)
        cur = conn.cursor()

        for sym, name, sec, ind, exch, act, st, ldate in STAGING_COMPANIES:
            s_id = sec_map.get(sec)
            i_id = ind_map.get(ind)
            cur.execute("""
                INSERT INTO companies (
                    symbol, company_name, sector, industry, exchange,
                    is_active, status, listing_date, created_at, source,
                    sector_id, industry_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'STAGING_PROVISION', ?, ?)
            """, (sym, name, sec, ind, exch, act, st, ldate, s_id, i_id))

        cur.execute("SELECT id, symbol FROM companies")
        company_ids = {r[1]: r[0] for r in cur.fetchall()}

        # 5. Insert Daily Price Bars (250 bars per stock up to current date)
        today = datetime.datetime.now(datetime.timezone.utc).date()
        base_prices = {
            "TCS": 3500.0, "INFY": 1500.0, "RELIANCE": 2500.0, "HDFCBANK": 1600.0,
            "ICICIBANK": 1100.0, "TATAMOTORS": 750.0, "SUNPHARMA": 1650.0,
            "HINDUNILVR": 2400.0, "ITC": 430.0, "LT": 3200.0
        }

        for sym, cid in company_ids.items():
            base_p = base_prices.get(sym, 1000.0)
            for i in range(250):
                d = today - datetime.timedelta(days=(250 - i))
                if d.weekday() >= 5:  # Skip weekends
                    continue
                d_str = d.isoformat()
                price = round(base_p + (i * 0.4), 2)
                cur.execute("""
                    INSERT OR REPLACE INTO daily_prices (
                        company_id, date, open, high, low, close, volume, adjusted_close
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, d_str, price - 4.0, price + 8.0, price - 6.0, price, 1500000, price))

        # 6. Insert Verified Point-in-Time Financial Vintages for 4 core stocks
        verified_vintages = {
            "TCS": [
                ("Q1FY26", 62000.0, 12000.0, 32.5, "2025-07-15"),
                ("Q2FY26", 64000.0, 12500.0, 33.8, "2025-10-15"),
                ("Q3FY26", 65500.0, 12800.0, 34.6, "2026-01-15"),
                ("Q4FY26", 67000.0, 13200.0, 35.7, "2026-04-15"),
            ],
            "INFY": [
                ("Q1FY26", 39000.0, 6300.0, 15.2, "2025-07-18"),
                ("Q2FY26", 40500.0, 6500.0, 15.7, "2025-10-18"),
                ("Q3FY26", 41200.0, 6650.0, 16.1, "2026-01-18"),
                ("Q4FY26", 42000.0, 6800.0, 16.5, "2026-04-18"),
            ],
            "RELIANCE": [
                ("Q1FY26", 230000.0, 17500.0, 25.8, "2025-07-25"),
                ("Q2FY26", 235000.0, 18000.0, 26.6, "2025-10-25"),
                ("Q3FY26", 240000.0, 18500.0, 27.3, "2026-01-25"),
                ("Q4FY26", 248000.0, 19200.0, 28.4, "2026-04-25"),
            ],
            "HDFCBANK": [
                ("Q1FY26", 82000.0, 16200.0, 21.3, "2025-07-20"),
                ("Q2FY26", 85000.0, 16800.0, 22.1, "2025-10-20"),
                ("Q3FY26", 87500.0, 17400.0, 22.9, "2026-01-20"),
                ("Q4FY26", 90000.0, 18000.0, 23.7, "2026-04-20"),
            ],
            "SUNPHARMA": [
                # Incomplete financials: only 2 quarters (cold-start / incomplete testing)
                ("Q3FY26", 13000.0, 2600.0, 10.8, "2026-01-30"),
                ("Q4FY26", 13500.0, 2750.0, 11.4, "2026-04-30"),
            ]
        }

        for sym, quarters in verified_vintages.items():
            cid = company_ids[sym]
            for q, rev, np, eps, pub_date in quarters:
                cur.execute("""
                    INSERT INTO quarterly_results (
                        company_id, quarter, revenue, net_profit, eps
                    ) VALUES (?, ?, ?, ?, ?)
                """, (cid, q, rev, np, eps))

        # 7. Universe Audit Log entry
        cur.execute("""
            INSERT INTO universe_audit_log (
                symbol, action, old_values_json, new_values_json, initiated_by, notes, timestamp
            ) VALUES (
                'SYSTEM', 'STAGING_PROVISION', NULL,
                '{"environment": "STAGING", "stock_count": 10}',
                'DEVOPS_ORCHESTRATOR', 'Automated staging universe provisioning',
                datetime('now')
            )
        """)

        conn.commit()
        conn.close()

        # 8. Run first-boot validation to confirm readiness
        from backend.database.first_boot_validation import validate_database_readiness
        validation = validate_database_readiness(out_path)
        if not validation["is_ready"]:
            raise RuntimeError(f"Staging database failed post-creation validation: {validation['detail']}")

        print(f"Staging database successfully provisioned at: {out_path}")
        print(f"Companies seeded: {validation['companies_count']}")
        return out_path

    finally:
        if prev_env is not None:
            os.environ["DATABASE_PATH"] = prev_env
        elif "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]

if __name__ == "__main__":
    provision_staging_database()
