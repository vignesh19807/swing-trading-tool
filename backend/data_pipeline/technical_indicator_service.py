"""
Week 8 - Technical Indicator Persistence Service

Purpose:
    Connect the validated Technical Engine to the SQLite database.

Flow:
    Daily OHLCV data
        ↓
    Data Service
        ↓
    Technical Engine
        ↓
    Technical Indicator Persistence
        ↓
    technical_indicators table

This service does NOT:
    - make trading decisions
    - calculate financial scores
    - generate buy/sell signals
    - modify the Technical Engine
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import run_technical_pipeline

# ============================================================
# PROJECT PATHS & DATABASE ACCESS LAYER
# ============================================================

from backend.config import DATABASE_PATH, PROJECT_ROOT
from backend.database.connection import get_db_connection, open_db_connection


# ============================================================
# INDICATOR COLUMNS
# ============================================================

INDICATOR_COLUMNS = [
    "rsi",
    "macd",
    "signal",
    "ema20",
    "ema50",
    "ema200",
    "histogram",
    "atr14",
    "technical_score",
]


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_company_id(connection, symbol):
    """
    Return company_id for a stock symbol.

    Returns None when the symbol does not exist.
    """

    row = connection.execute(
        """
        SELECT id
        FROM companies
        WHERE symbol = ?
        """,
        (symbol.upper().strip(),),
    ).fetchone()

    if row is None:
        return None

    return row["id"] if "id" in row else row[0]


# ============================================================
# SAVE TECHNICAL INDICATORS
# ============================================================

def save_technical_indicators(symbol):
    """
    Calculate and persist technical indicators for one stock.

    Existing records for the same company/date are updated.

    Returns
    -------
    int
        Number of records processed.
    """

    symbol = symbol.upper().strip()

    with get_db_connection(DATABASE_PATH) as connection:
        company_id = get_company_id(
            connection,
            symbol,
        )

        if company_id is None:
            print(
                f"⚠ {symbol}: company not found"
            )
            return 0

        # ----------------------------------------------------
        # Load OHLCV data
        # ----------------------------------------------------

        market_data = get_stock_data(
            symbol
        )

        if market_data.empty:
            print(
                f"⚠ {symbol}: no market data"
            )
            return 0

        # ----------------------------------------------------
        # Calculate technical indicators
        # ----------------------------------------------------

        result = run_technical_pipeline(
            market_data
        )

        indicators = result["indicators"].copy()

        if indicators.empty:
            print(
                f"⚠ {symbol}: no technical indicators"
            )
            return 0

        # ----------------------------------------------------
        # Normalize date information
        # ----------------------------------------------------

        if "date" in market_data.columns:
            indicators["date"] = (
                market_data["date"]
                .values
            )
        else:
            indicators["date"] = (
                indicators.index
                .astype(str)
            )

        # ----------------------------------------------------
        # Save records
        # ----------------------------------------------------

        records = 0
        cur = connection.cursor()

        for _, row in indicators.iterrows():
            date = str(row["date"])[:10]

            values = (
                row.get("rsi"),
                row.get("macd"),
                row.get("signal"),
                row.get("ema20"),
                row.get("ema50"),
                row.get("ema200"),
                row.get("histogram"),
                row.get("atr14"),
                row.get("technical_score"),
            )

            cur.execute(
                """
                INSERT INTO technical_indicators (
                    company_id,
                    date,
                    rsi,
                    macd,
                    macd_signal,
                    ema_20,
                    ema_50,
                    ema_200,
                    macd_histogram,
                    atr_14,
                    technical_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(company_id, date)
                DO UPDATE SET
                    rsi = excluded.rsi,
                    macd = excluded.macd,
                    macd_signal = excluded.macd_signal,
                    ema_20 = excluded.ema_20,
                    ema_50 = excluded.ema_50,
                    ema_200 = excluded.ema_200,
                    macd_histogram = excluded.macd_histogram,
                    atr_14 = excluded.atr_14,
                    technical_score = excluded.technical_score
                """,
                (
                    company_id,
                    date,
                    *values,
                ),
            )

            records += 1

        connection.commit()
        return records


# ============================================================
# GET TECHNICAL DATA
# ============================================================

def get_technical_indicators(symbol):
    """
    Return persisted technical indicators for one stock.
    """

    symbol = symbol.upper().strip()

    query = """
        SELECT
            companies.symbol,
            technical_indicators.date,
            technical_indicators.rsi,
            technical_indicators.macd,
            technical_indicators.macd_signal,
            technical_indicators.ema_20,
            technical_indicators.ema_50,
            technical_indicators.ema_200,
            technical_indicators.macd_histogram,
            technical_indicators.atr_14,
            technical_indicators.technical_score

        FROM technical_indicators

        INNER JOIN companies
            ON companies.id =
               technical_indicators.company_id

        WHERE companies.symbol = ?

        ORDER BY technical_indicators.date ASC
    """

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, (symbol,))
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=[
            "symbol", "date", "rsi", "macd", "macd_signal",
            "ema_20", "ema_50", "ema_200", "macd_histogram",
            "atr_14", "technical_score"
        ])

    return pd.DataFrame([dict(r) for r in rows])


# ============================================================
# GET LATEST TECHNICAL DATA
# ============================================================

def get_latest_technical_indicators(symbol):
    """
    Return the latest persisted technical record.

    Returns None when no record exists.
    """

    data = get_technical_indicators(
        symbol
    )

    if data.empty:
        return None

    return data.iloc[-1].to_dict()


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - TECHNICAL INDICATOR PERSISTENCE")
    print("=" * 60)

    symbol = "INFY"

    print(
        f"\nProcessing {symbol}..."
    )

    records = save_technical_indicators(
        symbol
    )

    print(
        f"✓ Records processed: {records}"
    )

    data = get_technical_indicators(
        symbol
    )

    print(
        f"✓ Records stored: {len(data)}"
    )

    if not data.empty:

        print(
            "\nLatest technical record:"
        )

        print(
            data.tail(1).to_string(
                index=False
            )
        )

    latest = get_latest_technical_indicators(
        symbol
    )

    print(
        "\nLatest record available:",
        latest is not None,
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "TECHNICAL INDICATOR PERSISTENCE TEST COMPLETE"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()