"""
Financial Data Service
======================

Week 3 Data Engineering Layer

Purpose:
    Provide clean financial data to the Logic Engineering layer.

The Logic Engineer should use:

    get_financial_data("INFY")

instead of accessing SQLite directly.

This service does NOT:
    - fetch data from yfinance
    - calculate financial scores
    - make trading decisions

It only reads standardized financial data from the database.
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
# FINANCIAL DATA COLUMNS
# ============================================================

FINANCIAL_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "industry",
    "quarter",
    "revenue",
    "net_profit",
    "eps",
    "roe",
    "roce",
    "debt_equity",
    "operating_margin",
    "net_margin",
]


# ============================================================
# GET FINANCIAL DATA
# ============================================================

def get_financial_data(symbol):
    """
    Return quarterly financial data for one stock.

    Parameters
    ----------
    symbol : str
        NSE symbol without .NS.

    Returns
    -------
    pandas.DataFrame

        Standardized financial records ordered
        from oldest to newest quarter.

    Returns an empty DataFrame if the symbol
    does not exist or has no financial records.
    """

    symbol = symbol.upper().strip()

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    query = """
        SELECT
            companies.symbol,
            companies.company_name,
            companies.sector,
            companies.industry,

            quarterly_results.quarter,
            quarterly_results.revenue,
            quarterly_results.net_profit,
            quarterly_results.eps,
            quarterly_results.roe,
            quarterly_results.roce,
            quarterly_results.debt_equity,
            quarterly_results.operating_margin,
            quarterly_results.net_margin

        FROM quarterly_results

        INNER JOIN companies
            ON companies.id =
               quarterly_results.company_id

        WHERE companies.symbol = ?

        ORDER BY quarterly_results.quarter ASC
    """

    try:

        data = pd.read_sql_query(
            query,
            connection,
            params=(symbol,)
        )

    finally:

        connection.close()

    # --------------------------------------------------------
    # Ensure consistent columns
    # --------------------------------------------------------

    for column in FINANCIAL_COLUMNS:

        if column not in data.columns:

            data[column] = None

    data = data[
        FINANCIAL_COLUMNS
    ]

    return data


# ============================================================
# GET LATEST FINANCIAL DATA
# ============================================================

def get_latest_financial_data(symbol):
    """
    Return the most recent available financial
    record for a stock.

    Returns None when no financial record exists.
    """

    data = get_financial_data(
        symbol
    )

    if data.empty:

        return None

    return data.iloc[-1].to_dict()


# ============================================================
# GET AVAILABLE FINANCIAL STOCKS
# ============================================================

def get_financial_stocks():
    """
    Return stocks that currently have financial
    records in the database.
    """

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    query = """
        SELECT DISTINCT
            companies.symbol
        FROM quarterly_results

        INNER JOIN companies
            ON companies.id =
               quarterly_results.company_id

        ORDER BY companies.symbol
    """

    try:

        data = pd.read_sql_query(
            query,
            connection
        )

    finally:

        connection.close()

    return data["symbol"].tolist()


# ============================================================
# FINANCIAL RECORD COUNT
# ============================================================

def get_financial_record_count(symbol):
    """
    Return the number of financial records
    available for a stock.
    """

    data = get_financial_data(
        symbol
    )

    return len(data)


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "FINANCIAL DATA SERVICE TEST"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # Test available stocks
    # --------------------------------------------------------

    stocks = get_financial_stocks()

    print(
        f"\nStocks with financial data: "
        f"{len(stocks)}"
    )

    print(
        stocks
    )

    # --------------------------------------------------------
    # Test INFY
    # --------------------------------------------------------

    symbol = "INFY"

    print(
        "\n------------------------------------------"
    )

    print(
        f"TEST: get_financial_data('{symbol}')"
    )

    print(
        "------------------------------------------"
    )

    data = get_financial_data(
        symbol
    )

    if data.empty:

        print(
            f"❌ No financial data found for "
            f"{symbol}"
        )

        return

    print(
        f"✓ Records returned: {len(data)}"
    )

    print(
        f"✓ Columns: "
        f"{data.columns.tolist()}"
    )

    print(
        "\nFinancial records:"
    )

    print(
        data.to_string(index=False)
    )

    # --------------------------------------------------------
    # Latest record
    # --------------------------------------------------------

    latest = get_latest_financial_data(
        symbol
    )

    print(
        "\n------------------------------------------"
    )

    print(
        "TEST: Latest Financial Record"
    )

    print(
        "------------------------------------------"
    )

    if latest:

        for key, value in latest.items():

            print(
                f"{key:<20}: {value}"
            )

    # --------------------------------------------------------
    # Record count
    # --------------------------------------------------------

    count = get_financial_record_count(
        symbol
    )

    print(
        "\n------------------------------------------"
    )

    print(
        "TEST: Record Count"
    )

    print(
        "------------------------------------------"
    )

    print(
        f"{symbol} financial records: {count}"
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL DATA SERVICE TEST COMPLETE"
    )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()