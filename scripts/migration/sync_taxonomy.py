"""
scripts/migration/03_sync_taxonomy.py
=====================================
Synchronizes sectors and industries taxonomy from source to destination.
Ensures foreign key referential integrity before company synchronization.

Dry-run by default. Explicit --commit required to execute.
Safety guard prevents execution against staging Neon database.
"""

import os
import sys
import sqlite3
import argparse
from typing import Dict, List, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.migration.common import setup_migration_logger, mask_database_url, validate_test_target_url
from backend.database.connection import open_db_connection

logger = setup_migration_logger("03_sync_taxonomy")

def read_source_taxonomy(sqlite_path: str) -> Tuple[List[Dict], List[Dict]]:
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM sectors ORDER BY id;")
    sectors = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
    
    cur.execute("SELECT id, sector_id, name FROM industries ORDER BY id;")
    industries = [{'id': r[0], 'sector_id': r[1], 'name': r[2]} for r in cur.fetchall()]
    conn.close()
    return sectors, industries

def sync_taxonomy_to_postgres(pg_url: str, sectors: List[Dict], industries: List[Dict], commit: bool = False, batch_id: str = None):
    validate_test_target_url(pg_url)
    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM sectors;")
            existing_sectors = {r['name']: r['id'] for r in cur.fetchall()}

            sectors_inserted = 0
            sectors_matched = 0
            sector_id_map = {}

            for s in sectors:
                s_name = s['name']
                s_id = s['id']
                if s_name in existing_sectors:
                    sectors_matched += 1
                    sector_id_map[s_id] = existing_sectors[s_name]
                else:
                    if commit:
                        cur.execute("INSERT INTO sectors (name, migration_batch_id) VALUES (%s, %s) RETURNING id;", (s_name, batch_id))
                        new_id = cur.fetchone()[0]
                        sector_id_map[s_id] = new_id
                        existing_sectors[s_name] = new_id
                    else:
                        sector_id_map[s_id] = -1
                    sectors_inserted += 1

            cur.execute("SELECT id, sector_id, name FROM industries;")
            existing_industries = {(r['name'], r['sector_id']): r['id'] for r in cur.fetchall()}

            industries_inserted = 0
            industries_matched = 0
            industry_id_map = {}

            for ind in industries:
                ind_name = ind['name']
                src_s_id = ind['sector_id']
                dest_s_id = sector_id_map.get(src_s_id)
                if dest_s_id is None or dest_s_id == -1:
                    continue
                key = (ind_name, dest_s_id)
                if key in existing_industries:
                    industries_matched += 1
                    industry_id_map[ind['id']] = existing_industries[key]
                else:
                    if commit:
                        cur.execute("INSERT INTO industries (sector_id, name, migration_batch_id) VALUES (%s, %s, %s) RETURNING id;", (dest_s_id, ind_name, batch_id))
                        new_ind_id = cur.fetchone()[0]
                        industry_id_map[ind['id']] = new_ind_id
                        existing_industries[key] = new_ind_id
                    else:
                        industry_id_map[ind['id']] = -1
                    industries_inserted += 1

            if commit:
                conn.commit()
                logger.info("[COMMITTED] PostgreSQL taxonomy synchronization committed successfully.")
            else:
                conn.rollback()
                logger.info("[DRY-RUN] PostgreSQL transaction rolled back cleanly. No writes persisted.")

            return {
                'sectors_matched': sectors_matched,
                'sectors_inserted': sectors_inserted,
                'industries_matched': industries_matched,
                'industries_inserted': industries_inserted,
                'sector_id_map': sector_id_map,
                'industry_id_map': industry_id_map
            }

def sync_taxonomy_to_sqlite(dest_path: str, sectors: List[Dict], industries: List[Dict], commit: bool = False):
    conn = sqlite3.connect(dest_path)
    cur = conn.cursor()
    cur.execute("BEGIN TRANSACTION;")
    try:
        # 1. Sync Sectors
        cur.execute("SELECT id, name FROM sectors;")
        existing_sectors = {r[1]: r[0] for r in cur.fetchall()}
        
        sectors_inserted = 0
        sectors_matched = 0
        sector_id_map = {} # source_sector_id -> dest_sector_id
        
        for s in sectors:
            s_name = s['name']
            s_id = s['id']
            if s_name in existing_sectors:
                sectors_matched += 1
                sector_id_map[s_id] = existing_sectors[s_name]
            else:
                if commit:
                    cur.execute("INSERT INTO sectors (name) VALUES (?);", (s_name,))
                    new_id = cur.lastrowid
                    sector_id_map[s_id] = new_id
                    existing_sectors[s_name] = new_id
                else:
                    sector_id_map[s_id] = -1
                sectors_inserted += 1

        # 2. Sync Industries
        cur.execute("SELECT id, sector_id, name FROM industries;")
        existing_industries = {(r[2], r[1]): r[0] for r in cur.fetchall()}
        
        industries_inserted = 0
        industries_matched = 0
        industry_id_map = {} # source_industry_id -> dest_industry_id
        
        for ind in industries:
            ind_name = ind['name']
            src_s_id = ind['sector_id']
            src_ind_id = ind['id']
            dest_s_id = sector_id_map.get(src_s_id)
            
            key = (ind_name, dest_s_id)
            if key in existing_industries:
                industries_matched += 1
                industry_id_map[src_ind_id] = existing_industries[key]
            else:
                if commit:
                    cur.execute("INSERT INTO industries (sector_id, name) VALUES (?, ?);", (dest_s_id, ind_name))
                    new_ind_id = cur.lastrowid
                    industry_id_map[src_ind_id] = new_ind_id
                    existing_industries[key] = new_ind_id
                else:
                    industry_id_map[src_ind_id] = -1
                industries_inserted += 1

        if commit:
            conn.commit()
            logger.info("[COMMITTED] Taxonomy synchronization committed successfully.")
        else:
            conn.rollback()
            logger.info("[DRY-RUN] Transaction rolled back cleanly. No writes persisted.")

        logger.info(f"Sectors: {sectors_matched} matched, {sectors_inserted} new to insert.")
        logger.info(f"Industries: {industries_matched} matched, {industries_inserted} new to insert.")
        return {
            'sectors_matched': sectors_matched,
            'sectors_inserted': sectors_inserted,
            'industries_matched': industries_matched,
            'industries_inserted': industries_inserted,
            'sector_id_map': sector_id_map,
            'industry_id_map': industry_id_map
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during taxonomy sync: {e}")
        raise
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Synchronize sector and industry taxonomy.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite DB path")
    parser.add_argument("--dest-sqlite", help="Destination test SQLite DB path (for isolated testing)")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination test PostgreSQL URL (for isolated testing)")
    parser.add_argument("--batch-id", help="Unique migration batch ID for targeted rollback isolation")
    parser.add_argument("--commit", action="store_true", help="Execute write transaction (default is dry-run)")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Sector & Industry Taxonomy Synchronization ===")
    logger.info(f"Execution Mode: {'COMMIT' if args.commit else 'DRY-RUN (Safe)'}")
    
    sectors, industries = read_source_taxonomy(args.source_sqlite)
    logger.info(f"Loaded {len(sectors)} sectors and {len(industries)} industries from source.")

    if args.dest_pg_url:
        logger.info(f"Target Destination (PostgreSQL): {mask_database_url(args.dest_pg_url)}")
        res = sync_taxonomy_to_postgres(args.dest_pg_url, sectors, industries, commit=args.commit, batch_id=args.batch_id)
        logger.info(f"PostgreSQL Result summary: {res}")
    elif args.dest_sqlite:
        logger.info(f"Target Destination (SQLite): {args.dest_sqlite}")
        res = sync_taxonomy_to_sqlite(args.dest_sqlite, sectors, industries, commit=args.commit)
        logger.info(f"SQLite Result summary: {res}")
    else:
        logger.info("[DRY-RUN] No isolated destination specified. Evaluated source taxonomy integrity only.")

if __name__ == "__main__":
    main()
