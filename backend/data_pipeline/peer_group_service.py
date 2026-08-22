"""
Week 7 - Sector / Industry Peer Group Service

Purpose:
    Provide reusable sector and industry peer-group information
    to the Logic Engineering layer.

The Logic Engineer should use this service instead of accessing
SQLite classification tables directly.

This service does NOT:
    - calculate technical scores
    - calculate financial scores
    - rank stocks
    - make trading decisions
    - modify database records
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
# GET CONNECTION
# ============================================================

def get_connection():
    """
    Create a read-only database connection for peer-group queries.
    """

    return sqlite3.connect(
        DATABASE_PATH
    )


# ============================================================
# GET COMPANY CLASSIFICATION
# ============================================================

def get_company_classification(symbol):
    """
    Return the sector and industry of a stock.

    Parameters
    ----------
    symbol : str
        NSE symbol without .NS.

    Returns
    -------
    dict or None
    """

    symbol = symbol.upper().strip()

    connection = get_connection()

    query = """
        SELECT
            c.symbol,
            c.company_name,
            s.name AS sector,
            i.name AS industry
        FROM companies c

        LEFT JOIN sectors s
            ON c.sector_id = s.id

        LEFT JOIN industries i
            ON c.industry_id = i.id

        WHERE c.symbol = ?
    """

    try:

        row = connection.execute(
            query,
            (symbol,)
        ).fetchone()

    finally:

        connection.close()

    if row is None:
        return None

    return {
        "symbol": row[0],
        "company_name": row[1],
        "sector": row[2],
        "industry": row[3],
    }


# ============================================================
# SECTOR SUMMARY
# ============================================================

def get_sector_summary():
    """
    Return the number of companies in each sector.

    Returns
    -------
    pandas.DataFrame

        Columns:
            sector
            stock_count
    """

    connection = get_connection()

    query = """
        SELECT
            s.name AS sector,
            COUNT(c.id) AS stock_count
        FROM sectors s

        LEFT JOIN companies c
            ON c.sector_id = s.id

        GROUP BY
            s.id,
            s.name

        ORDER BY
            s.name
    """

    try:

        data = pd.read_sql_query(
            query,
            connection
        )

    finally:

        connection.close()

    return data


# ============================================================
# INDUSTRY SUMMARY
# ============================================================

def get_industry_summary():
    """
    Return the number of companies in each industry-sector
    mapping.

    Returns
    -------
    pandas.DataFrame

        Columns:
            industry
            sector
            stock_count
    """

    connection = get_connection()

    query = """
        SELECT
            i.name AS industry,
            s.name AS sector,
            COUNT(c.id) AS stock_count
        FROM industries i

        INNER JOIN sectors s
            ON i.sector_id = s.id

        LEFT JOIN companies c
            ON c.industry_id = i.id

        GROUP BY
            i.id,
            i.name,
            s.name

        ORDER BY
            i.name,
            s.name
    """

    try:

        data = pd.read_sql_query(
            query,
            connection
        )

    finally:

        connection.close()

    return data


# ============================================================
# GET SECTOR PEERS
# ============================================================

def get_sector_peers(symbol):
    """
    Return all stocks belonging to the same sector as symbol.

    The requested stock is included in the peer group.

    Parameters
    ----------
    symbol : str

    Returns
    -------
    list[str]

        Sorted stock symbols.

    Returns an empty list when the symbol does not exist.
    """

    classification = get_company_classification(
        symbol
    )

    if classification is None:
        return []

    sector = classification["sector"]

    connection = get_connection()

    query = """
        SELECT
            c.symbol
        FROM companies c

        INNER JOIN sectors s
            ON c.sector_id = s.id

        WHERE s.name = ?

        ORDER BY c.symbol
    """

    try:

        rows = connection.execute(
            query,
            (sector,)
        ).fetchall()

    finally:

        connection.close()

    return [
        row[0]
        for row in rows
    ]


# ============================================================
# GET INDUSTRY PEERS
# ============================================================

def get_industry_peers(symbol):
    """
    Return all stocks belonging to the same industry as symbol.

    The industry ID is used rather than only the industry name.
    This is important because an industry name can appear under
    different sectors in the current master data.

    The requested stock is included in the peer group.

    Parameters
    ----------
    symbol : str

    Returns
    -------
    list[str]

        Sorted stock symbols.

    Returns an empty list when the symbol does not exist.
    """

    symbol = symbol.upper().strip()

    connection = get_connection()

    query = """
        SELECT
            peer.symbol
        FROM companies target

        INNER JOIN companies peer
            ON peer.industry_id = target.industry_id

        WHERE target.symbol = ?

        ORDER BY peer.symbol
    """

    try:

        rows = connection.execute(
            query,
            (symbol,)
        ).fetchall()

    finally:

        connection.close()

    return [
        row[0]
        for row in rows
    ]


# ============================================================
# GET SECTOR PEER COUNT
# ============================================================

def get_sector_peer_count(symbol):
    """
    Return the number of stocks in the same sector.
    """

    return len(
        get_sector_peers(symbol)
    )


# ============================================================
# GET INDUSTRY PEER COUNT
# ============================================================

def get_industry_peer_count(symbol):
    """
    Return the number of stocks in the same industry.
    """

    return len(
        get_industry_peers(symbol)
    )


# ============================================================
# GET PEER INFORMATION
# ============================================================

def get_peer_group(symbol):
    """
    Return complete peer-group information for a stock.

    Returns
    -------
    dict or None
    """

    classification = get_company_classification(
        symbol
    )

    if classification is None:
        return None

    return {
        "symbol": classification["symbol"],
        "sector": classification["sector"],
        "industry": classification["industry"],
        "sector_peers": get_sector_peers(symbol),
        "industry_peers": get_industry_peers(symbol),
    }


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 7 - PEER GROUP SERVICE TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Test sector summary
    # --------------------------------------------------------

    print("\n" + "-" * 50)
    print("TEST 1 - SECTOR SUMMARY")
    print("-" * 50)

    sector_data = get_sector_summary()

    print(
        f"✓ Sectors returned: {len(sector_data)}"
    )

    print(
        sector_data.to_string(index=False)
    )

    # --------------------------------------------------------
    # Test industry summary
    # --------------------------------------------------------

    print("\n" + "-" * 50)
    print("TEST 2 - INDUSTRY SUMMARY")
    print("-" * 50)

    industry_data = get_industry_summary()

    print(
        f"✓ Industry mappings returned: "
        f"{len(industry_data)}"
    )

    print(
        industry_data.to_string(index=False)
    )

    # --------------------------------------------------------
    # Test sector peers
    # --------------------------------------------------------

    symbol = "INFY"

    print("\n" + "-" * 50)
    print(
        f"TEST 3 - SECTOR PEERS FOR {symbol}"
    )
    print("-" * 50)

    sector_peers = get_sector_peers(
        symbol
    )

    print(
        f"✓ Sector peers: {len(sector_peers)}"
    )

    print(
        sector_peers
    )

    # --------------------------------------------------------
    # Test industry peers
    # --------------------------------------------------------

    print("\n" + "-" * 50)
    print(
        f"TEST 4 - INDUSTRY PEERS FOR {symbol}"
    )
    print("-" * 50)

    industry_peers = get_industry_peers(
        symbol
    )

    print(
        f"✓ Industry peers: {len(industry_peers)}"
    )

    print(
        industry_peers
    )

    # --------------------------------------------------------
    # Test complete peer group
    # --------------------------------------------------------

    print("\n" + "-" * 50)
    print(
        f"TEST 5 - COMPLETE PEER GROUP FOR {symbol}"
    )
    print("-" * 50)

    peer_group = get_peer_group(
        symbol
    )

    if peer_group is None:

        print(
            "❌ Peer group not found"
        )

    else:

        print(
            f"✓ Symbol   : {peer_group['symbol']}"
        )

        print(
            f"✓ Sector   : {peer_group['sector']}"
        )

        print(
            f"✓ Industry : {peer_group['industry']}"
        )

        print(
            f"✓ Sector peers   : "
            f"{len(peer_group['sector_peers'])}"
        )

        print(
            f"✓ Industry peers : "
            f"{len(peer_group['industry_peers'])}"
        )

    # --------------------------------------------------------
    # Invalid symbol
    # --------------------------------------------------------

    print("\n" + "-" * 50)
    print("TEST 6 - INVALID SYMBOL")
    print("-" * 50)

    invalid = get_peer_group(
        "INVALID_SYMBOL"
    )

    if invalid is None:

        print(
            "✓ Invalid symbol handled safely"
        )

    else:

        print(
            "❌ Invalid symbol returned data"
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("PEER GROUP SERVICE TEST COMPLETE")
    print("=" * 60)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()