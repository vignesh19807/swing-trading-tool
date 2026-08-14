import sqlite3
from pathlib import Path

from fetch_yfinance import STOCKS, fetch_stock_data


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
# COMPANY INFORMATION
# ============================================================

COMPANY_INFO = {
    "INFY.NS": {
        "company_name": "Infosys",
        "sector": "IT",
    },
    "TCS.NS": {
        "company_name": "Tata Consultancy Services",
        "sector": "IT",
    },
    "WIPRO.NS": {
        "company_name": "Wipro",
        "sector": "IT",
    },
    "RELIANCE.NS": {
        "company_name": "Reliance Industries",
        "sector": "Energy",
    },
    "HDFCBANK.NS": {
        "company_name": "HDFC Bank",
        "sector": "Banking",
    },
    "ITC.NS": {
        "company_name": "ITC",
        "sector": "FMCG",
    },
}


# ============================================================
# INSERT COMPANY
# ============================================================

def get_or_create_company(cursor, symbol):

    info = COMPANY_INFO[symbol]

    clean_symbol = symbol.replace(".NS", "")

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE symbol = ?
        """,
        (clean_symbol,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    cursor.execute(
        """
        INSERT INTO companies (
            symbol,
            company_name,
            sector,
            exchange
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            clean_symbol,
            info["company_name"],
            info["sector"],
            "NSE",
        )
    )

    return cursor.lastrowid


# ============================================================
# INSERT DAILY PRICES
# ============================================================

def insert_daily_prices(cursor, company_id, data):

    inserted = 0
    skipped = 0

    for _, row in data.iterrows():

        cursor.execute(
            """
            INSERT OR IGNORE INTO daily_prices (
                company_id,
                date,
                open,
                high,
                low,
                close,
                volume,
                adjusted_close
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                row["date"].isoformat(),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row["volume"]),
                float(row["adjusted_close"]),
            )
        )

        if cursor.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print("==========================================")
    print("DATABASE DATA INSERTION")
    print("==========================================")

    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    total_inserted = 0
    total_skipped = 0

    for symbol in STOCKS:

        print(f"\nProcessing {symbol}...")

        # ----------------------------------------------------
        # Download data
        # ----------------------------------------------------

        data = fetch_stock_data(symbol)

        if data is None:

            print(f"FAILED: No data for {symbol}")

            continue

        # ----------------------------------------------------
        # Create/get company
        # ----------------------------------------------------

        company_id = get_or_create_company(
            cursor,
            symbol
        )

        # ----------------------------------------------------
        # Insert price records
        # ----------------------------------------------------

        inserted, skipped = insert_daily_prices(
            cursor,
            company_id,
            data
        )

        total_inserted += inserted
        total_skipped += skipped

        print(
            f"{symbol}: "
            f"{inserted} inserted, "
            f"{skipped} skipped"
        )

    # Save everything
    connection.commit()

    connection.close()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("\n==========================================")
    print("INSERTION COMPLETE")
    print("==========================================")

    print(f"Total inserted: {total_inserted}")
    print(f"Total skipped:  {total_skipped}")

    print("==========================================")


if __name__ == "__main__":
    main()