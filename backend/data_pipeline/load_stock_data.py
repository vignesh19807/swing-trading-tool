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
Data Provider
        ↓
yfinance_provider.py
        ↓
yfinance
        ↓
Clean + Validate
        ↓
SQLite
"""

import sqlite3
from pathlib import Path

import pandas as pd

from backend.data_pipeline.stock_universe import STOCK_UNIVERSE
from backend.config import HISTORY_YEARS
from datetime import datetime, timedelta, timezone

from backend.data_pipeline.providers.yfinance_provider import (
    fetch_stock_data as provider_fetch_stock_data
)

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




# ============================================================
# FETCH DATA
# ============================================================

def fetch_stock_data(symbol, start_date=None, end_date=None):
    """
    Download approximately two years of daily market data
    using the configured market-data provider.

    The actual provider-specific logic is handled by
    yfinance_provider.py.
    """

    try:

        data = provider_fetch_stock_data(
            symbol,
            start_date=start_date,
            end_date=end_date
        )

        if data is None or data.empty:

            print(
                f"❌ No data received for {symbol}"
            )

            return None

        # ----------------------------------------------------
        # DATA TYPE CLEANING
        # ----------------------------------------------------

        data["date"] = pd.to_datetime(
            data["date"]
        )

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

        # ----------------------------------------------------
        # REMOVE MISSING CRITICAL VALUES
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # REMOVE DUPLICATE DATES
        # ----------------------------------------------------

        data = data.drop_duplicates(
            subset=["date"]
        )

        # ----------------------------------------------------
        # SORT CHRONOLOGICALLY
        # ----------------------------------------------------

        data = (
            data
            .sort_values("date")
            .reset_index(drop=True)
        )

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
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:

        return (
            False,
            f"Missing columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # MISSING VALUES
    # --------------------------------------------------------

    missing_values = (
        data[required_columns]
        .isnull()
        .sum()
    )

    if missing_values.any():

        return (
            False,
            f"Missing values: "
            f"{missing_values.to_dict()}"
        )

    # --------------------------------------------------------
    # POSITIVE PRICES
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
    # VOLUME
    # --------------------------------------------------------

    if (data["volume"] < 0).any():

        return (
            False,
            "Negative volume detected"
        )

    # --------------------------------------------------------
    # OHLC RELATIONSHIPS
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
    # DUPLICATE DATES
    # --------------------------------------------------------

    if data["date"].duplicated().any():

        return (
            False,
            "Duplicate dates detected"
        )

    # --------------------------------------------------------
    # DATE ORDER
    # --------------------------------------------------------

    if not data["date"].is_monotonic_increasing:

        return (
            False,
            "Dates are not sorted chronologically"
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

    # --------------------------------------------------------
    # FIND EXISTING COMPANY
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # UPDATE METADATA
        # ----------------------------------------------------

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

    # --------------------------------------------------------
    # CREATE COMPANY
    # --------------------------------------------------------

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
        f"{HISTORY_YEARS} years"
    )

    print(
        f"Database: "
        f"{DATABASE_PATH}"
    )

    # --------------------------------------------------------
    # CONNECT TO DATABASE
    # --------------------------------------------------------

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA foreign_keys = ON"
    )

    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------

    successful_stocks = 0

    failed_stocks = []

    total_inserted = 0

    total_skipped = 0

    # --------------------------------------------------------
    # PROCESS EVERY STOCK
    # --------------------------------------------------------

    for index, stock in enumerate(
        STOCK_UNIVERSE,
        start=1
    ):

        symbol = stock["symbol"]

        print(
            "\n------------------------------------------"
        )

        print(
            f"[{index}/{len(STOCK_UNIVERSE)}] "
            f"Processing {symbol}"
        )

        # ----------------------------------------------------
        # COMPANY
        # ----------------------------------------------------

        company_id = get_or_create_company(
            cursor,
            stock
        )

        # ----------------------------------------------------
        # DETERMINE BACKFILL / START DATE
        # ----------------------------------------------------

        target_start_date = (
            datetime.now(timezone.utc) - timedelta(days=365 * HISTORY_YEARS)
        ).strftime('%Y-%m-%d')

        start_date = target_start_date

        cursor.execute("SELECT MIN(date), MAX(date) FROM daily_prices WHERE company_id = ?", (company_id,))
        min_max_row = cursor.fetchone()

        if min_max_row and min_max_row[0] and min_max_row[1]:
            min_date = min_max_row[0][:10]
            max_date = min_max_row[1][:10]
            
            # If the database already has the required history,
            # just fetch from the latest date to today.
            if min_date <= target_start_date:
                start_date = max_date

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        data = fetch_stock_data(
            symbol,
            start_date=start_date
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
        # VALIDATE
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

        print(
            "✓ Data validation passed"
        )

        # ----------------------------------------------------
        # DAILY PRICES
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

        # ----------------------------------------------------
        # COMMIT AFTER EACH STOCK
        # ----------------------------------------------------

        connection.commit()

    # --------------------------------------------------------
    # CLOSE DATABASE
    # --------------------------------------------------------

    connection.close()

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "WEEK 2 DATA LOAD COMPLETE"
    )

    print(
        "=========================================="
    )

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
    # FAILED STOCKS
    # --------------------------------------------------------

    if failed_stocks:

        print(
            "\nFAILED STOCKS"
        )

        print(
            "------------------------------------------"
        )

        for symbol, reason in failed_stocks:

            print(
                f"{symbol}: {reason}"
            )

    else:

        print(
            "\n✓ No failed stocks"
        )

    print(
        "------------------------------------------"
    )

    if not failed_stocks:

        print(
            "🎉 ALL STOCKS PROCESSED SUCCESSFULLY"
        )

    else:

        print(
            "⚠ SOME STOCKS NEED REVIEW"
        )

    print(
        "==========================================\n"
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()