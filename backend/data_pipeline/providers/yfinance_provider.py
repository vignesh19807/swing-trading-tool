"""
Yahoo Finance Data Provider
============================

This module provides historical NSE market data using yfinance.

It is currently the working market-data provider for the project.
"""

import yfinance as yf
import pandas as pd


def fetch_stock_data(symbol, period="2y"):
    """
    Fetch historical daily market data for an NSE stock.

    Parameters
    ----------
    symbol : str
        NSE symbol without .NS, e.g. "INFY".

    period : str
        yfinance historical period. Default: "2y".

    Returns
    -------
    pandas.DataFrame or None

        Columns:
        date
        open
        high
        low
        close
        volume
        adjusted_close
    """

    symbol = symbol.upper().strip()

    # yfinance uses the .NS suffix for NSE stocks
    ticker_symbol = (
        symbol if symbol.endswith(".NS")
        else f"{symbol}.NS"
    )

    print(f"Downloading {ticker_symbol}...")

    ticker = yf.Ticker(ticker_symbol)

    data = ticker.history(
        period=period,
        interval="1d",
        auto_adjust=False
    )

    if data.empty:
        print(
            f"WARNING: No data received for "
            f"{ticker_symbol}"
        )
        return None

    # Convert index into a normal column
    data = data.reset_index()

    # Keep only fields required by the project
    data = data[
        [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Adj Close"
        ]
    ]

    # Standardize column names
    data.columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close"
    ]

    # Sort chronologically
    data = data.sort_values(
        "date"
    ).reset_index(drop=True)

    return data


def get_provider_name():
    """Return the provider name."""

    return "yfinance"