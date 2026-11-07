"""
Week 7 - Sector / Industry Classification Service

Purpose:
    Provide a clean interface for sector and industry
    classification data to the Logic Engineering layer.

The Logic Engineer should use this service instead of
accessing the SQLite classification tables directly.

This service does NOT:
    - calculate sector scores
    - calculate industry scores
    - rank stocks
    - make trading decisions
    - modify database records
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd

# ============================================================
# PROJECT PATHS & DATABASE ACCESS LAYER
# ============================================================

from backend.config import DATABASE_PATH, PROJECT_ROOT
from backend.database.connection import get_db_connection, DatabaseEngine


# ============================================================
# COMPANY CLASSIFICATION
# ============================================================

CLASSIFICATION_COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "industry",
]


def get_company_classification(symbol):
    """
    Return sector and industry classification for one stock.

    Parameters
    ----------
    symbol : str
        NSE symbol without .NS.

    Returns
    -------
    dict or None
        Company classification.

    Returns None when the symbol does not exist.
    """

    symbol = symbol.upper().strip()

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

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, (symbol,))
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "symbol": row["symbol"] if "symbol" in row else row[0],
        "company_name": row["company_name"] if "company_name" in row else row[1],
        "sector": row["sector"] if "sector" in row else row[2],
        "industry": row["industry"] if "industry" in row else row[3],
    }


# ============================================================
# GET STOCKS BY SECTOR
# ============================================================

def get_sector_stocks(sector):
    """
    Return all stocks belonging to a sector.

    Parameters
    ----------
    sector : str
        Sector name.

    Returns
    -------
    list[str]
        Sorted stock symbols.
    """

    sector = sector.strip()

    query = """
        SELECT
            c.symbol
        FROM companies c

        INNER JOIN sectors s
            ON c.sector_id = s.id

        WHERE s.name = ?

        ORDER BY c.symbol
    """

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, (sector,))
        rows = cur.fetchall()

    return [
        row["symbol"] if "symbol" in row else row[0]
        for row in rows
    ]


# ============================================================
# GET STOCKS BY INDUSTRY
# ============================================================

def get_industry_stocks(industry):
    """
    Return all stocks belonging to an industry.

    Parameters
    ----------
    industry : str
        Industry name.

    Returns
    -------
    list[str]
        Sorted stock symbols.

    Note:
        Industry names are resolved through the industry
        master table. An industry can exist under more
        than one sector in the current universe.
    """

    industry = industry.strip()

    query = """
        SELECT DISTINCT
            c.symbol
        FROM companies c

        INNER JOIN industries i
            ON c.industry_id = i.id

        WHERE i.name = ?

        ORDER BY c.symbol
    """

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query, (industry,))
        rows = cur.fetchall()

    return [
        row["symbol"] if "symbol" in row else row[0]
        for row in rows
    ]


# ============================================================
# GET ALL CLASSIFICATIONS
# ============================================================

def get_all_classifications():
    """
    Return the complete company classification mapping.

    Returns
    -------
    pandas.DataFrame
        One row per company.
    """

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        if connection.engine == DatabaseEngine.POSTGRESQL:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'companies'"
            )
            cols = {r["column_name"] for r in cur.fetchall()}
            where_clause = "WHERE (c.is_active = TRUE OR c.is_active IS NULL)" if "is_active" in cols else ""
        else:
            cur.execute("PRAGMA table_info(companies)")
            cols = {r[1] for r in cur.fetchall()}
            where_clause = "WHERE (c.is_active = 1 OR c.is_active IS NULL)" if "is_active" in cols else ""

        query = f"""
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

            {where_clause}

            ORDER BY c.symbol
        """
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=CLASSIFICATION_COLUMNS)

    data = pd.DataFrame([dict(r) for r in rows])
    for column in CLASSIFICATION_COLUMNS:
        if column not in data.columns:
            data[column] = None

    return data[CLASSIFICATION_COLUMNS]


# ============================================================
# GET SECTORS
# ============================================================

def get_sectors():
    """
    Return all available sectors.
    """

    query = """
        SELECT
            name
        FROM sectors
        ORDER BY name
    """

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query)
        rows = cur.fetchall()

    return [
        row["name"] if "name" in row else row[0]
        for row in rows
    ]


# ============================================================
# GET INDUSTRIES
# ============================================================

def get_industries():
    """
    Return all available industry-sector mappings.

    Returns
    -------
    pandas.DataFrame
        Columns:
            industry
            sector
    """

    query = """
        SELECT
            i.name AS industry,
            s.name AS sector
        FROM industries i

        INNER JOIN sectors s
            ON i.sector_id = s.id

        ORDER BY
            i.name,
            s.name
    """

    with get_db_connection(DATABASE_PATH) as connection:
        cur = connection.cursor()
        cur.execute(query)
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=["industry", "sector"])

    return pd.DataFrame([dict(r) for r in rows])


# ============================================================
# GET SECTOR STOCK COUNT
# ============================================================

def get_sector_stock_count(sector):
    """
    Return number of stocks in a sector.
    """

    return len(
        get_sector_stocks(
            sector
        )
    )


# ============================================================
# GET INDUSTRY STOCK COUNT
# ============================================================

def get_industry_stock_count(industry):
    """
    Return number of stocks in an industry.
    """

    return len(
        get_industry_stocks(
            industry
        )
    )


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print("=" * 60)

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "WEEK 7 - CLASSIFICATION SERVICE TEST"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # Test company classification
    # --------------------------------------------------------

    symbol = "INFY"

    print(
        "\n------------------------------------------"
    )

    print(
        f"TEST: get_company_classification('{symbol}')"
    )

    print(
        "------------------------------------------"
    )

    classification = (
        get_company_classification(
            symbol
        )
    )

    if classification is None:

        print(
            f"❌ No classification found for {symbol}"
        )

    else:

        print(
            "✓ Classification found"
        )

        for key, value in classification.items():

            print(
                f"{key:<15}: {value}"
            )

    # --------------------------------------------------------
    # Test sector
    # --------------------------------------------------------

    sector = "Information Technology"

    print(
        "\n------------------------------------------"
    )

    print(
        f"TEST: get_sector_stocks('{sector}')"
    )

    print(
        "------------------------------------------"
    )

    stocks = get_sector_stocks(
        sector
    )

    print(
        f"✓ Stocks found: {len(stocks)}"
    )

    print(
        stocks
    )

    # --------------------------------------------------------
    # Test industry
    # --------------------------------------------------------

    industry = "IT Services"

    print(
        "\n------------------------------------------"
    )

    print(
        f"TEST: get_industry_stocks('{industry}')"
    )

    print(
        "------------------------------------------"
    )

    stocks = get_industry_stocks(
        industry
    )

    print(
        f"✓ Stocks found: {len(stocks)}"
    )

    print(
        stocks
    )

    # --------------------------------------------------------
    # Test all classifications
    # --------------------------------------------------------

    print(
        "\n------------------------------------------"
    )

    print(
        "TEST: get_all_classifications()"
    )

    print(
        "------------------------------------------"
    )

    data = get_all_classifications()

    print(
        f"✓ Companies returned: {len(data)}"
    )

    print(
        f"✓ Columns: {data.columns.tolist()}"
    )

    # --------------------------------------------------------
    # Test sectors
    # --------------------------------------------------------

    sectors = get_sectors()

    print(
        "\n------------------------------------------"
    )

    print(
        "TEST: get_sectors()"
    )

    print(
        "------------------------------------------"
    )

    print(
        f"✓ Sectors returned: {len(sectors)}"
    )

    print(
        sectors
    )

    # --------------------------------------------------------
    # Test industries
    # --------------------------------------------------------

    industries = get_industries()

    print(
        "\n------------------------------------------"
    )

    print(
        "TEST: get_industries()"
    )

    print(
        "------------------------------------------"
    )

    print(
        f"✓ Industry mappings returned: "
        f"{len(industries)}"
    )

    print(
        industries.to_string(index=False)
    )

    # --------------------------------------------------------
    # Invalid stock test
    # --------------------------------------------------------

    print(
        "\n------------------------------------------"
    )

    print(
        "TEST: Invalid Symbol"
    )

    print(
        "------------------------------------------"
    )

    invalid = get_company_classification(
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

    print(
        "\n=========================================="
    )

    print(
        "CLASSIFICATION SERVICE TEST COMPLETE"
    )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()