"""
scripts/migration/05_sync_market_data.py
========================================
Synchronizes daily OHLCV prices from source SQLite to destination.

Features:
- Three-category conflict detection:
    1. MISSING -> Eligible for insertion.
    2. MATCHING -> Exact match; skip without modification.
    3. CONFLICTING -> Quarantined for owner review; NEVER overwritten.
- Chunked batch processing (default: 5,000 rows per transaction block).
- Dynamic foreign key resolution by symbol.
- Numeric and timestamp normalization.
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

from scripts.migration.common import (
    setup_migration_logger, 
    classify_market_record, 
    ConflictCategory, 
    canonical_market_data_serialize,
    validate_test_target_url,
    mask_database_url
)
from backend.database.connection import open_db_connection

logger = setup_migration_logger("05_sync_market_data")

def read_source_market_data(sqlite_path: str, chunk_size: int = 5000):
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT dp.id, c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume, dp.adjusted_close
        FROM daily_prices dp
        JOIN companies c ON dp.company_id = c.id
        ORDER BY c.symbol, dp.date;
    """)
    while True:
        rows = cur.fetchmany(chunk_size)
        if not rows:
            break
        yield [{
            'id': r[0],
            'symbol': r[1],
            'date': r[2],
            'open': r[3],
            'high': r[4],
            'low': r[5],
            'close': r[6],
            'volume': r[7],
            'adjusted_close': r[8]
        } for r in rows]
    conn.close()

def sync_market_data_to_sqlite(
    dest_path: str, 
    source_sqlite_path: str, 
    chunk_size: int = 5000, 
    commit: bool = False
) -> Dict:
    conn = sqlite3.connect(dest_path)
    cur = conn.cursor()
    
    # 1. Resolve destination companies
    cur.execute("SELECT id, symbol FROM companies;")
    dest_comp_map = {r[1]: r[0] for r in cur.fetchall()}
    
    total_processed = 0
    total_matching = 0
    total_inserted = 0
    total_conflicts = 0
    conflicts_log = []
    
    logger.info(f"Destination has {len(dest_comp_map)} mapped company symbols.")
    
    chunk_index = 0
    for chunk in read_source_market_data(source_sqlite_path, chunk_size=chunk_size):
        chunk_index += 1
        cur.execute("BEGIN TRANSACTION;")
        try:
            chunk_inserted = 0
            chunk_matched = 0
            chunk_conflicted = 0
            
            for row in chunk:
                sym = row['symbol']
                date = row['date']
                dest_cid = dest_comp_map.get(sym)
                
                if dest_cid is None:
                    # Company not present in destination; skip or log
                    continue
                
                # Check destination existence
                cur.execute("""
                    SELECT open, high, low, close, volume, adjusted_close
                    FROM daily_prices
                    WHERE company_id = ? AND date = ?;
                """, (dest_cid, date))
                existing = cur.fetchone()
                
                dst_row = None
                if existing:
                    dst_row = {
                        'open': existing[0],
                        'high': existing[1],
                        'low': existing[2],
                        'close': existing[3],
                        'volume': existing[4],
                        'adjusted_close': existing[5]
                    }
                
                cat, diff = classify_market_record(row, dst_row)
                
                if cat == ConflictCategory.MATCHING:
                    chunk_matched += 1
                elif cat == ConflictCategory.CONFLICTING:
                    chunk_conflicted += 1
                    conflicts_log.append({
                        'symbol': sym,
                        'date': date,
                        'diff': diff
                    })
                    # Strict Rule B: Never overwrite conflicting destination records!
                elif cat == ConflictCategory.MISSING:
                    if commit:
                        cur.execute("""
                            INSERT INTO daily_prices (company_id, date, open, high, low, close, volume, adjusted_close)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, (dest_cid, date, row['open'], row['high'], row['low'], row['close'], row['volume'], row['adjusted_close']))
                    chunk_inserted += 1
            
            total_processed += len(chunk)
            total_matching += chunk_matched
            total_inserted += (chunk_inserted if commit else 0)
            total_conflicts += chunk_conflicted
            
            if commit:
                conn.commit()
                logger.info(f"[CHUNK {chunk_index}] Inserted: {chunk_inserted}, Matched: {chunk_matched}, Conflicts: {chunk_conflicted} (Committed)")
            else:
                conn.rollback()
                logger.info(f"[CHUNK {chunk_index}] Eligible: {chunk_inserted}, Matched: {chunk_matched}, Conflicts: {chunk_conflicted} (Dry-Run)")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"[CHUNK {chunk_index} FAILED] Rolled back transaction. Error: {e}")
            raise
            
    conn.close()
    
    return {
        'total_processed': total_processed,
        'total_matching': total_matching,
        'total_inserted': total_inserted,
        'total_eligible_insert': total_processed - total_matching - total_conflicts,
        'total_conflicts': total_conflicts,
        'conflicts_sample': conflicts_log[:10]
    }

def sync_market_data_to_postgres(
    dest_pg_url: str,
    source_sqlite_path: str,
    chunk_size: int = 5000,
    commit: bool = False,
    batch_id: str = None
) -> Dict:
    validate_test_target_url(dest_pg_url)
    with open_db_connection(dest_pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, symbol FROM companies;")
            dest_comp_map = {r['symbol']: r['id'] for r in cur.fetchall()}

            total_processed = 0
            total_matching = 0
            total_inserted = 0
            total_conflicts = 0
            conflicts_log = []
            chunk_index = 0

            for chunk in read_source_market_data(source_sqlite_path, chunk_size=chunk_size):
                chunk_index += 1
                chunk_inserted = 0
                chunk_matched = 0
                chunk_conflicted = 0

                # Pre-fetch existing prices for these companies in this chunk's date span
                symbols = list({r['symbol'] for r in chunk if r['symbol'] in dest_comp_map})
                cids = [dest_comp_map[s] for s in symbols]
                existing_prices = {}
                if cids:
                    dates = list({r['date'] for r in chunk})
                    min_date = min(dates)
                    max_date = max(dates)
                    cur.execute("""
                        SELECT company_id, date, open, high, low, close, volume, adjusted_close
                        FROM daily_prices
                        WHERE company_id = ANY(%s) AND date >= %s AND date <= %s;
                    """, (cids, min_date, max_date))
                    for pr in cur.fetchall():
                        existing_prices[(pr['company_id'], str(pr['date']))] = {
                            'open': pr['open'],
                            'high': pr['high'],
                            'low': pr['low'],
                            'close': pr['close'],
                            'volume': pr['volume'],
                            'adjusted_close': pr['adjusted_close']
                        }

                for row in chunk:
                    sym = row['symbol']
                    dest_cid = dest_comp_map.get(sym)
                    if dest_cid is None:
                        continue
                    date = row['date']
                    dst_row = existing_prices.get((dest_cid, date))
                    cat, diff = classify_market_record(row, dst_row)

                    if cat == ConflictCategory.MATCHING:
                        chunk_matched += 1
                    elif cat == ConflictCategory.CONFLICTING:
                        chunk_conflicted += 1
                        conflicts_log.append({'symbol': sym, 'date': date, 'diff': diff})
                    elif cat == ConflictCategory.MISSING:
                        if commit:
                            cur.execute("""
                                INSERT INTO daily_prices (company_id, date, open, high, low, close, volume, adjusted_close, migration_batch_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, date) DO NOTHING;
                            """, (dest_cid, date, row['open'], row['high'], row['low'], row['close'], row['volume'], row['adjusted_close'], batch_id))
                        chunk_inserted += 1

                total_processed += len(chunk)
                total_matching += chunk_matched
                total_inserted += (chunk_inserted if commit else 0)
                total_conflicts += chunk_conflicted

                if commit:
                    conn.commit()
                    logger.info(f"[POSTGRES CHUNK {chunk_index}] Inserted: {chunk_inserted}, Matched: {chunk_matched}, Conflicts: {chunk_conflicted} (Committed)")
                else:
                    conn.rollback()
                    logger.info(f"[POSTGRES CHUNK {chunk_index}] Eligible: {chunk_inserted}, Matched: {chunk_matched}, Conflicts: {chunk_conflicted} (Dry-Run)")

            return {
                'total_processed': total_processed,
                'total_matching': total_matching,
                'total_inserted': total_inserted,
                'total_eligible_insert': total_processed - total_matching - total_conflicts,
                'total_conflicts': total_conflicts,
                'conflicts_sample': conflicts_log[:10]
            }

def main():
    parser = argparse.ArgumentParser(description="Synchronize daily market price data.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite DB path")
    parser.add_argument("--dest-sqlite", help="Destination test SQLite DB path (for isolated testing)")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination test PostgreSQL URL (for isolated testing)")
    parser.add_argument("--chunk-size", type=int, default=5000, help="Batch chunk size (default: 5000)")
    parser.add_argument("--batch-id", help="Unique migration batch ID for targeted rollback isolation")
    parser.add_argument("--commit", action="store_true", help="Execute write transaction (default is dry-run)")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Market Price Data Synchronization ===")
    logger.info(f"Execution Mode: {'COMMIT' if args.commit else 'DRY-RUN (Safe)'}")

    if args.dest_pg_url:
        logger.info(f"Target Destination (PostgreSQL): {mask_database_url(args.dest_pg_url)}")
        res = sync_market_data_to_postgres(args.dest_pg_url, args.source_sqlite, chunk_size=args.chunk_size, commit=args.commit, batch_id=args.batch_id)
        logger.info(f"Processed: {res['total_processed']} rows | Matched: {res['total_matching']} | Inserted: {res['total_inserted']} | Conflicts: {res['total_conflicts']}")
        if res['total_conflicts'] > 0:
            logger.warning(f"Quarantined {res['total_conflicts']} conflicting records for owner review (NOT overwritten).")
    elif args.dest_sqlite:
        logger.info(f"Target Destination: {args.dest_sqlite}")
        res = sync_market_data_to_sqlite(args.dest_sqlite, args.source_sqlite, chunk_size=args.chunk_size, commit=args.commit)
        logger.info(f"Processed: {res['total_processed']} rows | Matched: {res['total_matching']} | Inserted: {res['total_inserted']} | Conflicts: {res['total_conflicts']}")
        if res['total_conflicts'] > 0:
            logger.warning(f"Quarantined {res['total_conflicts']} conflicting records for owner review (NOT overwritten).")
    else:
        logger.info("[DRY-RUN] No isolated destination specified. Streaming validation only.")

if __name__ == "__main__":
    main()
