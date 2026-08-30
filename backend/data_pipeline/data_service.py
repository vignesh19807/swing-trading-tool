"""
Data Service
============

Provides a simple interface for the Logic Engine to access
validated market data from the SQLite database.

Architecture:

SQLite Database
       ↓
Data Service
       ↓
Pandas DataFrame
       ↓
Technical / Logic Engine
"""

import sqlite3
from pathlib import Path

import pandas as pd


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
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create a connection to the project SQLite database.
    """

    if not DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    return connection


# ============================================================
# GET STOCK DATA
# ============================================================

def get_stock_data(
    symbol,
    start_date=None,
    end_date=None
):
    """
    Return historical OHLCV data for a stock.

    Parameters
    ----------
    symbol : str
        NSE stock symbol, for example "INFY".

    start_date : str, optional
        Starting date, for example "2025-01-01".

    end_date : str, optional
        Ending date, for example "2026-01-01".

    Returns
    -------
    pandas.DataFrame

        Columns:

        date
        open
        high
        low
        close
        volume
    """

    symbol = symbol.upper().strip()

    connection = get_connection()

    try:

        query = """
            SELECT
                dp.date,
                dp.open,
                dp.high,
                dp.low,
                dp.close,
                dp.volume
            FROM daily_prices AS dp
            INNER JOIN companies AS c
                ON dp.company_id = c.id
            WHERE c.symbol = ?
        """

        parameters = [symbol]

        # ----------------------------------------------------
        # Optional start date
        # ----------------------------------------------------

        if start_date is not None:

            query += """
                AND dp.date >= ?
            """

            parameters.append(start_date)

        # ----------------------------------------------------
        # Optional end date
        # ----------------------------------------------------

        if end_date is not None:
            end_date_str = str(end_date).strip()
            if len(end_date_str) == 10:
                end_date_str = f"{end_date_str}T23:59:59+05:30"
            query += """
                AND dp.date <= ?
            """
            parameters.append(end_date_str)

        # ----------------------------------------------------
        # Always return chronological data
        # ----------------------------------------------------

        query += """
            ORDER BY dp.date ASC
        """

        data = pd.read_sql_query(
            query,
            connection,
            params=parameters
        )

    finally:

        connection.close()

    # --------------------------------------------------------
    # Convert date
    # --------------------------------------------------------

    if not data.empty:

        data["date"] = pd.to_datetime(
            data["date"]
        )

    return data


# ============================================================
# GET STOCK DATA INCLUDING ADJUSTED CLOSE
# ============================================================

def get_stock_data_with_adjusted_close(
    symbol,
    start_date=None,
    end_date=None
):
    """
    Return historical OHLCV data including adjusted close.

    This function is useful when an analysis requires
    adjusted closing prices.
    """

    symbol = symbol.upper().strip()

    connection = get_connection()

    try:

        query = """
            SELECT
                dp.date,
                dp.open,
                dp.high,
                dp.low,
                dp.close,
                dp.volume,
                dp.adjusted_close
            FROM daily_prices AS dp
            INNER JOIN companies AS c
                ON dp.company_id = c.id
            WHERE c.symbol = ?
        """

        parameters = [symbol]

        if start_date is not None:

            query += """
                AND dp.date >= ?
            """

            parameters.append(start_date)

        if end_date is not None:
            end_date_str = str(end_date).strip()
            if len(end_date_str) == 10:
                end_date_str = f"{end_date_str}T23:59:59+05:30"
            query += """
                AND dp.date <= ?
            """
            parameters.append(end_date_str)

        query += """
            ORDER BY dp.date ASC
        """

        data = pd.read_sql_query(
            query,
            connection,
            params=parameters
        )

    finally:

        connection.close()

    if not data.empty:

        data["date"] = pd.to_datetime(
            data["date"]
        )

    return data


# ============================================================
# GET LATEST PRICE
# ============================================================

def get_latest_price(symbol):
    """
    Return the latest available price record
    for a stock.
    """

    symbol = symbol.upper().strip()

    connection = get_connection()

    try:

        query = """
            SELECT
                dp.date,
                dp.open,
                dp.high,
                dp.low,
                dp.close,
                dp.volume
            FROM daily_prices AS dp
            INNER JOIN companies AS c
                ON dp.company_id = c.id
            WHERE c.symbol = ?
            ORDER BY dp.date DESC
            LIMIT 1
        """

        data = pd.read_sql_query(
            query,
            connection,
            params=[symbol]
        )

    finally:

        connection.close()

    if data.empty:

        return None

    data["date"] = pd.to_datetime(
        data["date"]
    )

    return data.iloc[0].to_dict()


# ============================================================
# GET AVAILABLE STOCKS
# ============================================================

def get_available_stocks():
    """
    Return all stock symbols currently available
    in the database.
    """

    connection = get_connection()

    try:

        query = """
            SELECT
                symbol,
                company_name,
                sector,
                industry,
                exchange
            FROM companies
            ORDER BY symbol
        """

        data = pd.read_sql_query(
            query,
            connection
        )

    finally:

        connection.close()

    return data


# ============================================================
# GET RECORD COUNT
# ============================================================

def get_stock_record_count(symbol):
    """
    Return the number of daily price records
    available for a stock.
    """

    symbol = symbol.upper().strip()

    connection = get_connection()

    try:

        query = """
            SELECT COUNT(*)
            FROM daily_prices AS dp
            INNER JOIN companies AS c
                ON dp.company_id = c.id
            WHERE c.symbol = ?
        """

        cursor = connection.cursor()

        cursor.execute(
            query,
            (symbol,)
        )

        result = cursor.fetchone()

    finally:

        connection.close()

    return result[0]


# ============================================================
# TEST DATA SERVICE
# ============================================================

def main():

    print("\n==========================================")
    print("SWING TRADING PLATFORM")
    print("DATA SERVICE TEST")
    print("==========================================")

    # --------------------------------------------------------
    # Test 1 — Available stocks
    # --------------------------------------------------------

    stocks = get_available_stocks()

    print(
        f"\nAvailable stocks: "
        f"{len(stocks)}"
    )

    print("\nFirst 10 stocks:")

    print(
        stocks.head(10).to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Test 2 — INFY
    # --------------------------------------------------------

    print("\n------------------------------------------")
    print("TEST: get_stock_data('INFY')")
    print("------------------------------------------")

    data = get_stock_data("INFY")

    if data.empty:

        print("❌ No data returned")

    else:

        print(
            f"✓ Records returned: "
            f"{len(data)}"
        )

        print(
            f"✓ Columns: "
            f"{list(data.columns)}"
        )

        print("\nFirst 5 records:")

        print(
            data.head().to_string(
                index=False
            )
        )

        print("\nLast 5 records:")

        print(
            data.tail().to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Test 3 — Record count
    # --------------------------------------------------------

    print("\n------------------------------------------")
    print("TEST: Record Count")
    print("------------------------------------------")

    count = get_stock_record_count(
        "INFY"
    )

    print(
        f"INFY records: {count}"
    )

    # --------------------------------------------------------
    # Test 4 — Latest price
    # --------------------------------------------------------

    print("\n------------------------------------------")
    print("TEST: Latest Price")
    print("------------------------------------------")

    latest = get_latest_price(
        "INFY"
    )

    if latest:

        print(
            f"Date   : {latest['date']}"
        )

        print(
            f"Open   : {latest['open']}"
        )

        print(
            f"High   : {latest['high']}"
        )

        print(
            f"Low    : {latest['low']}"
        )

        print(
            f"Close  : {latest['close']}"
        )

        print(
            f"Volume : {latest['volume']}"
        )

    else:

        print("❌ No latest price found")

    print("\n==========================================")
    print("DATA SERVICE TEST COMPLETE")
    print("==========================================\n")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()