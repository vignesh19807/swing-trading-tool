"""
Financial Data Normalizer
=========================

Week 4 - Tuesday

Purpose
-------
Normalize financial data before it is consumed by the
Financial Data Service / Logic Engineer.

Normalization includes:

    - Symbol normalization
    - Company name normalization
    - Reporting-period normalization
    - Numeric conversion
    - Percentage normalization
    - NULL handling
    - Duplicate company/quarter detection

Important
---------
This module does NOT modify the SQLite database.

NULL values are preserved as NULL/NaN.

NULL does NOT mean zero.
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
# FINANCIAL COLUMNS
# ============================================================

NUMERIC_COLUMNS = [
    "revenue",
    "net_profit",
    "eps",
    "roe",
    "roce",
    "debt_equity",
    "operating_margin",
    "net_margin",
]


# These fields represent percentages.
#
# ROE from some providers may appear as:
#
#     0.32
#
# meaning:
#
#     32%
#
# Other fields may already appear as:
#
#     21.17
#
# meaning:
#
#     21.17%
#
# The normalizer converts ratio-style percentage values
# between -1 and 1 into percentage points.
#
# Example:
#
#     0.32  -> 32.0
#     0.138 -> 13.8
#
# Values already expressed as percentage points are kept.
PERCENTAGE_COLUMNS = [
    "roe",
    "roce",
    "operating_margin",
    "net_margin",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_financial_data():
    """
    Load all financial records from SQLite.
    """

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

        ORDER BY
            companies.symbol,
            quarterly_results.quarter
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
# NORMALIZE SYMBOL
# ============================================================

def normalize_symbol(symbol):
    """
    Normalize stock symbols.

    Example:

        ' infy ' -> 'INFY'
    """

    if pd.isna(symbol):

        return None

    return str(
        symbol
    ).strip().upper()


# ============================================================
# NORMALIZE COMPANY NAME
# ============================================================

def normalize_company_name(name):
    """
    Normalize company names by removing unnecessary
    leading/trailing whitespace.
    """

    if pd.isna(name):

        return None

    return (
        str(name)
        .strip()
    )


# ============================================================
# NORMALIZE REPORTING PERIOD
# ============================================================

def normalize_quarter(value):
    """
    Normalize reporting period into YYYY-MM-DD.

    Example:

        2026-06-30
        2026-06-30 00:00:00

    both become:

        2026-06-30
    """

    if pd.isna(value):

        return pd.NaT

    converted = pd.to_datetime(
        value,
        errors="coerce"
    )

    if pd.isna(converted):

        return pd.NaT

    return converted.normalize()


# ============================================================
# NORMALIZE NUMERIC VALUES
# ============================================================

def normalize_numeric_columns(data):
    """
    Convert financial numeric columns to numeric values.

    Invalid numeric values become NaN.

    Existing NULL values remain missing.
    """

    for column in NUMERIC_COLUMNS:

        if column not in data.columns:

            continue

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    return data


# ============================================================
# NORMALIZE PERCENTAGES
# ============================================================

def normalize_percentage_columns(data):
    """
    Normalize percentage fields according to their
    known source representation.


    Current provider conventions:


        ROE
            Source may return a decimal ratio.
            Example:
                0.32 -> 32.0%


        ROCE
            Already represented as percentage points.
            Example:
                4.43 -> 4.43%


        Operating Margin
            Already represented as percentage points.


        Net Margin
            Already represented as percentage points.


    IMPORTANT:
        Debt/Equity is NOT a percentage and is therefore
        intentionally excluded.


    Missing values remain missing.
    """


    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------


    if "roe" in data.columns:


        def normalize_roe(value):


            if pd.isna(value):
                return value


            value = float(value)


            # Current provider returns ROE as a ratio
            # for example:
            #
            # 0.32 -> 32%
            #
            if -1 <= value <= 1:
                return value * 100


            # If already expressed as percentage points,
            # keep it unchanged.
            return value


        data["roe"] = (
            data["roe"]
            .apply(normalize_roe)
        )


    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------


    if "roce" in data.columns:


        data["roce"] = pd.to_numeric(
            data["roce"],
            errors="coerce"
        )


    # --------------------------------------------------------
    # Operating Margin
    # --------------------------------------------------------


    if "operating_margin" in data.columns:


        data["operating_margin"] = pd.to_numeric(
            data["operating_margin"],
            errors="coerce"
        )


    # --------------------------------------------------------
    # Net Margin
    # --------------------------------------------------------


    if "net_margin" in data.columns:


        data["net_margin"] = pd.to_numeric(
            data["net_margin"],
            errors="coerce"
        )


    return data



# ============================================================
# NORMALIZE NULL VALUES
# ============================================================

def normalize_null_values(data):
    """
    Standardize missing values.

    Empty strings and common textual NULL values become NaN.

    IMPORTANT:
        Missing values are NOT converted to zero.
    """

    null_values = [
        "",
        " ",
        "NA",
        "N/A",
        "NULL",
        "null",
        "None",
        "none",
        "-",
    ]

    data = data.replace(
        null_values,
        pd.NA
    )

    return data


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_records(data):
    """
    Remove duplicate company + reporting-period records.

    The first occurrence is preserved.

    The database already enforces:

        UNIQUE(company_id, quarter)

    so duplicates here should normally be zero.

    This is an additional protection at the data
    normalization layer.
    """

    before = len(data)

    data = data.drop_duplicates(
        subset=[
            "symbol",
            "quarter",
        ],
        keep="first"
    )

    removed = (
        before - len(data)
    )

    return data, removed


# ============================================================
# NORMALIZE FINANCIAL DATA
# ============================================================

def normalize_financial_data(data):
    """
    Run the complete normalization pipeline.

    Returns
    -------
    pandas.DataFrame
        Cleaned and normalized data.
    """

    if data is None:

        return pd.DataFrame()

    data = data.copy()

    # --------------------------------------------------------
    # NULL normalization FIRST
    # --------------------------------------------------------

    data = normalize_null_values(
        data
    )

    # --------------------------------------------------------
    # Symbols
    # --------------------------------------------------------

    if "symbol" in data.columns:

        data["symbol"] = (
            data["symbol"]
            .apply(normalize_symbol)
        )

    # --------------------------------------------------------
    # Company names
    # --------------------------------------------------------

    if "company_name" in data.columns:

        data["company_name"] = (
            data["company_name"]
            .apply(normalize_company_name)
        )

    # --------------------------------------------------------
    # Reporting period
    # --------------------------------------------------------

    if "quarter" in data.columns:

        data["quarter"] = (
            data["quarter"]
            .apply(normalize_quarter)
        )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    data = normalize_numeric_columns(
        data
    )

    # --------------------------------------------------------
    # Percentage fields
    # --------------------------------------------------------

    data = normalize_percentage_columns(
        data
    )

    # --------------------------------------------------------
    # Remove duplicate company/quarter records
    # --------------------------------------------------------

    data, removed = (
        remove_duplicate_records(
            data
        )
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    if (
        "symbol" in data.columns
        and "quarter" in data.columns
    ):

        data = data.sort_values(
            [
                "symbol",
                "quarter",
            ]
        )

    data = data.reset_index(
        drop=True
    )

    return data


# ============================================================
# NORMALIZATION REPORT
# ============================================================

def print_normalization_report(
    original,
    normalized
):
    """
    Print a summary comparing original and normalized data.
    """

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL DATA NORMALIZATION REPORT"
    )

    print(
        "=========================================="
    )

    print(
        f"Original records   : {len(original)}"
    )

    print(
        f"Normalized records : {len(normalized)}"
    )

    print(
        f"Records removed    : "
        f"{len(original) - len(normalized)}"
    )

    # --------------------------------------------------------
    # Symbol check
    # --------------------------------------------------------

    if "symbol" in normalized.columns:

        invalid_symbols = normalized[
            normalized["symbol"].isna()
        ]

        if invalid_symbols.empty:

            print(
                "✓ Symbol normalization passed"
            )

        else:

            print(
                f"⚠ Missing symbols: "
                f"{len(invalid_symbols)}"
            )

    # --------------------------------------------------------
    # Quarter check
    # --------------------------------------------------------

    if "quarter" in normalized.columns:

        invalid_quarters = normalized[
            normalized["quarter"].isna()
        ]

        if invalid_quarters.empty:

            print(
                "✓ Reporting-period normalization passed"
            )

        else:

            print(
                f"⚠ Invalid periods: "
                f"{len(invalid_quarters)}"
            )

    # --------------------------------------------------------
    # Duplicate check
    # --------------------------------------------------------

    duplicates = (
        normalized
        .duplicated(
            subset=[
                "symbol",
                "quarter",
            ]
        )
        .sum()
    )

    if duplicates == 0:

        print(
            "✓ No duplicate company/quarter records"
        )

    else:

        print(
            f"⚠ Duplicate records remaining: "
            f"{duplicates}"
        )

    # --------------------------------------------------------
    # NULL summary
    # --------------------------------------------------------

    print(
        "\nMissing values after normalization:"
    )

    for column in NUMERIC_COLUMNS:

        if column not in normalized.columns:

            continue

        missing = (
            normalized[column]
            .isna()
            .sum()
        )

        print(
            f"  {column:<20} {missing}"
        )

    # --------------------------------------------------------
    # Percentage sample
    # --------------------------------------------------------

    print(
        "\nNormalized percentage sample:"
    )

    for column in PERCENTAGE_COLUMNS:

        if column not in normalized.columns:

            continue

        values = (
            normalized[column]
            .dropna()
            .head(5)
            .tolist()
        )

        print(
            f"  {column:<20} {values}"
        )

    print(
        "\n=========================================="
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "WEEK 4 - FINANCIAL NORMALIZATION"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    data = load_financial_data()

    if data.empty:

        print(
            "❌ No financial data found."
        )

        return

    print(
        f"\nRecords loaded: {len(data)}"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    normalized = (
        normalize_financial_data(
            data
        )
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print_normalization_report(
        data,
        normalized
    )

    # --------------------------------------------------------
    # Show sample
    # --------------------------------------------------------

    print(
        "\nFirst 10 normalized records:"
    )

    print(
        normalized[
            [
                "symbol",
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
        ].head(10).to_string(
            index=False
        )
    )

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL NORMALIZATION COMPLETE"
    )

    print(
        "Database was NOT modified."
    )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()