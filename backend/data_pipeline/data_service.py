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
from typing import Optional, Dict, Any, List

import pandas as pd

# ============================================================
# PROJECT PATHS & DATABASE ACCESS LAYER
# ============================================================

from backend.config import DATABASE_PATH, PROJECT_ROOT
from backend.database.connection import get_db_connection, open_db_connection, ConnectionWrapper


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection() -> ConnectionWrapper:
    """
    Create a connection using the centralized Database Access Layer (DAL).
    Supports both SQLite and PostgreSQL backends transparently.
    """
    return open_db_connection(DATABASE_PATH)


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

    if start_date is not None:
        query += " AND dp.date >= ?"
        parameters.append(start_date)

    if end_date is not None:
        end_date_str = str(end_date).strip()
        if len(end_date_str) == 10:
            end_date_str = f"{end_date_str}T23:59:59+05:30"
        query += " AND dp.date <= ?"
        parameters.append(end_date_str)

    query += " ORDER BY dp.date ASC"

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, parameters)
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    data = pd.DataFrame([dict(r) for r in rows])
    data["date"] = pd.to_datetime(data["date"])
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
        query += " AND dp.date >= ?"
        parameters.append(start_date)

    if end_date is not None:
        end_date_str = str(end_date).strip()
        if len(end_date_str) == 10:
            end_date_str = f"{end_date_str}T23:59:59+05:30"
        query += " AND dp.date <= ?"
        parameters.append(end_date_str)

    query += " ORDER BY dp.date ASC"

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, parameters)
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "adjusted_close"])

    data = pd.DataFrame([dict(r) for r in rows])
    data["date"] = pd.to_datetime(data["date"])
    return data


# ============================================================
# GET LATEST PRICE
# ============================================================

def get_latest_price(symbol, evaluation_date=None):
    """
    Return the latest available price record
    for a stock, optionally up to an evaluation_date.
    """

    symbol = symbol.upper().strip()

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

    if evaluation_date is not None:
        eval_date_str = str(evaluation_date).strip()
        if len(eval_date_str) == 10:
            eval_date_str = f"{eval_date_str}T23:59:59+05:30"
        query += " AND dp.date <= ?"
        parameters.append(eval_date_str)

    query += " ORDER BY dp.date DESC LIMIT 1"

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, parameters)
        row = cur.fetchone()

    if not row:
        return None

    res = dict(row)
    res["date"] = pd.to_datetime(res["date"])
    return res


# ============================================================
# GET AVAILABLE STOCKS
# ============================================================

def get_available_stocks():
    """
    Return all stock symbols currently available
    in the database.
    """

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
    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=["symbol", "company_name", "sector", "industry", "exchange"])

    return pd.DataFrame([dict(r) for r in rows])


# ============================================================
# GET RECORD COUNT
# ============================================================

def get_stock_record_count(symbol):
    """
    Return the number of daily price records
    available for a stock.
    """

    symbol = symbol.upper().strip()

    query = """
        SELECT COUNT(*) as cnt
        FROM daily_prices AS dp
        INNER JOIN companies AS c
            ON dp.company_id = c.id
        WHERE c.symbol = ?
    """
    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, (symbol,))
        row = cur.fetchone()

    if not row:
        return 0
    return row["cnt"] if "cnt" in row else row[0]


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