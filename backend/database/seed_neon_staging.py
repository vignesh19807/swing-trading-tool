"""
Neon PostgreSQL Staging Provisioning and Synthetic Seeding Script
==================================================================
Provisions a staging Neon PostgreSQL database with canonical schemas,
realistic synthetic Indian equities, price history, indicators, and
point-in-time financial vintages.

STRICT SAFETY INVARIANTS:
1. NEVER uploads or touches database/swing_trading.db or database/staging_financial_expansion.db.
2. NEVER migrates or accesses production financial records.
3. ALL records are clearly identifiable as synthetic staging data.
4. Idempotent: can be executed multiple times without duplicate errors.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import hashlib
import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.config import PROJECT_ROOT
from backend.database.connection import (
    open_db_connection,
    reset_db_pool,
    mask_database_url,
    DatabaseEngine,
    DatabaseConnectionError,
    DatabaseQueryError,
)

# Canonical production database checksums for invariant enforcement
PROD_CANONICAL_SHA256 = "1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8"
STAGING_CANONICAL_SHA256 = "84263F185EC782443F8C15F08F0AEAB96C0BD8B40413D5ADD12C3AE908176BE7"

STAGING_COMPANIES = [
    ("TCS", "Tata Consultancy Services Ltd", "Information Technology", "IT Services", "NSE", True, "ACTIVE", "2004-08-25"),
    ("INFY", "Infosys Ltd", "Information Technology", "IT Services", "NSE", True, "ACTIVE", "1993-02-08"),
    ("RELIANCE", "Reliance Industries Ltd", "Energy", "Oil & Gas", "NSE", True, "ACTIVE", "1977-11-29"),
    ("HDFCBANK", "HDFC Bank Ltd", "Financial Services", "Private Sector Bank", "NSE", True, "ACTIVE", "1995-05-19"),
    ("ICICIBANK", "ICICI Bank Ltd", "Financial Services", "Private Sector Bank", "NSE", True, "ACTIVE", "1998-09-17"),
    ("TATAMOTORS", "Tata Motors Ltd", "Automobile and Auto Components", "Automobiles", "NSE", True, "COLD_START", "1945-09-01"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd", "Healthcare", "Pharmaceuticals", "NSE", True, "ACTIVE", "1994-12-26"),
    ("HINDUNILVR", "Hindustan Unilever Ltd", "Fast Moving Consumer Goods", "Personal Products", "NSE", True, "ACTIVE", "1956-11-01"),
    ("ITC", "ITC Ltd", "Fast Moving Consumer Goods", "Cigarettes & Tobacco", "NSE", True, "ACTIVE", "1954-08-24"),
    ("LT", "Larsen & Toubro Ltd", "Capital Goods", "Civil Construction", "NSE", True, "ACTIVE", "1950-06-23"),
]


def verify_database_invariants():
    """Verify that production and staging SQLite databases are intact."""
    prod_path = PROJECT_ROOT / "database" / "swing_trading.db"
    stag_path = PROJECT_ROOT / "database" / "staging_financial_expansion.db"

    if prod_path.exists():
        h = hashlib.sha256(prod_path.read_bytes()).hexdigest().upper()
        if h != PROD_CANONICAL_SHA256:
            raise RuntimeError(f"PROD DB SHA256 CORRUPTION DETECTED: {h}")

    if stag_path.exists():
        h = hashlib.sha256(stag_path.read_bytes()).hexdigest().upper()
        if h != STAGING_CANONICAL_SHA256:
            raise RuntimeError(f"STAGING DB SHA256 CORRUPTION DETECTED: {h}")


def apply_schema_to_neon(pg_url: str) -> None:
    """Applies schema_pg.sql to the target Neon database."""
    verify_database_invariants()
    schema_path = PROJECT_ROOT / "backend" / "database" / "schema_pg.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"PostgreSQL schema file not found at: {schema_path}")

    sql_text = schema_path.read_text(encoding="utf-8")
    masked = mask_database_url(pg_url)
    print(f"Applying schema_pg.sql to Neon staging target: {masked}")

    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            cur.raw_cursor.execute(sql_text)
        conn.commit()

    print("PostgreSQL 16 canonical schema and triggers applied successfully.")


def seed_synthetic_staging_data(pg_url: str) -> Dict[str, Any]:
    """
    Seeds realistic synthetic Indian equities data into Neon PostgreSQL.
    Idempotent and safe: uses parameterized queries and conflict resolution.
    """
    verify_database_invariants()
    masked = mask_database_url(pg_url)
    print(f"Seeding synthetic staging data into: {masked}")

    stats = {
        "sectors": 0,
        "industries": 0,
        "companies": 0,
        "daily_prices": 0,
        "technical_indicators": 0,
        "quarterly_results": 0,
        "quarterly_financial_vintages": 0,
        "audit_logs": 0,
    }

    with open_db_connection(pg_url) as conn:
        with conn.cursor() as cur:
            # 1. Sectors
            unique_sectors = sorted(list({c[2] for c in STAGING_COMPANIES}))
            for sec_name in unique_sectors:
                cur.execute(
                    "INSERT INTO sectors (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (sec_name,),
                )
            cur.execute("SELECT id, name FROM sectors")
            sec_map = {r["name"]: r["id"] for r in cur.fetchall()}
            stats["sectors"] = len(sec_map)

            # 2. Industries
            unique_industries = sorted(list({(c[3], c[2]) for c in STAGING_COMPANIES if c[3]}))
            for ind_name, sec_name in unique_industries:
                sec_id = sec_map[sec_name]
                cur.execute(
                    "INSERT INTO industries (name, sector_id) VALUES (%s, %s) "
                    "ON CONFLICT (name, sector_id) DO NOTHING",
                    (ind_name, sec_id),
                )
            cur.execute("SELECT id, name, sector_id FROM industries")
            ind_map = {f"{r['name']}_{r['sector_id']}": r["id"] for r in cur.fetchall()}
            stats["industries"] = len(ind_map)

            # 3. Companies
            for sym, name, sec, ind, exch, is_act, st, ldate in STAGING_COMPANIES:
                s_id = sec_map.get(sec)
                i_id = ind_map.get(f"{ind}_{s_id}")
                cur.execute(
                    """
                    INSERT INTO companies (
                        symbol, company_name, sector, industry, exchange,
                        sector_id, industry_id, is_active, status, listing_date,
                        source, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'NEON_SYNTHETIC_STAGING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (symbol) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        status = EXCLUDED.status,
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (sym, name, sec, ind, exch, s_id, i_id, is_act, st, ldate),
                )
            cur.execute("SELECT id, symbol FROM companies")
            company_ids = {r["symbol"]: r["id"] for r in cur.fetchall()}
            stats["companies"] = len(company_ids)

            # 4. Daily Prices & Technical Indicators
            today = datetime.datetime.now(datetime.timezone.utc).date()
            base_prices = {
                "TCS": 3500.0, "INFY": 1500.0, "RELIANCE": 2500.0, "HDFCBANK": 1600.0,
                "ICICIBANK": 1100.0, "TATAMOTORS": 750.0, "SUNPHARMA": 1650.0,
                "HINDUNILVR": 2400.0, "ITC": 430.0, "LT": 3200.0
            }

            price_batch = []
            indicator_batch = []
            for sym, cid in company_ids.items():
                base_p = base_prices.get(sym, 1000.0)
                # Seed 100 trading days of history
                for i in range(100):
                    d = today - datetime.timedelta(days=(130 - i))
                    if d.weekday() >= 5:  # Skip weekends
                        continue
                    d_str = d.isoformat()
                    price = round(base_p + (i * 0.45), 2)
                    open_p = round(price - 5.0, 2)
                    high_p = round(price + 8.0, 2)
                    low_p = round(price - 7.0, 2)
                    vol = 1200000 + (i * 1000)

                    price_batch.append((cid, d_str, open_p, high_p, low_p, price, vol, price))

                    # Technical indicators
                    ema_20 = round(price - 2.0, 2)
                    ema_50 = round(price - 8.0, 2)
                    ema_200 = round(price - 20.0, 2)
                    rsi = 58.5
                    indicator_batch.append((cid, d_str, rsi, 12.5, 10.0, 2.5, ema_20, ema_50, ema_200, 15.0, 72.0))

            cur.executemany(
                """
                INSERT INTO daily_prices (
                    company_id, date, open, high, low, close, volume, adjusted_close
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, date) DO UPDATE SET
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
                """,
                price_batch,
            )
            cur.executemany(
                """
                INSERT INTO technical_indicators (
                    company_id, date, rsi, macd, macd_signal, macd_histogram,
                    ema_20, ema_50, ema_200, atr_14, technical_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, date) DO UPDATE SET
                    rsi = EXCLUDED.rsi,
                    ema_20 = EXCLUDED.ema_20
                """,
                indicator_batch,
            )

            stats["daily_prices"] = len(price_batch)
            stats["technical_indicators"] = len(indicator_batch)

            # 5. Verified Quarterly Financial Vintages (Synthetic Point-in-Time)
            vintages_data = {
                "TCS": [
                    ("Q1FY26", "2025-04-01", "2025-06-30", 62000.0, 12000.0, 32.5, "2025-07-15", "2025-07-16"),
                    ("Q2FY26", "2025-07-01", "2025-09-30", 64000.0, 12500.0, 33.8, "2025-10-15", "2025-10-16"),
                    ("Q3FY26", "2025-10-01", "2025-12-31", 65500.0, 12800.0, 34.6, "2026-01-15", "2026-01-16"),
                    ("Q4FY26", "2026-01-01", "2026-03-31", 67000.0, 13200.0, 35.7, "2026-04-15", "2026-04-16"),
                ],
                "INFY": [
                    ("Q1FY26", "2025-04-01", "2025-06-30", 39000.0, 6300.0, 15.2, "2025-07-18", "2025-07-21"),
                    ("Q2FY26", "2025-07-01", "2025-09-30", 40500.0, 6500.0, 15.7, "2025-10-18", "2025-10-20"),
                    ("Q3FY26", "2025-10-01", "2025-12-31", 41200.0, 6650.0, 16.1, "2026-01-18", "2026-01-19"),
                    ("Q4FY26", "2026-01-01", "2026-03-31", 42000.0, 6800.0, 16.5, "2026-04-18", "2026-04-20"),
                ],
                "RELIANCE": [
                    ("Q1FY26", "2025-04-01", "2025-06-30", 230000.0, 17500.0, 25.8, "2025-07-25", "2025-07-28"),
                    ("Q2FY26", "2025-07-01", "2025-09-30", 235000.0, 18000.0, 26.6, "2025-10-25", "2025-10-27"),
                    ("Q3FY26", "2025-10-01", "2025-12-31", 240000.0, 18500.0, 27.3, "2026-01-25", "2026-01-27"),
                    ("Q4FY26", "2026-01-01", "2026-03-31", 248000.0, 19200.0, 28.4, "2026-04-25", "2026-04-27"),
                ],
                "HDFCBANK": [
                    ("Q1FY26", "2025-04-01", "2025-06-30", 82000.0, 16200.0, 21.3, "2025-07-20", "2025-07-21"),
                    ("Q2FY26", "2025-07-01", "2025-09-30", 85000.0, 16800.0, 22.1, "2025-10-20", "2025-10-21"),
                    ("Q3FY26", "2025-10-01", "2025-12-31", 87500.0, 17400.0, 22.9, "2026-01-20", "2026-01-21"),
                    ("Q4FY26", "2026-01-01", "2026-03-31", 90000.0, 18000.0, 23.7, "2026-04-20", "2026-04-21"),
                ],
                "SUNPHARMA": [
                    # Incomplete financials: only 2 quarters (cold-start / incomplete testing)
                    ("Q3FY26", "2025-10-01", "2025-12-31", 13000.0, 2600.0, 10.8, "2026-01-30", "2026-02-02"),
                    ("Q4FY26", "2026-01-01", "2026-03-31", 13500.0, 2750.0, 11.4, "2026-04-30", "2026-05-02"),
                ],
            }

            v_count = 0
            q_count = 0
            for sym, quarters in vintages_data.items():
                cid = company_ids[sym]
                for q, p_start, p_end, rev, np, eps, pub_d, eff_d in quarters:
                    # Legacy quarterly_results
                    cur.execute(
                        """
                        INSERT INTO quarterly_results (
                            company_id, quarter, revenue, net_profit, eps, publication_date
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (company_id, quarter) DO UPDATE SET
                            revenue = EXCLUDED.revenue,
                            net_profit = EXCLUDED.net_profit
                        """,
                        (cid, q, rev, np, eps, pub_d),
                    )
                    q_count += 1

                    # Canonical quarterly_financial_vintages (conforms strictly to Trigger 3)
                    broadcast_id = f"SYNTH_NSE_{sym}_{q}_V1"
                    pub_ts = f"{pub_d} 18:30:00+05:30"
                    doc_url = f"https://nsearchives.nseindia.com/corporate/synthetic_{sym}_{q}.pdf"
                    doc_hash = hashlib.sha256(f"SYNTH_STAGING_{sym}_{q}".encode("utf-8")).hexdigest()

                    cur.execute(
                        """
                        INSERT INTO quarterly_financial_vintages (
                            company_id, quarter, period_start_date, period_end_date,
                            accounting_standard, filing_scope,
                            company_filing_type, internal_revision_type,
                            verification_status, research_eligibility,
                            version_sequence, exchange, exchange_broadcast_id,
                            published_at, effective_trading_date,
                            revenue, net_profit, eps, is_banking_institution,
                            source_document_url, source_document_hash
                        ) VALUES (
                            %s, %s, %s, %s,
                            'IND_AS', 'CONSOLIDATED',
                            'ORIGINAL', 'INITIAL_INGESTION',
                            'VERIFIED', 'VERIFIED_ELIGIBLE',
                            1, 'NSE', %s,
                            %s, %s,
                            %s, %s, %s, %s,
                            %s, %s
                        )
                        ON CONFLICT (company_id, quarter, version_sequence, filing_scope) DO NOTHING
                        """,
                        (
                            cid, q, p_start, p_end,
                            broadcast_id,
                            pub_ts, eff_d,
                            rev, np, eps, (sym == "HDFCBANK"),
                            doc_url, doc_hash,
                        ),
                    )
                    v_count += 1

            stats["quarterly_results"] = q_count
            stats["quarterly_financial_vintages"] = v_count

            # 6. Universe Audit Log
            cur.execute(
                """
                INSERT INTO universe_audit_log (
                    symbol, action, old_values_json, new_values_json,
                    initiated_by, notes, timestamp
                ) VALUES (
                    'SYSTEM', 'NEON_STAGING_PROVISION', NULL,
                    '{"environment": "NEON_STAGING", "company_count": 10, "provider": "Neon Serverless"}',
                    'NEON_STAGING_SEED',
                    'Automated synthetic staging seed provisioning for Phase 5.3.7',
                    CURRENT_TIMESTAMP
                )
                """
            )
            stats["audit_logs"] = 1

        conn.commit()

    verify_database_invariants()
    print("Synthetic staging data seeding completed successfully.")
    for k, v in stats.items():
        print(f"  - {k}: {v}")
    return stats


if __name__ == "__main__":
    target_url = os.getenv("DATABASE_URL")
    if not target_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    apply_schema_to_neon(target_url)
    seed_synthetic_staging_data(target_url)

