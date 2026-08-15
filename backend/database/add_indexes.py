"""
Database Indexes
================

Creates indexes that improve query performance
for the Swing Trading Platform database.
"""

import sqlite3
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "swing_trading.db"
)


# ============================================================
# CREATE INDEXES
# ============================================================

def create_indexes():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    print("==========================================")
    print("DATABASE INDEX CREATION")
    print("==========================================")

    # --------------------------------------------------------
    # Daily price lookup index
    # --------------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_daily_prices_company_date
        ON daily_prices(company_id, date)
    """)

    print(
        "✓ idx_daily_prices_company_date"
    )

    # --------------------------------------------------------
    # Technical indicator lookup
    # --------------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_technical_indicators_company_date
        ON technical_indicators(company_id, date)
    """)

    print(
        "✓ idx_technical_indicators_company_date"
    )

    # --------------------------------------------------------
    # Financial score lookup
    # --------------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_financial_scores_company_date
        ON financial_scores(company_id, date)
    """)

    print(
        "✓ idx_financial_scores_company_date"
    )

    # --------------------------------------------------------
    # Opportunity score lookup
    # --------------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_opportunity_scores_company_date
        ON opportunity_scores(company_id, date)
    """)

    print(
        "✓ idx_opportunity_scores_company_date"
    )

    # --------------------------------------------------------
    # Signals lookup
    # --------------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_signals_company_date
        ON signals(company_id, date)
    """)

    print(
        "✓ idx_signals_company_date"
    )

    connection.commit()

    connection.close()

    print("------------------------------------------")
    print("✓ Database indexes created successfully")
    print("==========================================")
    

# ============================================================
# VERIFY INDEXES
# ============================================================

def verify_indexes():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            name,
            tbl_name
        FROM sqlite_master
        WHERE type = 'index'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    indexes = cursor.fetchall()

    connection.close()

    print("\n==========================================")
    print("DATABASE INDEX VERIFICATION")
    print("==========================================")

    for name, table in indexes:

        print(
            f"✓ {name} → {table}"
        )

    print("------------------------------------------")

    print(
        f"Total custom indexes: "
        f"{len(indexes)}"
    )

    print("==========================================")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    create_indexes()

    verify_indexes()