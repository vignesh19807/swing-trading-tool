"""
scripts/migration/create_ci_source_fixture.py
=============================================
Generates a deterministic, synthetic CI source SQLite database fixture for
reproducible PostgreSQL 16 migration validation in GitHub Actions and local CI.

Strict Governance Invariants:
1. Synthetic data only: Never extracts, clones, or exposes production data.
2. Zero credentials: Free of any secrets, tokens, or sensitive URLs.
3. Deterministic: Fixed timestamps, identifiers, and financial values.
4. Schema-compliant: Matches authoritative SQLite schema and PostgreSQL 16
   relational integrity constraints (FKs, CHECKs, UNIQUEs).
5. Multi-domain coverage:
   - Sectors & Industries taxonomy
   - Authoritative company universe (from STOCK_UNIVERSE)
   - Daily OHLCV price series
   - Technical indicators
   - Quarterly financial vintages (with Point-in-Time provenance and lineage)
   - Quarantined legacy financial results
"""

from __future__ import annotations

import os
import sys
import sqlite3
import argparse
import hashlib
from pathlib import Path
from typing import Dict, Any

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_ci_source_database(db_path: str) -> Dict[str, int]:
    """
    Creates and populates a synthetic, deterministic SQLite source database.

    Parameters
    ----------
    db_path : str
        Target filesystem path for the SQLite database file.

    Returns
    -------
    Dict[str, int]
        Counts of inserted rows across domain tables.
    """
    out_path = Path(db_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # --------------------------------------------------------------------------
    # 1. DDL: Create All Tables Matching Authoritative Schema
    # --------------------------------------------------------------------------
    cur.executescript("""
    -- 1. Taxonomy: Sectors & Industries
    CREATE TABLE IF NOT EXISTS sectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS industries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sector_id INTEGER NOT NULL REFERENCES sectors(id) ON DELETE RESTRICT,
        name TEXT NOT NULL,
        UNIQUE(name, sector_id)
    );

    -- 2. Companies Universe Master
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE NOT NULL,
        company_name TEXT NOT NULL,
        sector TEXT,
        industry TEXT,
        exchange TEXT NOT NULL DEFAULT 'NSE',
        sector_id INTEGER REFERENCES sectors(id) ON DELETE SET NULL,
        industry_id INTEGER REFERENCES industries(id) ON DELETE SET NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        listing_date TEXT,
        created_at TEXT DEFAULT '2026-01-01 00:00:00',
        updated_at TEXT DEFAULT '2026-01-01 00:00:00',
        source TEXT DEFAULT 'INITIAL_UNIVERSE'
    );

    -- 3. Daily OHLCV Prices
    CREATE TABLE IF NOT EXISTS daily_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        adjusted_close REAL,
        UNIQUE(company_id, date)
    );

    -- 4. Technical Indicators
    CREATE TABLE IF NOT EXISTS technical_indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        ema_20 REAL,
        ema_50 REAL,
        ema_200 REAL,
        macd_histogram REAL,
        atr_14 REAL,
        technical_score REAL,
        UNIQUE(company_id, date)
    );

    -- 5. Quarterly Results (Legacy Financials)
    CREATE TABLE IF NOT EXISTS quarterly_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        quarter TEXT NOT NULL,
        revenue REAL,
        net_profit REAL,
        eps REAL,
        roe REAL,
        roce REAL,
        debt_equity REAL,
        operating_margin REAL,
        net_margin REAL,
        publication_date TEXT,
        UNIQUE(company_id, quarter)
    );

    -- 5b. Quarantined Financial Results (Legacy Quarantine & Provenance)
    CREATE TABLE IF NOT EXISTS quarantined_quarterly_results (
        quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        quarter TEXT NOT NULL,
        revenue REAL,
        net_profit REAL,
        eps REAL,
        roe REAL,
        roce REAL,
        debt_equity REAL,
        operating_margin REAL,
        net_margin REAL,
        publication_date TEXT,
        quarantined_at TEXT DEFAULT '2026-01-01 00:00:00+00:00',
        quarantine_reason TEXT NOT NULL,
        original_id INTEGER NOT NULL,
        original_table TEXT NOT NULL DEFAULT 'quarterly_results',
        UNIQUE(company_id, quarter)
    );

    -- 6. Quarterly Financial Vintages (Point-in-Time Research & Governance)
    CREATE TABLE IF NOT EXISTS quarterly_financial_vintages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
        quarter TEXT NOT NULL,
        period_start_date TEXT NOT NULL,
        period_end_date TEXT NOT NULL,
        accounting_standard TEXT NOT NULL DEFAULT 'IND_AS' CHECK(accounting_standard IN ('IND_AS', 'IGAAP')),
        filing_scope TEXT NOT NULL DEFAULT 'CONSOLIDATED' CHECK(filing_scope IN ('CONSOLIDATED', 'STANDALONE')),
        company_filing_type TEXT NOT NULL CHECK(company_filing_type IN (
            'ORIGINAL', 'REVISED_DISCLOSURE', 'CORPORATE_RESTATEMENT', 'ANNUAL_AUDITED_FINAL'
        )),
        filing_type TEXT GENERATED ALWAYS AS (company_filing_type) VIRTUAL,
        internal_revision_type TEXT NOT NULL DEFAULT 'INITIAL_INGESTION' CHECK(internal_revision_type IN (
            'INITIAL_INGESTION', 'EXTRACTION_CORRECTION', 'SCOPE_REALIGNMENT', 'SECTOR_NORMALIZATION'
        )),
        verification_status TEXT NOT NULL DEFAULT 'AUTHENTIC_VERIFIED' CHECK(verification_status IN (
            'AUTHENTIC_VERIFIED', 'AUTHENTIC_UNVERIFIED', 'VERIFIED', 'PROVISIONAL', 'REJECTED'
        )),
        research_eligibility TEXT NOT NULL DEFAULT 'VERIFIED_ELIGIBLE' CHECK(research_eligibility IN (
            'VERIFIED_ELIGIBLE', 'UNVERIFIED_OPERATIONAL_ONLY', 'PROVISIONAL_DEMO', 'QUARANTINED', 'SUPERSEDED'
        )),
        version_sequence INTEGER NOT NULL DEFAULT 1 CHECK(version_sequence >= 1),
        parent_vintage_id INTEGER REFERENCES quarterly_financial_vintages(id),
        supersedes_vintage_id INTEGER REFERENCES quarterly_financial_vintages(id),
        superseded_by_vintage_id INTEGER REFERENCES quarterly_financial_vintages(id),
        revision_reason TEXT,
        revision_source TEXT,
        lineage_created_at TEXT DEFAULT '2026-01-01 00:00:00+00:00',
        exchange TEXT NOT NULL CHECK(exchange IN ('NSE', 'BSE')),
        exchange_broadcast_id TEXT NOT NULL,
        original_broadcast_id TEXT,
        publication_date TEXT,
        published_at TEXT NOT NULL,
        publication_timestamp TEXT GENERATED ALWAYS AS (published_at) VIRTUAL,
        effective_trading_date TEXT NOT NULL,
        market_session TEXT DEFAULT 'POST_MARKET',
        ingested_at TEXT DEFAULT '2026-01-01 00:00:00+00:00',
        internally_corrected_at TEXT,
        company_revision_published_at TEXT,
        revenue REAL NOT NULL,
        operating_profit REAL,
        net_profit REAL NOT NULL,
        eps REAL NOT NULL,
        is_banking_institution INTEGER NOT NULL DEFAULT 0 CHECK(is_banking_institution IN (0, 1)),
        net_interest_income REAL,
        capital_adequacy_ratio REAL,
        gross_npa_pct REAL,
        net_npa_pct REAL,
        total_assets REAL,
        total_equity REAL,
        total_debt REAL,
        current_liabilities REAL,
        roe REAL,
        roce REAL,
        debt_equity REAL,
        operating_margin REAL,
        net_margin REAL,
        original_currency TEXT DEFAULT 'INR',
        original_extracted_value REAL,
        conversion_rate REAL DEFAULT 1.0,
        conversion_date TEXT,
        source_document_url TEXT NOT NULL,
        source_document_hash TEXT NOT NULL,
        verification_notes TEXT,
        created_at TEXT DEFAULT '2026-01-01 00:00:00+00:00',
        UNIQUE(exchange, exchange_broadcast_id),
        UNIQUE(company_id, quarter, filing_scope, version_sequence)
    );

    -- 7. Signals & Scores (Decision Intelligence)
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        signal TEXT,
        entry_price REAL,
        stop_loss REAL,
        target_price REAL,
        confidence REAL
    );

    CREATE TABLE IF NOT EXISTS financial_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        profitability_score REAL,
        growth_score REAL,
        valuation_score REAL,
        overall_score REAL
    );

    CREATE TABLE IF NOT EXISTS opportunity_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        technical_score REAL,
        financial_score REAL,
        momentum_score REAL,
        opportunity_score REAL
    );

    CREATE TABLE IF NOT EXISTS universe_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        old_values_json TEXT,
        new_values_json TEXT,
        initiated_by TEXT NOT NULL DEFAULT 'SYSTEM',
        notes TEXT,
        timestamp TEXT NOT NULL
    );
    """)

    # --------------------------------------------------------------------------
    # 2. Synthetic Data Insertion (Deterministic & Representative)
    # --------------------------------------------------------------------------
    counts = {}

    # 2.1 Sectors & Industries
    cur.executemany("INSERT INTO sectors (id, name) VALUES (?, ?);", [
        (1, "Information Technology"),
        (2, "Financial Services"),
        (3, "Energy"),
        (4, "Automobile"),
    ])
    counts["sectors"] = 4

    cur.executemany("INSERT INTO industries (id, sector_id, name) VALUES (?, ?, ?);", [
        (1, 1, "Computers - Software"),
        (2, 2, "Banks"),
        (3, 3, "Oil & Gas"),
        (4, 4, "Automobiles"),
    ])
    counts["industries"] = 4

    # 2.2 Companies Master (Authoritative symbols from STOCK_UNIVERSE)
    cur.executemany("""
    INSERT INTO companies (id, symbol, company_name, sector, industry, exchange, sector_id, industry_id, is_active, status, listing_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, [
        (1, "INFY", "Infosys Limited", "Information Technology", "Computers - Software", "NSE", 1, 1, 1, "ACTIVE", "1993-06-14"),
        (2, "TCS", "Tata Consultancy Services Limited", "Information Technology", "Computers - Software", "NSE", 1, 1, 1, "ACTIVE", "2004-08-25"),
        (3, "HDFCBANK", "HDFC Bank Limited", "Financial Services", "Banks", "NSE", 2, 2, 1, "ACTIVE", "1995-05-19"),
        (4, "RELIANCE", "Reliance Industries Limited", "Energy", "Oil & Gas", "NSE", 3, 3, 1, "ACTIVE", "1977-11-29"),
    ])
    counts["companies"] = 4

    # 2.3 Daily Prices (5 deterministic trading sessions across 4 symbols = 20 bars)
    market_data = [
        # INFY (id=1)
        (1, 1, "2026-01-05", 1850.0, 1870.0, 1845.0, 1865.0, 2500000, 1865.0),
        (2, 1, "2026-01-06", 1865.0, 1880.0, 1855.0, 1872.0, 2100000, 1872.0),
        (3, 1, "2026-01-07", 1872.0, 1895.0, 1860.0, 1888.0, 3100000, 1888.0),
        (4, 1, "2026-01-08", 1888.0, 1900.0, 1875.0, 1882.0, 1900000, 1882.0),
        (5, 1, "2026-01-09", 1882.0, 1890.0, 1865.0, 1878.0, 2200000, 1878.0),
        # TCS (id=2)
        (6, 2, "2026-01-05", 4120.0, 4150.0, 4100.0, 4135.0, 1200000, 4135.0),
        (7, 2, "2026-01-06", 4135.0, 4165.0, 4125.0, 4150.0, 1400000, 4150.0),
        (8, 2, "2026-01-07", 4150.0, 4180.0, 4140.0, 4172.0, 1600000, 4172.0),
        (9, 2, "2026-01-08", 4172.0, 4190.0, 4155.0, 4160.0, 1100000, 4160.0),
        (10, 2, "2026-01-09", 4160.0, 4175.0, 4145.0, 4168.0, 1300000, 4168.0),
        # HDFCBANK (id=3)
        (11, 3, "2026-01-05", 1650.0, 1670.0, 1640.0, 1662.0, 5000000, 1662.0),
        (12, 3, "2026-01-06", 1662.0, 1680.0, 1655.0, 1675.0, 4800000, 1675.0),
        (13, 3, "2026-01-07", 1675.0, 1690.0, 1668.0, 1682.0, 5200000, 1682.0),
        (14, 3, "2026-01-08", 1682.0, 1695.0, 1670.0, 1678.0, 4300000, 1678.0),
        (15, 3, "2026-01-09", 1678.0, 1685.0, 1665.0, 1670.0, 4600000, 1670.0),
        # RELIANCE (id=4)
        (16, 4, "2026-01-05", 2900.0, 2930.0, 2890.0, 2915.0, 3000000, 2915.0),
        (17, 4, "2026-01-06", 2915.0, 2940.0, 2905.0, 2928.0, 2800000, 2928.0),
        (18, 4, "2026-01-07", 2928.0, 2955.0, 2920.0, 2945.0, 3200000, 2945.0),
        (19, 4, "2026-01-08", 2945.0, 2960.0, 2935.0, 2940.0, 2600000, 2940.0),
        (20, 4, "2026-01-09", 2940.0, 2950.0, 2925.0, 2932.0, 2700000, 2932.0),
    ]
    cur.executemany("""
    INSERT INTO daily_prices (id, company_id, date, open, high, low, close, volume, adjusted_close)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, market_data)
    counts["daily_prices"] = len(market_data)

    # 2.4 Technical Indicators (20 matching rows)
    indicators_data = [
        # INFY (id=1)
        (1, 1, "2026-01-05", 58.5, 12.4, 10.2, 1840.0, 1820.0, 1750.0, 2.2, 25.0, 78.5),
        (2, 1, "2026-01-06", 60.1, 13.1, 10.8, 1845.0, 1823.0, 1752.0, 2.3, 24.5, 80.0),
        (3, 1, "2026-01-07", 63.4, 14.5, 11.5, 1851.0, 1827.0, 1755.0, 3.0, 26.0, 84.0),
        (4, 1, "2026-01-08", 61.8, 14.2, 12.0, 1855.0, 1830.0, 1758.0, 2.2, 25.5, 81.0),
        (5, 1, "2026-01-09", 60.5, 13.8, 12.3, 1859.0, 1833.0, 1760.0, 1.5, 25.0, 79.0),
        # TCS (id=2)
        (6, 2, "2026-01-05", 52.0, 15.0, 14.0, 4110.0, 4080.0, 3950.0, 1.0, 45.0, 72.0),
        (7, 2, "2026-01-06", 54.2, 16.2, 14.4, 4115.0, 4084.0, 3953.0, 1.8, 44.0, 74.5),
        (8, 2, "2026-01-07", 57.0, 18.0, 15.1, 4122.0, 4089.0, 3957.0, 2.9, 46.0, 78.0),
        (9, 2, "2026-01-08", 55.1, 17.5, 15.6, 4128.0, 4093.0, 3960.0, 1.9, 45.5, 75.0),
        (10, 2, "2026-01-09", 56.3, 17.9, 16.1, 4133.0, 4097.0, 3963.0, 1.8, 45.0, 76.5),
        # HDFCBANK (id=3)
        (11, 3, "2026-01-05", 54.0, 5.5, 4.8, 1645.0, 1630.0, 1580.0, 0.7, 22.0, 71.0),
        (12, 3, "2026-01-06", 56.5, 6.4, 5.1, 1650.0, 1633.0, 1582.0, 1.3, 21.5, 74.0),
        (13, 3, "2026-01-07", 58.2, 7.2, 5.5, 1655.0, 1636.0, 1584.0, 1.7, 22.5, 77.0),
        (14, 3, "2026-01-08", 56.9, 6.9, 5.8, 1659.0, 1639.0, 1586.0, 1.1, 22.0, 75.0),
        (15, 3, "2026-01-09", 55.0, 6.2, 5.9, 1662.0, 1641.0, 1588.0, 0.3, 21.5, 72.0),
        # RELIANCE (id=4)
        (16, 4, "2026-01-05", 62.0, 20.5, 18.0, 2890.0, 2850.0, 2720.0, 2.5, 35.0, 81.0),
        (17, 4, "2026-01-06", 64.1, 22.0, 18.8, 2895.0, 2855.0, 2724.0, 3.2, 34.5, 83.5),
        (18, 4, "2026-01-07", 66.8, 24.5, 19.9, 2902.0, 2860.0, 2728.0, 4.6, 36.0, 87.0),
        (19, 4, "2026-01-08", 65.2, 23.8, 20.7, 2908.0, 2865.0, 2732.0, 3.1, 35.5, 85.0),
        (20, 4, "2026-01-09", 63.9, 22.9, 21.1, 2913.0, 2869.0, 2736.0, 1.8, 35.0, 83.0),
    ]
    cur.executemany("""
    INSERT INTO technical_indicators (id, company_id, date, rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, indicators_data)
    counts["technical_indicators"] = len(indicators_data)

    # 2.5 Quarterly Financial Vintages (Representative, Lineage-aware, PIT-compliant)
    # Notes for Reconciliation parity:
    # - publication_date is set to NULL because schema_pg.sql does not include publication_date in quarterly_financial_vintages.
    # - published_at uses UTC offset format 'YYYY-MM-DD HH:MM:SS+00:00' to match PostgreSQL TIMESTAMPTZ str representation.
    # - Banking company (HDFCBANK) has debt_equity=NULL to respect CHECK(NOT is_banking_institution OR debt_equity IS NULL).
    vintages_data = [
        # 1. INFY 2024-Q1 Version 1 (Parent Vintage)
        (
            1, 1, "2024-Q1", "2024-01-01", "2024-03-31",
            "IND_AS", "CONSOLIDATED", "ORIGINAL", "INITIAL_INGESTION",
            "AUTHENTIC_VERIFIED", "VERIFIED_ELIGIBLE", 1, None, None, None,
            None, None, "2026-01-01 00:00:00+00:00",
            "NSE", "NSE_BC_INFY_2024Q1_V1", None,
            "2024-04-18 16:30:00+00:00", "2024-04-19", "POST_MARKET", "2024-04-18 17:00:00+00:00",
            None, None,
            37923.0, 8288.0, 6128.0, 14.75,
            0, None, None, None, None,
            125000.0, 85000.0, 6800.0, 33200.0,
            0.28, 0.35, 0.08, 0.2185, 0.1616,
            "INR", 37923.0, 1.0, "2024-04-18",
            "https://archives.nseindia.com/corporate/INFY_Q1_2024.pdf", "HASH_INFY_Q1_2024_A1B2",
            "Verified against official exchange PDF", "2024-04-18 17:00:00+00:00"
        ),
        # 2. INFY 2024-Q1 Version 2 (Child Revision)
        (
            2, 1, "2024-Q1", "2024-01-01", "2024-03-31",
            "IND_AS", "CONSOLIDATED", "REVISED_DISCLOSURE", "EXTRACTION_CORRECTION",
            "AUTHENTIC_VERIFIED", "VERIFIED_ELIGIBLE", 2, 1, 1, None,
            "Revision to operational expense reporting", "Auditor Note", "2026-01-01 00:00:00+00:00",
            "NSE", "NSE_BC_INFY_2024Q1_V2", None,
            "2024-04-20 11:00:00+00:00", "2024-04-22", "POST_MARKET", "2024-04-20 12:00:00+00:00",
            None, None,
            37923.0, 8295.0, 6135.0, 14.77,
            0, None, None, None, None,
            125000.0, 85000.0, 6800.0, 33200.0,
            0.28, 0.35, 0.08, 0.2187, 0.1618,
            "INR", 37923.0, 1.0, "2024-04-20",
            "https://archives.nseindia.com/corporate/INFY_Q1_2024_rev.pdf", "HASH_INFY_Q1_2024_REV_C3D4",
            "Revised disclosure correcting minor operating expenses", "2024-04-20 12:00:00+00:00"
        ),
        # 3. TCS 2024-Q1 Version 1
        (
            3, 2, "2024-Q1", "2024-01-01", "2024-03-31",
            "IND_AS", "CONSOLIDATED", "ORIGINAL", "INITIAL_INGESTION",
            "AUTHENTIC_VERIFIED", "VERIFIED_ELIGIBLE", 1, None, None, None,
            None, None, "2026-01-01 00:00:00+00:00",
            "NSE", "NSE_BC_TCS_2024Q1_V1", None,
            "2024-04-12 18:00:00+00:00", "2024-04-15", "POST_MARKET", "2024-04-12 18:30:00+00:00",
            None, None,
            61237.0, 15464.0, 12241.0, 33.45,
            0, None, None, None, None,
            145000.0, 98000.0, 4900.0, 42100.0,
            0.49, 0.58, 0.05, 0.2525, 0.1999,
            "INR", 61237.0, 1.0, "2024-04-12",
            "https://archives.nseindia.com/corporate/TCS_Q1_2024.pdf", "HASH_TCS_Q1_2024_E5F6",
            "Verified against exchange broadcast", "2024-04-12 18:30:00+00:00"
        ),
        # 4. TCS 2024-Q2 Version 1 (Unverified Operational Only)
        (
            4, 2, "2024-Q2", "2024-04-01", "2024-06-30",
            "IND_AS", "CONSOLIDATED", "ORIGINAL", "INITIAL_INGESTION",
            "AUTHENTIC_UNVERIFIED", "UNVERIFIED_OPERATIONAL_ONLY", 1, None, None, None,
            None, None, "2026-01-01 00:00:00+00:00",
            "NSE", "NSE_BC_TCS_2024Q2_V1", None,
            "2024-07-11 17:30:00+00:00", "2024-07-12", "POST_MARKET", "2024-07-11 18:00:00+00:00",
            None, None,
            62613.0, 15444.0, 12040.0, 32.90,
            0, None, None, None, None,
            148000.0, 100000.0, 5000.0, 43000.0,
            0.48, 0.57, 0.05, 0.2467, 0.1923,
            "INR", 62613.0, 1.0, "2024-07-11",
            "https://archives.nseindia.com/corporate/TCS_Q2_2024.pdf", "HASH_TCS_Q2_2024_G7H8",
            "Unverified provisional disclosure", "2024-07-11 18:00:00+00:00"
        ),
        # 5. HDFCBANK 2024-Q1 Version 1 (Banking Institution)
        (
            5, 3, "2024-Q1", "2024-01-01", "2024-03-31",
            "IND_AS", "CONSOLIDATED", "ORIGINAL", "INITIAL_INGESTION",
            "AUTHENTIC_VERIFIED", "VERIFIED_ELIGIBLE", 1, None, None, None,
            None, None, "2026-01-01 00:00:00+00:00",
            "NSE", "NSE_BC_HDFC_2024Q1_V1", None,
            "2024-04-20 14:00:00+00:00", "2024-04-22", "POST_MARKET", "2024-04-20 14:30:00+00:00",
            None, None,
            82538.0, 29274.0, 16512.0, 21.70,
            1, 29077.0, 18.8, 1.24, 0.33,
            3617623.0, 442564.0, 3175059.0, 150000.0,
            0.15, 0.17, None, 0.3547, 0.2001,
            "INR", 82538.0, 1.0, "2024-04-20",
            "https://archives.nseindia.com/corporate/HDFC_Q1_2024.pdf", "HASH_HDFC_Q1_2024_I9J0",
            "Audited banking disclosure verified", "2024-04-20 14:30:00+00:00"
        ),
        # 6. RELIANCE 2024-Q1 Version 1 (Industrial / Conglomerate)
        (
            6, 4, "2024-Q1", "2024-01-01", "2024-03-31",
            "IND_AS", "CONSOLIDATED", "ORIGINAL", "INITIAL_INGESTION",
            "AUTHENTIC_VERIFIED", "VERIFIED_ELIGIBLE", 1, None, None, None,
            None, None, "2026-01-01 00:00:00+00:00",
            "NSE", "NSE_BC_RIL_2024Q1_V1", None,
            "2024-04-22 19:00:00+00:00", "2024-04-23", "POST_MARKET", "2024-04-22 19:30:00+00:00",
            None, None,
            236533.0, 42516.0, 18951.0, 28.01,
            0, None, None, None, None,
            1750000.0, 790000.0, 330000.0, 630000.0,
            0.096, 0.115, 0.42, 0.1797, 0.0801,
            "INR", 236533.0, 1.0, "2024-04-22",
            "https://archives.nseindia.com/corporate/RIL_Q1_2024.pdf", "HASH_RIL_Q1_2024_K1L2",
            "Audited consolidated results verified", "2024-04-22 19:30:00+00:00"
        ),
    ]
    cur.executemany("""
    INSERT INTO quarterly_financial_vintages (
        id, company_id, quarter, period_start_date, period_end_date,
        accounting_standard, filing_scope, company_filing_type, internal_revision_type,
        verification_status, research_eligibility, version_sequence, parent_vintage_id,
        supersedes_vintage_id, superseded_by_vintage_id, revision_reason, revision_source,
        lineage_created_at, exchange, exchange_broadcast_id, publication_date,
        published_at, effective_trading_date, market_session, ingested_at,
        internally_corrected_at, company_revision_published_at,
        revenue, operating_profit, net_profit, eps,
        is_banking_institution, net_interest_income, capital_adequacy_ratio, gross_npa_pct, net_npa_pct,
        total_assets, total_equity, total_debt, current_liabilities,
        roe, roce, debt_equity, operating_margin, net_margin,
        original_currency, original_extracted_value, conversion_rate, conversion_date,
        source_document_url, source_document_hash, verification_notes, created_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?
    );
    """, vintages_data)
    counts["quarterly_financial_vintages"] = len(vintages_data)

    # 2.6 Quarantined Legacy Financial Results
    quarantine_data = [
        (1, 2, "2023-Q3", 59692.0, 11342.0, 31.0, 0.45, 0.54, 0.05, 0.24, 0.19, "2023-10-11", "2023-10-12 10:00:00+00:00", "LEGACY_UNVERIFIED_SOURCE", 101, "quarterly_results"),
        (2, 1, "2023-Q3", 38994.0, 6212.0, 14.95, 0.29, 0.36, 0.07, 0.21, 0.16, "2023-10-12", "2023-10-13 10:00:00+00:00", "LEGACY_UNVERIFIED_SOURCE", 102, "quarterly_results"),
    ]
    cur.executemany("""
    INSERT INTO quarantined_quarterly_results (
        quarantine_id, company_id, quarter, revenue, net_profit, eps, roe, roce,
        debt_equity, operating_margin, net_margin, publication_date, quarantined_at,
        quarantine_reason, original_id, original_table
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, quarantine_data)
    counts["quarantined_quarterly_results"] = len(quarantine_data)

    # 2.7 Quarterly Results (Legacy support)
    cur.executemany("""
    INSERT INTO quarterly_results (id, company_id, quarter, revenue, net_profit, eps, roe, roce, debt_equity, operating_margin, net_margin, publication_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, [
        (1, 1, "2024-Q1", 37923.0, 6128.0, 14.75, 0.28, 0.35, 0.08, 0.2185, 0.1616, "2024-04-18"),
        (2, 2, "2024-Q1", 61237.0, 12241.0, 33.45, 0.49, 0.58, 0.05, 0.2525, 0.1999, "2024-04-12"),
    ])
    counts["quarterly_results"] = 2

    # 2.8 Decision Intelligence & Logging Support Tables
    cur.executemany("""
    INSERT INTO signals (id, company_id, date, signal, entry_price, stop_loss, target_price, confidence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, [
        (1, 1, "2026-01-09", "BUY", 1880.0, 1840.0, 1960.0, 0.85),
        (2, 2, "2026-01-09", "HOLD", 4165.0, 4100.0, 4300.0, 0.72),
        (3, 3, "2026-01-09", "BUY", 1675.0, 1640.0, 1750.0, 0.88),
        (4, 4, "2026-01-09", "HOLD", 2935.0, 2880.0, 3050.0, 0.65),
    ])
    counts["signals"] = 4

    cur.executemany("""
    INSERT INTO financial_scores (id, company_id, date, profitability_score, growth_score, valuation_score, overall_score)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, [
        (1, 1, "2026-01-09", 82.0, 75.0, 68.0, 76.5),
        (2, 2, "2026-01-09", 88.0, 72.0, 65.0, 77.0),
        (3, 3, "2026-01-09", 80.0, 82.0, 70.0, 78.5),
        (4, 4, "2026-01-09", 74.0, 68.0, 72.0, 71.5),
    ])
    counts["financial_scores"] = 4

    cur.executemany("""
    INSERT INTO opportunity_scores (id, company_id, date, technical_score, financial_score, momentum_score, opportunity_score)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, [
        (1, 1, "2026-01-09", 79.0, 76.5, 82.0, 79.2),
        (2, 2, "2026-01-09", 76.5, 77.0, 74.0, 76.0),
        (3, 3, "2026-01-09", 72.0, 78.5, 75.0, 75.2),
        (4, 4, "2026-01-09", 83.0, 71.5, 80.0, 78.8),
    ])
    counts["opportunity_scores"] = 4

    cur.executemany("""
    INSERT INTO universe_audit_log (id, symbol, action, old_values_json, new_values_json, initiated_by, notes, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, [
        (1, "INFY", "INITIAL_SEED", None, '{"status": "ACTIVE"}', "CI_FIXTURE", "CI synthetic fixture init", "2026-01-01 00:00:00"),
        (2, "TCS", "INITIAL_SEED", None, '{"status": "ACTIVE"}', "CI_FIXTURE", "CI synthetic fixture init", "2026-01-01 00:00:00"),
        (3, "HDFCBANK", "INITIAL_SEED", None, '{"status": "ACTIVE"}', "CI_FIXTURE", "CI synthetic fixture init", "2026-01-01 00:00:00"),
        (4, "RELIANCE", "INITIAL_SEED", None, '{"status": "ACTIVE"}', "CI_FIXTURE", "CI synthetic fixture init", "2026-01-01 00:00:00"),
    ])
    counts["universe_audit_log"] = 4

    conn.commit()
    conn.close()

    return counts


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic SQLite source database for CI.")
    parser.add_argument(
        "--output",
        default=os.getenv("SOURCE_SQLITE_PATH", os.path.join(PROJECT_ROOT, "scratch", "ci_source_fixture.db")),
        help="Target filesystem path for output SQLite database"
    )
    args = parser.parse_args()

    print(f"=== Creating CI Source SQLite Fixture ===")
    print(f"Target path: {args.output}")

    counts = create_ci_source_database(args.output)

    # Compute SHA-256 for logging
    h = hashlib.sha256()
    with open(args.output, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    sha256 = h.hexdigest().upper()

    print("\n--- Summary of Generated Fixture Records ---")
    for table, count in sorted(counts.items()):
        print(f"  {table:30}: {count:5} rows")
    print(f"\n[SUCCESS] CI SQLite Fixture generated successfully.")
    print(f"SHA-256: {sha256}")
    print(f"File size: {os.path.getsize(args.output)} bytes")


if __name__ == "__main__":
    main()
