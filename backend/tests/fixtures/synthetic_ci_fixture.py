"""
Synthetic CI Test Fixture Generator
====================================
Generates a minimal, non-sensitive, purely synthetic SQLite test database fixture
specifically for portable CI API contract verification and routing tests.

Provenance & Verification:
- Contains ZERO authentic financial records or proprietary market data.
- Built strictly from database schema columns.
- Seeds 52 synthetic company symbols (including INFY) to satisfy universe size assertions.
- Seeds 200 synthetic OHLCV bars and technical indicators for INFY.
- Safe for public CI runners; never touches or exposes production databases.
"""

import sqlite3
import datetime
from pathlib import Path

def create_synthetic_ci_database(db_path: Path) -> Path:
    """Create and seed minimal synthetic database for portable CI contract testing."""
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    # 1. Sectors and Industries
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS industries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )
    """)

    # 2. Companies Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            sector TEXT,
            industry TEXT,
            exchange TEXT,
            sector_id INTEGER,
            industry_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            listing_date TEXT,
            created_at TEXT,
            updated_at TEXT,
            source TEXT DEFAULT 'INITIAL_UNIVERSE',
            FOREIGN KEY (sector_id) REFERENCES sectors(id),
            FOREIGN KEY (industry_id) REFERENCES industries(id)
        )
    """)

    # 2.1 Universe Audit Log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS universe_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            old_values_json TEXT,
            new_values_json TEXT,
            initiated_by TEXT NOT NULL DEFAULT 'SYSTEM',
            notes TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    # 3. Daily Prices Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            adjusted_close REAL,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            UNIQUE(company_id, date)
        )
    """)

    # 4. Quarterly Results Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
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
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # 5. Technical Indicators Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
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
            FOREIGN KEY (company_id) REFERENCES companies(id),
            UNIQUE(company_id, date)
        )
    """)

    # 6. Financial Scores Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            profitability_score REAL,
            growth_score REAL,
            valuation_score REAL,
            overall_score REAL,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # 7. Opportunity Scores Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS opportunity_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            technical_score REAL,
            financial_score REAL,
            momentum_score REAL,
            opportunity_score REAL,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # 8. Signals Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            signal TEXT,
            entry_price REAL,
            stop_loss REAL,
            target_price REAL,
            confidence REAL,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    # 9. Backtest Tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id TEXT PRIMARY KEY,
            strategy_version TEXT,
            start_date TEXT,
            end_date TEXT,
            initial_capital REAL,
            config_json TEXT,
            status TEXT,
            metrics_json TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtest_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT,
            run_id TEXT,
            symbol TEXT,
            direction TEXT,
            signal_date TEXT,
            entry_date TEXT,
            entry_price REAL,
            exit_date TEXT,
            exit_price REAL,
            quantity INTEGER,
            initial_value REAL,
            gross_pl REAL,
            entry_costs REAL,
            exit_costs REAL,
            total_costs REAL,
            net_pl REAL,
            return_pct REAL,
            status TEXT,
            exit_reason TEXT,
            holding_days INTEGER,
            trade_metadata TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtest_equity_curve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            date TEXT,
            cash REAL,
            positions_value REAL,
            total_equity REAL,
            drawdown_pct REAL,
            created_at TEXT
        )
    """)

    # Seed 5 Sectors
    sectors = ['Information Technology', 'Financial Services', 'Energy', 'Automobile', 'Healthcare']
    for s in sectors:
        cur.execute("INSERT INTO sectors (name) VALUES (?)", (s,))

    # Seed 1 Industry
    cur.execute("INSERT INTO industries (name, sector_id) VALUES ('IT Services', 1)")

    # Seed 52 Synthetic Companies
    cur.execute("""
        INSERT INTO companies (symbol, company_name, sector, industry, exchange, sector_id, industry_id)
        VALUES ('INFY', 'Infosys Limited', 'Information Technology', 'IT Services', 'NSE', 1, 1)
    """)
    for i in range(1, 52):
        sym = f"STUB{i:02d}"
        cur.execute("""
            INSERT INTO companies (symbol, company_name, sector, industry, exchange, sector_id, industry_id)
            VALUES (?, ?, 'Information Technology', 'IT Services', 'NSE', 1, 1)
        """, (sym, f"Synthetic Stub Company {i}"))

    # Seed 200 Synthetic Daily Prices & Technicals for INFY (company_id=1)
    base_date = datetime.date(2025, 1, 1)
    base_price = 1500.0
    for day in range(200):
        d_str = (base_date + datetime.timedelta(days=day)).isoformat()
        close_p = base_price + (day * 0.5)
        cur.execute("""
            INSERT INTO daily_prices (company_id, date, open, high, low, close, volume, adjusted_close)
            VALUES (1, ?, ?, ?, ?, ?, 100000, ?)
        """, (d_str, close_p - 5.0, close_p + 10.0, close_p - 10.0, close_p, close_p))

        cur.execute("""
            INSERT INTO technical_indicators (company_id, date, rsi, macd, macd_signal, ema_20, ema_50, ema_200, macd_histogram, atr_14, technical_score)
            VALUES (1, ?, 55.0, 1.2, 1.0, ?, ?, ?, 0.2, 15.0, 75.0)
        """, (d_str, close_p - 2.0, close_p - 5.0, close_p - 10.0))

    conn.commit()
    conn.close()
    return db_path
