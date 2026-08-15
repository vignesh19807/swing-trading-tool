"""
Week 2 Market Data Loader
=========================

Loads historical market data for the complete stock universe
and stores it in the existing SQLite database.

Pipeline:

stock_universe.py
        ↓
load_stock_data.py
        ↓
yfinance
        ↓
Clean + Validate
        ↓
SQLite
"""

import sqlite3
from pathlib import Path

import yfinance as yf
import pandas as pd

from stock_universe import STOCK_UNIVERSE


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
# CONFIGURATION
# ============================================================

HISTORY_PERIOD = "2y"
INTERVAL = "1d"


# ============================================================
# FETCH DATA
# ============================================================

def fetch_stock_data(symbol):
    """
    Download approximately two years of daily market data
    for one NSE stock.
    """

    yahoo_symbol = f"{symbol}.NS"

    print(f"\nDownloading {yahoo_symbol}...")

    try:

        ticker = yf.Ticker(yahoo_symbol)

        data = ticker.history(
            period=HISTORY_PERIOD,
            interval=INTERVAL,
            auto_adjust=False
        )

        if data.empty:

            print(
                f"❌ No data received for {symbol}"
            )

            return None

        # Convert index into a normal column
        data = data.reset_index()

        # Make sure required columns exist
        required_columns = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Adj Close",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:

            print(
                f"❌ Missing columns for {symbol}: "
                f"{missing_columns}"
            )

            return None

        # Keep only required columns
        data = data[required_columns].copy()

        # Standardize column names
        data.columns = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
        ]

        # ----------------------------------------------------
        # DATA TYPE CLEANING
        # ----------------------------------------------------

        data["date"] = pd.to_datetime(data["date"])

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
        ]

        for column in numeric_columns:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

        # Remove rows with missing critical values
        data = data.dropna(
            subset=[
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

        # Remove duplicate dates
        data = data.drop_duplicates(
            subset=["date"]
        )

        # Sort chronologically
        data = data.sort_values(
            "date"
        ).reset_index(drop=True)

        return data

    except Exception as error:

        print(
            f"❌ Failed to download "
            f"{symbol}: {error}"
        )

        return None


# ============================================================
# VALIDATE DATA BEFORE INSERTION
# ============================================================

def validate_stock_data(symbol, data):
    """
    Perform basic validation before inserting
    market data into SQLite.
    """

    if data is None or data.empty:

        return False, "No data"

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    required_columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing_values = data[
        required_columns
    ].isnull().sum()

    if missing_values.any():

        return (
            False,
            f"Missing values: "
            f"{missing_values.to_dict()}"
        )

    # --------------------------------------------------------
    # Positive prices
    # --------------------------------------------------------

    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in price_columns:

        if (data[column] <= 0).any():

            return (
                False,
                f"Invalid price in {column}"
            )

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    if (data["volume"] < 0).any():

        return (
            False,
            "Negative volume detected"
        )

    # --------------------------------------------------------
    # OHLC relationships
    # --------------------------------------------------------

    invalid_ohlc = (
        (data["high"] < data["open"])
        | (data["high"] < data["close"])
        | (data["high"] < data["low"])
        | (data["low"] > data["open"])
        | (data["low"] > data["close"])
    )

    if invalid_ohlc.any():

        return (
            False,
            "Invalid OHLC relationship"
        )

    # --------------------------------------------------------
    # Duplicate dates
    # --------------------------------------------------------

    if data["date"].duplicated().any():

        return (
            False,
            "Duplicate dates detected"
        )

    return True, "Valid"


# ============================================================
# INSERT / GET COMPANY
# ============================================================

def get_or_create_company(cursor, stock):
    """
    Find an existing company or create it
    using the Week 2 stock universe metadata.
    """

    symbol = stock["symbol"]

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE symbol = ?
        """,
        (symbol,)
    )

    result = cursor.fetchone()

    if result:

        company_id = result[0]

        # Update metadata so the database
        # reflects the current stock universe.
        cursor.execute(
            """
            UPDATE companies
            SET company_name = ?,
                sector = ?,
                industry = ?,
                exchange = ?
            WHERE id = ?
            """,
            (
                stock["name"],
                stock["sector"],
                stock["industry"],
                stock["exchange"],
                company_id,
            )
        )

        return company_id

    cursor.execute(
        """
        INSERT INTO companies (
            symbol,
            company_name,
            sector,
            industry,
            exchange
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            symbol,
            stock["name"],
            stock["sector"],
            stock["industry"],
            stock["exchange"],
        )
    )

    return cursor.lastrowid


# ============================================================
# INSERT DAILY PRICES
# ============================================================

def insert_daily_prices(
    cursor,
    company_id,
    data
):
    """
    Insert daily price records.

    Existing records are ignored because
    (company_id, date) is UNIQUE in the database.
    """

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
                (
                    float(row["adjusted_close"])
                    if pd.notna(
                        row["adjusted_close"]
                    )
                    else None
                ),
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

    print("\n==========================================")
    print("SWING TRADING PLATFORM")
    print("WEEK 2 MARKET DATA LOADER")
    print("==========================================")

    print(
        f"Stock universe: "
        f"{len(STOCK_UNIVERSE)} stocks"
    )

    print(
        f"History period: "
        f"{HISTORY_PERIOD}"
    )

    print(
        f"Database: "
        f"{DATABASE_PATH}"
    )

    # --------------------------------------------------------
    # Connect to database
    # --------------------------------------------------------

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA foreign_keys = ON"
    )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    successful_stocks = 0
    failed_stocks = []

    total_inserted = 0
    total_skipped = 0

    # --------------------------------------------------------
    # Process every stock
    # --------------------------------------------------------

    for index, stock in enumerate(
        STOCK_UNIVERSE,
        start=1
    ):

        symbol = stock["symbol"]

        print("\n------------------------------------------")

        print(
            f"[{index}/{len(STOCK_UNIVERSE)}] "
            f"Processing {symbol}"
        )

        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

        data = fetch_stock_data(
            symbol
        )

        if data is None:

            failed_stocks.append(
                (
                    symbol,
                    "Download failed"
                )
            )

            continue

        print(
            f"Downloaded: "
            f"{len(data)} records"
        )

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        valid, message = validate_stock_data(
            symbol,
            data
        )

        if not valid:

            print(
                f"❌ Validation failed: "
                f"{message}"
            )

            failed_stocks.append(
                (
                    symbol,
                    message
                )
            )

            continue

        print("✓ Data validation passed")

        # ----------------------------------------------------
        # Company
        # ----------------------------------------------------

        company_id = get_or_create_company(
            cursor,
            stock
        )

        # ----------------------------------------------------
        # Daily prices
        # ----------------------------------------------------

        inserted, skipped = insert_daily_prices(
            cursor,
            company_id,
            data
        )

        total_inserted += inserted
        total_skipped += skipped

        successful_stocks += 1

        print(
            f"✓ Inserted: {inserted}"
        )

        print(
            f"✓ Skipped existing: {skipped}"
        )

        # Commit after each stock.
        # This protects already processed stocks
        # if a later stock fails.
        connection.commit()

    # --------------------------------------------------------
    # Close database
    # --------------------------------------------------------

    connection.close()

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n==========================================")
    print("WEEK 2 DATA LOAD COMPLETE")
    print("==========================================")

    print(
        f"Stocks processed : "
        f"{len(STOCK_UNIVERSE)}"
    )

    print(
        f"Successful       : "
        f"{successful_stocks}"
    )

    print(
        f"Failed           : "
        f"{len(failed_stocks)}"
    )

    print(
        f"Records inserted : "
        f"{total_inserted}"
    )

    print(
        f"Records skipped  : "
        f"{total_skipped}"
    )

    # --------------------------------------------------------
    # Failed stocks
    # --------------------------------------------------------

    if failed_stocks:

        print("\nFAILED STOCKS")
        print("------------------------------------------")

        for symbol, reason in failed_stocks:

            print(
                f"{symbol}: {reason}"
            )

    else:

        print("\n✓ No failed stocks")

    print("------------------------------------------")

    if not failed_stocks:

        print(
            "🎉 ALL STOCKS PROCESSED SUCCESSFULLY"
        )

    else:

        print(
            "⚠ SOME STOCKS NEED REVIEW"
        )

    print("==========================================\n")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()