import sqlite3
from pathlib import Path


from backend.config import DATABASE_PATH, DATABASE_DIR, PROJECT_ROOT


def create_database():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # Enable foreign key relationships
    cursor.execute("PRAGMA foreign_keys = ON")

    # ---------------------------------------------------------
    # 1. COMPANIES
    # ---------------------------------------------------------
    cursor.execute("""
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
            source TEXT DEFAULT 'INITIAL_UNIVERSE'
        )
    """)

    # ---------------------------------------------------------
    # 1.1 UNIVERSE AUDIT LOG
    # ---------------------------------------------------------
    cursor.execute("""
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

    # ---------------------------------------------------------
    # 2. DAILY PRICES
    # ---------------------------------------------------------
    cursor.execute("""
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

            FOREIGN KEY (company_id)
                REFERENCES companies(id),

            UNIQUE(company_id, date)
        )
    """)

    # ---------------------------------------------------------
    # 3. QUARTERLY RESULTS
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            revenue REAL,
            net_profit REAL,
            eps REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id)
        )
    """)

    # ---------------------------------------------------------
    # 4. TECHNICAL INDICATORS
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            rsi REAL,
            macd REAL,
            macd_signal REAL,
            ema_20 REAL,
            ema_50 REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id),

            UNIQUE(company_id, date)
        )
    """)

    # ---------------------------------------------------------
    # 5. FINANCIAL SCORES
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            profitability_score REAL,
            growth_score REAL,
            valuation_score REAL,
            overall_score REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id)
        )
    """)

    # ---------------------------------------------------------
    # 6. OPPORTUNITY SCORES
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunity_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            technical_score REAL,
            financial_score REAL,
            momentum_score REAL,
            opportunity_score REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id)
        )
    """)

    # ---------------------------------------------------------
    # 7. SIGNALS
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            signal TEXT,
            entry_price REAL,
            stop_loss REAL,
            target_price REAL,
            confidence REAL,

            FOREIGN KEY (company_id)
                REFERENCES companies(id)
        )
    """)

    connection.commit()
    connection.close()

    print("======================================")
    print("SQLite database created successfully!")
    print(f"Database: {DATABASE_PATH}")
    print("======================================")


if __name__ == "__main__":
    create_database()