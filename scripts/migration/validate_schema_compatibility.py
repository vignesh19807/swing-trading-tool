"""
scripts/migration/02_validate_schema_compatibility.py
=====================================================
Validates schema compatibility between SQLite (source) and PostgreSQL (target).
Identifies missing tables, column discrepancies, constraint requirements,
and emits pre-migration DDL.

Usage:
    python scripts/migration/02_validate_schema_compatibility.py
"""

import os
import sys
import sqlite3
import argparse

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.migration.common import setup_migration_logger
from backend.database.connection import open_db_connection

logger = setup_migration_logger("02_validate_schema_compatibility")

def get_sqlite_schema(db_path: str):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    
    table_cols = {}
    for t in tables:
        cur.execute(f"PRAGMA table_info('{t}');")
        table_cols[t] = {r[1]: r[2] for r in cur.fetchall()}
    conn.close()
    return tables, table_cols

def get_pg_schema(target_url: str = None):
    if target_url:
        from scripts.migration.common import validate_test_target_url
        validate_test_target_url(target_url)
    with open_db_connection(target_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SET default_transaction_read_only = on;")
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [r[0] for r in cur.fetchall()]
            
            table_cols = {}
            for t in tables:
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (t,))
                table_cols[t] = {r[0]: r[1] for r in cur.fetchall()}
            return tables, table_cols

def main():
    parser = argparse.ArgumentParser(description="Validate schema compatibility between SQLite and PostgreSQL.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite DB path")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination PostgreSQL URL for testing")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Schema Compatibility Validation ===")
    
    sq_tables, sq_cols = get_sqlite_schema(args.source_sqlite)
    pg_tables, pg_cols = get_pg_schema(args.dest_pg_url)

    logger.info(f"SQLite Tables ({len(sq_tables)}): {sq_tables}")
    logger.info(f"PostgreSQL Tables ({len(pg_tables)}): {pg_tables}")

    missing_in_pg = set(sq_tables) - set(pg_tables)
    extra_in_pg = set(pg_tables) - set(sq_tables)
    common_tables = set(sq_tables).intersection(set(pg_tables))

    if missing_in_pg:
        logger.warning(f"Tables present in SQLite but MISSING in PostgreSQL: {sorted(missing_in_pg)}")
    if extra_in_pg:
        logger.info(f"Tables present in PostgreSQL but not in SQLite: {sorted(extra_in_pg)}")

    logger.info("\n--- Column Discrepancies in Shared Tables ---")
    missing_cols_report = {}
    for t in sorted(common_tables):
        sq_c = set(sq_cols[t].keys())
        pg_c = set(pg_cols[t].keys())
        missing_in_dst = sq_c - pg_c
        missing_in_src = pg_c - sq_c
        
        if missing_in_dst or missing_in_src:
            logger.info(f"Table '{t}':")
            if missing_in_dst:
                logger.warning(f"  Missing in PostgreSQL: {sorted(missing_in_dst)}")
                missing_cols_report[t] = sorted(missing_in_dst)
            if missing_in_src:
                logger.info(f"  Extra in PostgreSQL: {sorted(missing_in_src)}")

    # Specific check for quarterly_financial_vintages
    if "quarterly_financial_vintages" in missing_cols_report:
        logger.warning("\n[CRITICAL] quarterly_financial_vintages in PostgreSQL is missing required columns:")
        for col in missing_cols_report["quarterly_financial_vintages"]:
            logger.warning(f"  - {col}")

    # Emit DDL Recommendations
    logger.info("\n--- Required Pre-Migration DDL ---")
    ddl = [
        "ALTER TABLE quarterly_financial_vintages ADD COLUMN IF NOT EXISTS publication_date DATE;",
        "ALTER TABLE quarterly_financial_vintages ADD COLUMN IF NOT EXISTS market_session VARCHAR(20) DEFAULT 'POST_MARKET';",
        "ALTER TABLE quarterly_financial_vintages ADD COLUMN IF NOT EXISTS original_currency VARCHAR(10) DEFAULT 'INR';",
        "ALTER TABLE quarterly_financial_vintages ADD COLUMN IF NOT EXISTS original_extracted_value DOUBLE PRECISION;",
        "ALTER TABLE quarterly_financial_vintages ADD COLUMN IF NOT EXISTS conversion_rate DOUBLE PRECISION DEFAULT 1.0;",
        "ALTER TABLE quarterly_financial_vintages ADD COLUMN IF NOT EXISTS conversion_date DATE;",
        "",
        "CREATE TABLE IF NOT EXISTS quarantined_quarterly_results (",
        "    id BIGSERIAL PRIMARY KEY,",
        "    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,",
        "    quarter VARCHAR(20) NOT NULL,",
        "    revenue DOUBLE PRECISION,",
        "    net_profit DOUBLE PRECISION,",
        "    eps DOUBLE PRECISION,",
        "    roe DOUBLE PRECISION,",
        "    roce DOUBLE PRECISION,",
        "    debt_equity DOUBLE PRECISION,",
        "    operating_margin DOUBLE PRECISION,",
        "    net_margin DOUBLE PRECISION,",
        "    publication_date DATE,",
        "    quarantine_reason TEXT,",
        "    quarantined_at TIMESTAMPTZ DEFAULT NOW(),",
        "    CONSTRAINT uq_quarantined_company_quarter UNIQUE (company_id, quarter)",
        ");"
    ]
    for line in ddl:
        logger.info("  " + line)

    logger.info("\n[SUCCESS] Schema compatibility validation completed.")

if __name__ == "__main__":
    main()
