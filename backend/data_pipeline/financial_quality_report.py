"""
Financial Data Quality Report
=============================

Week 4 - Monday

Purpose:
    Analyze financial-data completeness for the full
    50-stock universe.

Checks:
    - Number of financial records per stock
    - Reporting periods
    - Revenue availability
    - Net profit availability
    - EPS availability
    - ROE availability
    - ROCE availability
    - Debt/Equity availability
    - Operating Margin availability
    - Net Margin availability

This module only reports data quality.
It does not modify the database.
"""

import sqlite3
from pathlib import Path

import pandas as pd

from backend.data_pipeline.stock_universe import (
    STOCK_UNIVERSE,
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

REPORTS_DIR = PROJECT_ROOT / "reports"

REPORTS_DIR.mkdir(
    exist_ok=True
)

REPORT_PATH = (
    REPORTS_DIR
    / "financial_quality_report.csv"
)


# ============================================================
# FINANCIAL FIELDS
# ============================================================

FINANCIAL_FIELDS = [
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
# GET STOCK SYMBOLS
# ============================================================

def get_stock_symbols():
    """
    Return all symbols from the 50-stock universe.
    """

    symbols = []

    for stock in STOCK_UNIVERSE:

        if isinstance(stock, dict):

            symbol = stock.get("symbol")

        else:

            symbol = str(stock)

        if symbol:

            symbols.append(
                symbol.upper().strip()
            )

    return symbols


# ============================================================
# LOAD FINANCIAL DATA
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
# BUILD QUALITY REPORT
# ============================================================

def build_quality_report(
    data,
    symbols
):
    """
    Build one completeness row for each stock.
    """

    rows = []

    for symbol in symbols:

        stock_data = data[
            data["symbol"] == symbol
        ]

        record_count = len(
            stock_data
        )

        row = {
            "symbol": symbol,
            "records": record_count,
        }

        # ----------------------------------------------------
        # Reporting periods
        # ----------------------------------------------------

        if record_count > 0:

            row["first_period"] = (
                stock_data["quarter"]
                .min()
            )

            row["latest_period"] = (
                stock_data["quarter"]
                .max()
            )

        else:

            row["first_period"] = None
            row["latest_period"] = None

        # ----------------------------------------------------
        # Financial field completeness
        # ----------------------------------------------------

        for field in FINANCIAL_FIELDS:

            if record_count == 0:

                available = 0
                missing = 0
                percentage = 0.0

            else:

                available = (
                    stock_data[field]
                    .notna()
                    .sum()
                )

                missing = (
                    stock_data[field]
                    .isna()
                    .sum()
                )

                percentage = (
                    available
                    / record_count
                    * 100
                )

            row[
                f"{field}_available"
            ] = int(available)

            row[
                f"{field}_missing"
            ] = int(missing)

            row[
                f"{field}_availability_pct"
            ] = round(
                percentage,
                2
            )

        rows.append(row)

    return pd.DataFrame(
        rows
    )


# ============================================================
# PRINT REPORT
# ============================================================

def print_report(
    report
):
    """
    Print a readable summary to the terminal.
    """

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL DATA QUALITY REPORT"
    )

    print(
        "=========================================="
    )

    print(
        f"Stocks analyzed : {len(report)}"
    )

    print(
        "\nStock completeness:"
    )

    print(
        "------------------------------------------"
    )

    header = (
        f"{'Symbol':<12}"
        f"{'Records':>8}"
        f"{'Revenue':>10}"
        f"{'Profit':>10}"
        f"{'EPS':>10}"
        f"{'ROE':>10}"
        f"{'ROCE':>10}"
        f"{'D/E':>10}"
    )

    print(header)

    print(
        "-" * len(header)
    )

    for _, row in report.iterrows():

        print(
            f"{row['symbol']:<12}"
            f"{row['records']:>8}"
            f"{row['revenue_availability_pct']:>9.1f}%"
            f"{row['net_profit_availability_pct']:>9.1f}%"
            f"{row['eps_availability_pct']:>9.1f}%"
            f"{row['roe_availability_pct']:>9.1f}%"
            f"{row['roce_availability_pct']:>9.1f}%"
            f"{row['debt_equity_availability_pct']:>9.1f}%"
        )

    # ========================================================
    # FIELD SUMMARY
    # ========================================================

    print(
        "\n------------------------------------------"
    )

    print(
        "OVERALL FIELD AVAILABILITY"
    )

    print(
        "------------------------------------------"
    )

    total_records = report[
        "records"
    ].sum()

    for field in FINANCIAL_FIELDS:

        available = report[
            f"{field}_available"
        ].sum()

        missing = report[
            f"{field}_missing"
        ].sum()

        if total_records > 0:

            percentage = (
                available
                / total_records
                * 100
            )

        else:

            percentage = 0

        print(
            f"{field:<20}"
            f"Available: {available:<5}"
            f"Missing: {missing:<5}"
            f"Coverage: {percentage:.2f}%"
        )

    # ========================================================
    # PERIOD SUMMARY
    # ========================================================

    print(
        "\n------------------------------------------"
    )

    print(
        "REPORTING PERIOD SUMMARY"
    )

    print(
        "------------------------------------------"
    )

    if not report.empty:

        first_period = (
            report["first_period"]
            .dropna()
            .min()
        )

        latest_period = (
            report["latest_period"]
            .dropna()
            .max()
        )

        print(
            f"Oldest period : {first_period}"
        )

        print(
            f"Latest period : {latest_period}"
        )

    # ========================================================
    # STOCKS WITHOUT DATA
    # ========================================================

    no_data = report[
        report["records"] == 0
    ]

    print(
        "\n------------------------------------------"
    )

    print(
        "STOCKS WITHOUT FINANCIAL DATA"
    )

    print(
        "------------------------------------------"
    )

    if no_data.empty:

        print(
            "✓ All stocks have financial records"
        )

    else:

        for symbol in no_data[
            "symbol"
        ]:

            print(
                f"⚠ {symbol}"
            )

    print(
        "\n=========================================="
    )


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    report
):
    """
    Save the quality report as CSV.
    """

    report.to_csv(
        REPORT_PATH,
        index=False
    )

    print(
        f"\n✓ Report saved:"
    )

    print(
        f"  {REPORT_PATH}"
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
        "WEEK 4 - FINANCIAL COMPLETENESS"
    )

    print(
        "=========================================="
    )

    symbols = get_stock_symbols()

    print(
        f"\nStock universe: {len(symbols)} stocks"
    )

    if len(symbols) != 50:

        print(
            "⚠ WARNING: Expected 50 stocks"
        )

    data = load_financial_data()

    print(
        f"Financial records loaded: "
        f"{len(data)}"
    )

    if data.empty:

        print(
            "❌ No financial data found."
        )

        return

    report = build_quality_report(
        data,
        symbols
    )

    print_report(
        report
    )

    save_report(
        report
    )

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL COMPLETENESS CHECK COMPLETE"
    )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()