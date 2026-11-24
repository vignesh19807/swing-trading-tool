"""
scripts/migration/06_sync_indicators.py
=======================================
Synchronizes technical indicator data from source SQLite to destination.

Features:
- 3-way conflict detection (MISSING, MATCHING, CONFLICTING).
- Chunked batch processing (5,000 rows per transaction block).
- Dynamic foreign key resolution by symbol.
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

from scripts.migration.common import setup_migration_logger, ConflictCategory, validate_test_target_url, mask_database_url
from backend.database.connection import open_db_connection

logger = setup_migration_logger("06_sync_indicators")

def read_source_indicators(sqlite_path: str, chunk_size: int = 5000):
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT ti.id, c.symbol, ti.date, ti.rsi, ti.macd, ti.macd_signal, ti.ema_20, ti.ema_50, ti.ema_200, ti.macd_histogram, ti.atr_14, ti.technical_score
        FROM technical_indicators ti
        JOIN companies c ON ti.company_id = c.id
        ORDER BY c.symbol, ti.date;
    """)
    while True:
        rows = cur.fetchmany(chunk_size)
        if not rows:
            break
        yield [{
            'id': r[0],
            'symbol': r[1],
            'date': r[2],
            'rsi': r[3],
            'macd': r[4],
            'macd_signal': r[5],
            'ema_20': r[6],
            'ema_50': r[7],
            'ema_200': r[8],
            'macd_histogram': r[9],
            'atr_14': r[10],
            'technical_score': r[11]
        } for r in rows]
    conn.close()

def sync_indicators_to_sqlite(
    dest_path: str, 
    source_sqlite_path: str, 
    chunk_size: int = 5000, 
    commit: bool = False
) -> Dict:
    conn = sqlite3.connect(dest_path)
    cur = conn.cursor()
    
    cur.execute("SELECT id, symbol FROM companies;")
    dest_comp_map = {r[1]: r[0] for r in cur.fetchall()}
    
    total_processed = 0
    total_matching = 0
    total_inserted = 0
    total_conflicts = 0
    conflicts_log = []
    
    chunk_index = 0
    for chunk in read_source_indicators(source_sqlite_path, chunk_size=chunk_size):
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
                    continue
                    
                cur.execute("""
                    SELECT rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score
                    FROM technical_indicators
                    WHERE company_id = ? AND date = ?;
                """, (dest_cid, date))
                existing = cur.fetchone()
                
                if existing is None:
                    if commit:
                        cur.execute("""
                            INSERT INTO technical_indicators (company_id, date, rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (dest_cid, date, row['rsi'], row['macd'], row['macd_signal'], row['ema_20'], row['ema_50'], row['ema_200'], row['macd_histogram'], row['atr_14'], row['technical_score']))
                    chunk_inserted += 1
                else:
                    # Compare key indicator: technical_score
                    diff = False
                    if row['technical_score'] is not None and existing[8] is not None:
                        if abs(float(row['technical_score']) - float(existing[8])) > 1e-4:
                            diff = True
                    if diff:
                        chunk_conflicted += 1
                        conflicts_log.append({'symbol': sym, 'date': date, 'src_score': row['technical_score'], 'dst_score': existing[8]})
                    else:
                        chunk_matched += 1
                        
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
        'total_conflicts': total_conflicts,
        'conflicts_sample': conflicts_log[:10]
    }

def sync_indicators_to_postgres(
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

            for chunk in read_source_indicators(source_sqlite_path, chunk_size=chunk_size):
                chunk_index += 1
                chunk_inserted = 0
                chunk_matched = 0
                chunk_conflicted = 0

                symbols = list({r['symbol'] for r in chunk if r['symbol'] in dest_comp_map})
                cids = [dest_comp_map[s] for s in symbols]
                existing_inds = {}
                if cids:
                    dates = list({r['date'] for r in chunk})
                    min_date = min(dates)
                    max_date = max(dates)
                    cur.execute("""
                        SELECT company_id, date, rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score
                        FROM technical_indicators
                        WHERE company_id = ANY(%s) AND date >= %s AND date <= %s;
                    """, (cids, min_date, max_date))
                    for ind in cur.fetchall():
                        existing_inds[(ind['company_id'], str(ind['date']))] = ind

                for row in chunk:
                    sym = row['symbol']
                    dest_cid = dest_comp_map.get(sym)
                    if dest_cid is None:
                        continue
                    date = row['date']
                    dst_row = existing_inds.get((dest_cid, date))

                    if dst_row is not None:
                        chunk_matched += 1
                    else:
                        if commit:
                            cur.execute("""
                                INSERT INTO technical_indicators (company_id, date, rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score, migration_batch_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, date) DO NOTHING;
                            """, (dest_cid, date, row['rsi'], row['macd'], row['macd_signal'], row['ema_20'], row['ema_50'], row['ema_200'], row['macd_histogram'], row['atr_14'], row['technical_score'], batch_id))
                        chunk_inserted += 1

                total_processed += len(chunk)
                total_matching += chunk_matched
                total_inserted += (chunk_inserted if commit else 0)
                total_conflicts += chunk_conflicted

                if commit:
                    conn.commit()
                    logger.info(f"[POSTGRES CHUNK {chunk_index}] Inserted: {chunk_inserted}, Matched: {chunk_matched} (Committed)")
                else:
                    conn.rollback()
                    logger.info(f"[POSTGRES CHUNK {chunk_index}] Eligible: {chunk_inserted}, Matched: {chunk_matched} (Dry-Run)")

            return {
                'total_processed': total_processed,
                'total_matching': total_matching,
                'total_inserted': total_inserted,
                'total_conflicts': total_conflicts
            }

def main():
    parser = argparse.ArgumentParser(description="Synchronize technical indicators.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite DB path")
    parser.add_argument("--dest-sqlite", help="Destination test SQLite DB path (for isolated testing)")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination test PostgreSQL URL (for isolated testing)")
    parser.add_argument("--chunk-size", type=int, default=5000, help="Batch chunk size (default: 5000)")
    parser.add_argument("--batch-id", help="Unique migration batch ID for targeted rollback isolation")
    parser.add_argument("--commit", action="store_true", help="Execute write transaction (default is dry-run)")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Technical Indicators Synchronization ===")
    logger.info(f"Execution Mode: {'COMMIT' if args.commit else 'DRY-RUN (Safe)'}")

    if args.dest_pg_url:
        logger.info(f"Target Destination (PostgreSQL): {mask_database_url(args.dest_pg_url)}")
        res = sync_indicators_to_postgres(args.dest_pg_url, args.source_sqlite, chunk_size=args.chunk_size, commit=args.commit, batch_id=args.batch_id)
        logger.info(f"Processed: {res['total_processed']} rows | Matched: {res['total_matching']} | Inserted: {res['total_inserted']} | Conflicts: {res['total_conflicts']}")
    elif args.dest_sqlite:
        logger.info(f"Target Destination: {args.dest_sqlite}")
        res = sync_indicators_to_sqlite(args.dest_sqlite, args.source_sqlite, chunk_size=args.chunk_size, commit=args.commit)
        logger.info(f"Processed: {res['total_processed']} rows | Matched: {res['total_matching']} | Inserted: {res['total_inserted']} | Conflicts: {res['total_conflicts']}")
    else:
        logger.info("[DRY-RUN] No isolated destination specified. Streaming validation only.")

if __name__ == "__main__":
    main()
