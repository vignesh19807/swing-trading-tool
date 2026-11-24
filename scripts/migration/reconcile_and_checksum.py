"""
scripts/migration/08_reconcile_and_checksum.py
==============================================
Computes deterministic, canonical SHA-256 checksums across source and destination
databases to prove 100% bit-exact reconciliation without transferring full datasets.

Specifications:
- Market Data: Canonical serialization of (symbol, date, open, high, low, close, adjusted_close, volume).
- Financial Data: Canonical serialization of (symbol, quarter, version, dates, status, eligibility, financials, hash, url).
- Normalization: 4 decimal places for floats, integer volume, 'NULL' for missing fields, uppercase symbols, ISO dates.
"""

from __future__ import annotations

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
    canonical_market_data_hash, 
    canonical_indicator_hash,
    canonical_financial_vintage_hash,
    canonical_quarantine_hash,
    validate_test_target_url,
    mask_database_url
)
from backend.database.connection import open_db_connection

logger = setup_migration_logger("08_reconcile_and_checksum")

def compute_sqlite_market_checksum(db_path: str, exact: bool = False) -> Tuple[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.adjusted_close, dp.volume
        FROM daily_prices dp
        JOIN companies c ON dp.company_id = c.id;
    """)
    rows = [{
        'symbol': r[0],
        'date': r[1],
        'open': r[2],
        'high': r[3],
        'low': r[4],
        'close': r[5],
        'adjusted_close': r[6],
        'volume': r[7]
    } for r in cur.fetchall()]
    conn.close()
    return canonical_market_data_hash(rows, exact=exact), len(rows)

def compute_sqlite_indicator_checksum(db_path: str, exact: bool = False) -> Tuple[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.symbol, ti.date, ti.rsi, ti.macd, ti.macd_signal, ti.ema_20, ti.ema_50, ti.ema_200, ti.macd_histogram, ti.atr_14, ti.technical_score
        FROM technical_indicators ti
        JOIN companies c ON ti.company_id = c.id;
    """)
    rows = [{
        'symbol': r[0],
        'date': r[1],
        'rsi': r[2],
        'macd': r[3],
        'macd_signal': r[4],
        'ema_20': r[5],
        'ema_50': r[6],
        'ema_200': r[7],
        'macd_histogram': r[8],
        'atr_14': r[9],
        'technical_score': r[10]
    } for r in cur.fetchall()]
    conn.close()
    return canonical_indicator_hash(rows, exact=exact), len(rows)

def compute_sqlite_financial_checksum(db_path: str, exact: bool = False) -> Tuple[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            c.symbol, qfv.quarter, qfv.version_sequence, qfv.period_start_date, qfv.period_end_date,
            qfv.verification_status, qfv.research_eligibility, qfv.publication_timestamp,
            qfv.publication_date, qfv.effective_trading_date, qfv.filing_scope,
            qfv.accounting_standard, qfv.revenue, qfv.operating_profit, qfv.net_profit, qfv.eps,
            qfv.is_banking_institution, qfv.net_interest_income, qfv.total_assets, qfv.total_equity,
            qfv.total_debt, qfv.roe, qfv.roce, qfv.debt_equity, qfv.operating_margin,
            qfv.net_margin, qfv.source_document_hash, qfv.source_document_url
        FROM quarterly_financial_vintages qfv
        JOIN companies c ON qfv.company_id = c.id;
    """)
    cols = [
        "symbol", "quarter", "version_sequence", "period_start_date", "period_end_date",
        "verification_status", "research_eligibility", "publication_timestamp",
        "publication_date", "effective_trading_date", "filing_scope",
        "accounting_standard", "revenue", "operating_profit", "net_profit", "eps",
        "is_banking_institution", "net_interest_income", "total_assets", "total_equity",
        "total_debt", "roe", "roce", "debt_equity", "operating_margin",
        "net_margin", "source_document_hash", "source_document_url"
    ]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return canonical_financial_vintage_hash(rows, exact=exact), len(rows)

def compute_postgres_market_checksum(pg_url: str, exact: bool = False) -> Tuple[str, int]:
    validate_test_target_url(pg_url)
    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.symbol, dp.date, dp.open, dp.high, dp.low, dp.close, dp.adjusted_close, dp.volume
                FROM daily_prices dp
                JOIN companies c ON dp.company_id = c.id;
            """)
            rows = [{
                'symbol': r['symbol'],
                'date': str(r['date']),
                'open': r['open'],
                'high': r['high'],
                'low': r['low'],
                'close': r['close'],
                'adjusted_close': r['adjusted_close'],
                'volume': r['volume']
            } for r in cur.fetchall()]
            return canonical_market_data_hash(rows, exact=exact), len(rows)

def compute_postgres_indicator_checksum(pg_url: str, exact: bool = False) -> Tuple[str, int]:
    validate_test_target_url(pg_url)
    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.symbol, ti.date, ti.rsi, ti.macd, ti.macd_signal, ti.ema_20, ti.ema_50, ti.ema_200, ti.macd_histogram, ti.atr_14, ti.technical_score
                FROM technical_indicators ti
                JOIN companies c ON ti.company_id = c.id;
            """)
            rows = [{
                'symbol': r['symbol'],
                'date': str(r['date']),
                'rsi': r['rsi'],
                'macd': r['macd'],
                'macd_signal': r['macd_signal'],
                'ema_20': r['ema_20'],
                'ema_50': r['ema_50'],
                'ema_200': r['ema_200'],
                'macd_histogram': r['macd_histogram'],
                'atr_14': r['atr_14'],
                'technical_score': r['technical_score']
            } for r in cur.fetchall()]
            return canonical_indicator_hash(rows, exact=exact), len(rows)

def compute_postgres_financial_checksum(pg_url: str, exact: bool = False) -> Tuple[str, int]:
    validate_test_target_url(pg_url)
    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.symbol, qfv.quarter, qfv.version_sequence, qfv.period_start_date, qfv.period_end_date,
                    qfv.verification_status, qfv.research_eligibility, qfv.published_at,
                    qfv.effective_trading_date, qfv.filing_scope,
                    qfv.accounting_standard, qfv.revenue, qfv.operating_profit, qfv.net_profit, qfv.eps,
                    qfv.is_banking_institution, qfv.net_interest_income, qfv.total_assets, qfv.total_equity,
                    qfv.total_debt, qfv.roe, qfv.roce, qfv.debt_equity, qfv.operating_margin,
                    qfv.net_margin, qfv.source_document_hash, qfv.source_document_url
                FROM quarterly_financial_vintages qfv
                JOIN companies c ON qfv.company_id = c.id;
            """)
            rows = []
            for r in cur.fetchall():
                rows.append({
                    'symbol': r['symbol'],
                    'quarter': r['quarter'],
                    'version_sequence': r['version_sequence'],
                    'period_start_date': str(r['period_start_date']),
                    'period_end_date': str(r['period_end_date']),
                    'verification_status': r['verification_status'],
                    'research_eligibility': r['research_eligibility'],
                    'publication_timestamp': str(r['published_at']),
                    'publication_date': None,
                    'effective_trading_date': str(r['effective_trading_date']),
                    'filing_scope': r['filing_scope'],
                    'accounting_standard': r['accounting_standard'],
                    'revenue': r['revenue'],
                    'operating_profit': r['operating_profit'],
                    'net_profit': r['net_profit'],
                    'eps': r['eps'],
                    'is_banking_institution': r['is_banking_institution'],
                    'net_interest_income': r['net_interest_income'],
                    'total_assets': r['total_assets'],
                    'total_equity': r['total_equity'],
                    'total_debt': r['total_debt'],
                    'roe': r['roe'],
                    'roce': r['roce'],
                    'debt_equity': r['debt_equity'],
                    'operating_margin': r['operating_margin'],
                    'net_margin': r['net_margin'],
                    'source_document_hash': r['source_document_hash'],
                    'source_document_url': r['source_document_url']
                })
            return canonical_financial_vintage_hash(rows, exact=exact), len(rows)

def compute_sqlite_quarantine_checksum(db_path: str, exact: bool = False) -> Tuple[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quarantined_quarterly_results';")
    if not cur.fetchone():
        conn.close()
        return "NO_QUARANTINE_TABLE", 0
    cur.execute("PRAGMA table_info(quarantined_quarterly_results);")
    cols_info = [r[1] for r in cur.fetchall()]
    has_orig_id = "original_id" in cols_info
    has_orig_tbl = "original_table" in cols_info
    orig_id_expr = "q.original_id" if has_orig_id else "0"
    orig_tbl_expr = "q.original_table" if has_orig_tbl else "'quarterly_results'"

    cur.execute(f"""
        SELECT c.symbol, q.quarter, q.revenue, q.net_profit, q.eps, q.roe, q.roce,
               q.debt_equity, q.operating_margin, q.net_margin, q.publication_date,
               q.quarantine_reason, {orig_id_expr}, {orig_tbl_expr}
        FROM quarantined_quarterly_results q
        JOIN companies c ON q.company_id = c.id;
    """)
    cols = [
        "symbol", "quarter", "revenue", "net_profit", "eps", "roe", "roce",
        "debt_equity", "operating_margin", "net_margin", "publication_date",
        "quarantine_reason", "original_id", "original_table"
    ]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return canonical_quarantine_hash(rows, exact=exact), len(rows)

def compute_postgres_quarantine_checksum(pg_url: str, exact: bool = False) -> Tuple[str, int]:
    validate_test_target_url(pg_url)
    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'quarantined_quarterly_results';
            """)
            if not cur.fetchone():
                return "NO_QUARANTINE_TABLE", 0
            cur.execute("""
                SELECT c.symbol, q.quarter, q.revenue, q.net_profit, q.eps, q.roe, q.roce,
                       q.debt_equity, q.operating_margin, q.net_margin, q.publication_date,
                       q.quarantine_reason, q.original_id, q.original_table
                FROM quarantined_quarterly_results q
                JOIN companies c ON q.company_id = c.id;
            """)
            rows = []
            for r in cur.fetchall():
                rows.append({
                    'symbol': r['symbol'],
                    'quarter': r['quarter'],
                    'revenue': r['revenue'],
                    'net_profit': r['net_profit'],
                    'eps': r['eps'],
                    'roe': r['roe'],
                    'roce': r['roce'],
                    'debt_equity': r['debt_equity'],
                    'operating_margin': r['operating_margin'],
                    'net_margin': r['net_margin'],
                    'publication_date': str(r['publication_date']) if r['publication_date'] else None,
                    'quarantine_reason': r['quarantine_reason'],
                    'original_id': r['original_id'],
                    'original_table': r['original_table']
                })
            return canonical_quarantine_hash(rows, exact=exact), len(rows)

def main():
    parser = argparse.ArgumentParser(description="Compute and compare canonical SHA-256 database checksums.")
    parser.add_argument("--source-sqlite", default=os.path.join(project_root, "database", "swing_trading.db"), help="Source SQLite DB path")
    parser.add_argument("--dest-sqlite", help="Destination test SQLite DB path (optional comparison)")
    parser.add_argument("--dest-pg-url", default=os.getenv("TEST_POSTGRESQL_URL"), help="Destination test PostgreSQL URL (optional comparison)")
    parser.add_argument("--exact", action="store_true", help="Perform bit-exact migration integrity hashing without 4-decimal rounding")
    args = parser.parse_args()

    logger.info("=== Phase 7.2C: Deterministic Canonical Reconciliation Checksums ===")
    logger.info(f"Mode: {'EXACT BIT-LEVEL INTEGRITY (Zero Rounding)' if args.exact else 'STATUTORY 4-DECIMAL NORMALIZATION'}")
    
    src_m_hash, src_m_count = compute_sqlite_market_checksum(args.source_sqlite, exact=args.exact)
    src_ti_hash, src_ti_count = compute_sqlite_indicator_checksum(args.source_sqlite, exact=args.exact)
    src_f_hash, src_f_count = compute_sqlite_financial_checksum(args.source_sqlite, exact=args.exact)
    src_q_hash, src_q_count = compute_sqlite_quarantine_checksum(args.source_sqlite, exact=args.exact)

    logger.info(f"Source Daily Prices: {src_m_count} rows | Canonical SHA-256: {src_m_hash}")
    logger.info(f"Source Indicators:   {src_ti_count} rows | Canonical SHA-256: {src_ti_hash}")
    logger.info(f"Source Financials:   {src_f_count} rows | Canonical SHA-256: {src_f_hash}")
    logger.info(f"Source Quarantined:  {src_q_count} rows | Canonical SHA-256: {src_q_hash}")

    if args.dest_pg_url:
        logger.info(f"\nComparing with Destination (PostgreSQL): {mask_database_url(args.dest_pg_url)}")
        dst_m_hash, dst_m_count = compute_postgres_market_checksum(args.dest_pg_url, exact=args.exact)
        dst_ti_hash, dst_ti_count = compute_postgres_indicator_checksum(args.dest_pg_url, exact=args.exact)
        dst_f_hash, dst_f_count = compute_postgres_financial_checksum(args.dest_pg_url, exact=args.exact)
        dst_q_hash, dst_q_count = compute_postgres_quarantine_checksum(args.dest_pg_url, exact=args.exact)

        logger.info(f"Dest Daily Prices: {dst_m_count} rows | Canonical SHA-256: {dst_m_hash}")
        logger.info(f"Dest Indicators:   {dst_ti_count} rows | Canonical SHA-256: {dst_ti_hash}")
        logger.info(f"Dest Financials:   {dst_f_count} rows | Canonical SHA-256: {dst_f_hash}")
        logger.info(f"Dest Quarantined:  {dst_q_count} rows | Canonical SHA-256: {dst_q_hash}")

        m_match = (src_m_hash == dst_m_hash)
        ti_match = (src_ti_hash == dst_ti_hash)
        f_match = (src_f_hash == dst_f_hash)
        q_match = (src_q_hash == dst_q_hash)

        logger.info(f"\n--- RECONCILIATION VERDICT ---")
        logger.info(f"Market Prices Parity:        [{'PASS' if m_match else 'FAIL'}]")
        logger.info(f"Technical Indicators Parity: [{'PASS' if ti_match else 'FAIL'}]")
        logger.info(f"Financial Vintages Parity:   [{'PASS' if f_match else 'FAIL'}]")
        logger.info(f"Quarantined Records Parity:  [{'PASS' if q_match else 'FAIL'}]")
        if not (m_match and ti_match and f_match and q_match):
            logger.error("[FAIL] One or more parity checks failed.")
            sys.exit(1)
        logger.info("[SUCCESS] 100% Canonical SHA-256 Checksum Parity Verified!")
    elif args.dest_sqlite:
        logger.info(f"\nComparing with Destination (SQLite): {args.dest_sqlite}")
        dst_m_hash, dst_m_count = compute_sqlite_market_checksum(args.dest_sqlite, exact=args.exact)
        dst_ti_hash, dst_ti_count = compute_sqlite_indicator_checksum(args.dest_sqlite, exact=args.exact)
        dst_f_hash, dst_f_count = compute_sqlite_financial_checksum(args.dest_sqlite, exact=args.exact)
        dst_q_hash, dst_q_count = compute_sqlite_quarantine_checksum(args.dest_sqlite, exact=args.exact)

        logger.info(f"Dest Daily Prices: {dst_m_count} rows | Canonical SHA-256: {dst_m_hash}")
        logger.info(f"Dest Indicators:   {dst_ti_count} rows | Canonical SHA-256: {dst_ti_hash}")
        logger.info(f"Dest Financials:   {dst_f_count} rows | Canonical SHA-256: {dst_f_hash}")
        logger.info(f"Dest Quarantined:  {dst_q_count} rows | Canonical SHA-256: {dst_q_hash}")

        m_match = (src_m_hash == dst_m_hash)
        ti_match = (src_ti_hash == dst_ti_hash)
        f_match = (src_f_hash == dst_f_hash)
        q_match = (src_q_hash == dst_q_hash)

        logger.info(f"\n--- RECONCILIATION VERDICT ---")
        logger.info(f"Market Prices Parity:        [{'PASS' if m_match else 'FAIL'}]")
        logger.info(f"Technical Indicators Parity: [{'PASS' if ti_match else 'FAIL'}]")
        logger.info(f"Financial Vintages Parity:   [{'PASS' if f_match else 'FAIL'}]")
        logger.info(f"Quarantined Records Parity:  [{'PASS' if q_match else 'FAIL'}]")
        if not (m_match and ti_match and f_match and q_match):
            logger.error("[FAIL] One or more parity checks failed.")
            sys.exit(1)
        logger.info("[SUCCESS] 100% Canonical SHA-256 Checksum Parity Verified!")

if __name__ == "__main__":
    main()
