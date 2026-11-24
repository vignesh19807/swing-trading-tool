"""
scripts/migration/04_sync_companies.py
======================================
Synchronizes company universe from authoritative source into destination.
Features:
- Full 100-stock authoritative universe reconciliation.
- Dependency-aware synthetic records investigation & classification.
- Strictly ZERO deletions performed.
- Dry-run by default. Explicit --commit required for write execution.
- Rejection of production Neon targets in this phase.
"""

import os
import sys
import sqlite3
import argparse
from typing import Dict, List, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.migration.common import setup_migration_logger, classify_pilot_record, SyntheticDisposition, validate_test_target_url, mask_database_url
from backend.database.connection import open_db_connection
from backend.data_pipeline.stock_universe import STOCK_UNIVERSE

logger = setup_migration_logger("04_sync_companies")

def read_source_companies(sqlite_path: str) -> List[Dict]:
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, symbol, company_name, sector, industry, exchange, sector_id, industry_id 
        FROM companies 
        ORDER BY symbol;
    """)
    comps = [{
        'id': r[0],
        'symbol': r[1],
        'company_name': r[2],
        'sector': r[3],
        'industry': r[4],
        'exchange': r[5],
        'sector_id': r[6],
        'industry_id': r[7]
    } for r in cur.fetchall()]
    conn.close()
    return comps

def investigate_destination_pilot_records(dest_companies: List[Dict]) -> List[Dict]:
    """Generates dependency-aware classification for any non-authoritative records."""
    auth_symbols = {item['symbol'] for item in STOCK_UNIVERSE}
    investigations = []
    for c in dest_companies:
        sym = c['symbol']
        if sym not in auth_symbols:
            classification = classify_pilot_record(sym)
            investigations.append({
                'id': c.get('id'),
                'symbol': sym,
                'name': c.get('company_name'),
                'is_active': c.get('is_active', True),
                'disposition': classification['disposition'],
                'reason': classification['reason']
            })
    return investigations

def sync_companies_to_sqlite(
    dest_path: str, 
    source_companies: List[Dict], 
    commit: bool = False
) -> Dict:
    conn = sqlite3.connect(dest_path)
    cur = conn.cursor()
    cur.execute("BEGIN TRANSACTION;")
    try:
        # Check existing
        cur.execute("SELECT id, symbol, company_name FROM companies;")
        existing_map = {r[1]: r[0] for r in cur.fetchall()}
        
        missing_to_insert = []
        matching = []
        
        for sc in source_companies:
            sym = sc['symbol']
            if sym in existing_map:
                matching.append(sym)
            else:
                missing_to_insert.append(sc)

        logger.info(f"Existing matching companies: {len(matching)}")
        logger.info(f"Missing companies to insert: {len(missing_to_insert)}")

        if commit and missing_to_insert:
            # Check if columns is_active exists in dest
            cur.execute("PRAGMA table_info(companies);")
            cols = [r[1] for r in cur.fetchall()]
            has_is_active = "is_active" in cols
            
            for c in missing_to_insert:
                if has_is_active:
                    cur.execute("""
                        INSERT INTO companies (symbol, company_name, sector, industry, exchange, sector_id, industry_id, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1);
                    """, (c['symbol'], c['company_name'], c['sector'], c['industry'], c['exchange'], c['sector_id'], c['industry_id']))
                else:
                    cur.execute("""
                        INSERT INTO companies (symbol, company_name, sector, industry, exchange, sector_id, industry_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (c['symbol'], c['company_name'], c['sector'], c['industry'], c['exchange'], c['sector_id'], c['industry_id']))

            conn.commit()
            logger.info(f"[COMMITTED] Successfully inserted {len(missing_to_insert)} companies.")
        else:
            conn.rollback()
            logger.info("[DRY-RUN] No writes committed. Transaction rolled back cleanly.")

        # Re-query final destination state
        cur.execute("SELECT id, symbol, company_name FROM companies;")
        dest_companies = [{'id': r[0], 'symbol': r[1], 'company_name': r[2]} for r in cur.fetchall()]
        pilot_report = investigate_destination_pilot_records(dest_companies)

        return {
            'matching_count': len(matching),
            'inserted_count': len(missing_to_insert) if commit else 0,
            'missing_count': len(missing_to_insert),
            'pilot_records_investigation': pilot_report
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during company sync: {e}")
        raise
    finally:
        conn.close()

def sync_companies_to_postgres(
    dest_pg_url: str,
    source_companies: List[Dict],
    commit: bool = False,
    batch_id: str = None
) -> Dict:
    validate_test_target_url(dest_pg_url)
    with open_db_connection(dest_pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, symbol, company_name FROM companies;")
            existing_map = {r['symbol']: r['id'] for r in cur.fetchall()}

            missing_to_insert = [sc for sc in source_companies if sc['symbol'] not in existing_map]
            matching = [sc['symbol'] for sc in source_companies if sc['symbol'] in existing_map]

            logger.info(f"Existing matching companies: {len(matching)}")
            logger.info(f"Missing companies to insert: {len(missing_to_insert)}")

            # Resolve sectors and industries maps for foreign keys
            cur.execute("SELECT id, name FROM sectors;")
            sector_name_map = {r['name']: r['id'] for r in cur.fetchall()}

            cur.execute("SELECT id, name, sector_id FROM industries;")
            industry_name_map = {(r['name'], r['sector_id']): r['id'] for r in cur.fetchall()}

            if commit and missing_to_insert:
                for c in missing_to_insert:
                    s_id = sector_name_map.get(c.get('sector'))
                    ind_id = industry_name_map.get((c.get('industry'), s_id)) if s_id else None
                    cur.execute("""
                        INSERT INTO companies (symbol, company_name, sector, industry, exchange, sector_id, industry_id, is_active, migration_batch_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                        ON CONFLICT (symbol) DO NOTHING;
                    """, (c['symbol'], c['company_name'], c.get('sector'), c.get('industry'), c.get('exchange', 'NSE'), s_id, ind_id, batch_id))
                conn.commit()
                logger.info(f"[COMMITTED] Successfully inserted {len(missing_to_insert)} companies into PostgreSQL.")
            else:
                conn.rollback()
                logger.info("[DRY-RUN] No writes committed. PostgreSQL transaction rolled back cleanly.")

            cur.execute("SELECT id, symbol, company_name FROM companies;")
            dest_companies = [{'id': r['id'], 'symbol': r['symbol'], 'company_name': r['company_name']} for r in cur.fetchall()]
            pilot_report = investigate_destination_pilot_records(dest_companies)

            return {
                'matching_count': len(matching),
                'inserted_count': len(missing_to_insert) if commit else 0,
                'missing_count': len(missing_to_insert),
                'pilot_records_investigation': pilot_report
            }

def main():
    parser = argparse.ArgumentParser(description="Synchronize 100-stock company universe.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite DB path")
    parser.add_argument("--dest-sqlite", help="Destination test SQLite DB path (for isolated testing)")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination test PostgreSQL URL (for isolated testing)")
    parser.add_argument("--batch-id", help="Unique migration batch ID for targeted rollback isolation")
    parser.add_argument("--commit", action="store_true", help="Execute write transaction (default is dry-run)")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Company Universe Synchronization ===")
    logger.info(f"Execution Mode: {'COMMIT' if args.commit else 'DRY-RUN (Safe)'}")

    src_comps = read_source_companies(args.source_sqlite)
    logger.info(f"Loaded {len(src_comps)} authoritative companies from source.")

    if args.dest_pg_url:
        logger.info(f"Target Destination (PostgreSQL): {mask_database_url(args.dest_pg_url)}")
        res = sync_companies_to_postgres(args.dest_pg_url, src_comps, commit=args.commit, batch_id=args.batch_id)
        logger.info(f"PostgreSQL Result summary: matching={res['matching_count']}, missing={res['missing_count']}, inserted={res['inserted_count']}")
        if res['pilot_records_investigation']:
            logger.info("\n--- Synthetic / Pilot Record Investigation Report ---")
            for p in res['pilot_records_investigation']:
                logger.info(f"Symbol: {p['symbol']:12} | Disposition: {p['disposition']:22} | Reason: {p['reason']}")
    elif args.dest_sqlite:
        logger.info(f"Target Destination (SQLite): {args.dest_sqlite}")
        res = sync_companies_to_sqlite(args.dest_sqlite, src_comps, commit=args.commit)
        logger.info(f"SQLite Result summary: matching={res['matching_count']}, missing={res['missing_count']}, inserted={res['inserted_count']}")
        if res['pilot_records_investigation']:
            logger.info("\n--- Synthetic / Pilot Record Investigation Report ---")
            for p in res['pilot_records_investigation']:
                logger.info(f"Symbol: {p['symbol']:12} | Disposition: {p['disposition']:22} | Reason: {p['reason']}")
    else:
        logger.info("[DRY-RUN] No isolated destination specified. Evaluated source universe integrity only.")

if __name__ == "__main__":
    main()
