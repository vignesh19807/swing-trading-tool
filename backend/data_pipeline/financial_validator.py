"""
Financial Data Validator
========================

Week 3 Data Engineering Layer

Responsibilities:
    - Check required columns
    - Check missing financial values
    - Check duplicate company/period records
    - Check reporting periods
    - Check invalid numerical values
    - Flag suspicious values

This module does NOT calculate financial scores.
"""

import pandas as pd


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
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


# ============================================================
# NUMERICAL COLUMNS
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


# ============================================================
# VALIDATION RESULT
# ============================================================

def validate_financial_data(symbol, data):
    """
    Validate normalized financial data.

    Returns
    -------
    tuple
        (is_valid, report)
    """

    report = {
        "symbol": symbol,
        "records": 0,
        "missing_values": {},
        "duplicate_records": 0,
        "invalid_periods": 0,
        "invalid_values": {},
        "warnings": [],
        "errors": [],
    }

    # --------------------------------------------------------
    # DATA EXISTENCE
    # --------------------------------------------------------

    if data is None:

        report["errors"].append(
            "No financial data returned"
        )

        return False, report

    if data.empty:

        report["errors"].append(
            "Financial DataFrame is empty"
        )

        return False, report

    report["records"] = len(data)

    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:

        report["errors"].append(
            f"Missing columns: {missing_columns}"
        )

        return False, report

    # --------------------------------------------------------
    # REPORTING PERIOD
    # --------------------------------------------------------

    for index, period in data["quarter"].items():

        try:

            pd.to_datetime(
                period,
                errors="raise"
            )

        except Exception:

            report["invalid_periods"] += 1

            report["errors"].append(
                f"Invalid reporting period at row "
                f"{index}: {period}"
            )

    # --------------------------------------------------------
    # DUPLICATE COMPANY + PERIOD
    # --------------------------------------------------------

    duplicates = data.duplicated(
        subset=["symbol", "quarter"],
        keep=False
    )

    duplicate_count = int(
        duplicates.sum()
    )

    report["duplicate_records"] = (
        duplicate_count
    )

    if duplicate_count > 0:

        report["errors"].append(
            f"Duplicate company/period records: "
            f"{duplicate_count}"
        )

    # --------------------------------------------------------
    # MISSING VALUES
    # --------------------------------------------------------

    for column in NUMERIC_COLUMNS:

        missing_count = int(
            data[column].isna().sum()
        )

        report["missing_values"][column] = (
            missing_count
        )

        if missing_count > 0:

            report["warnings"].append(
                f"{column}: "
                f"{missing_count} missing value(s)"
            )

    # --------------------------------------------------------
    # NUMERICAL VALUE VALIDATION
    # --------------------------------------------------------

    for column in NUMERIC_COLUMNS:

        invalid_count = 0

        for value in data[column]:

            if pd.isna(value):
                continue

            try:

                number = float(value)

            except (TypeError, ValueError):

                invalid_count += 1
                continue

            if not pd.api.types.is_number(number):

                invalid_count += 1

        report["invalid_values"][column] = (
            invalid_count
        )

        if invalid_count > 0:

            report["errors"].append(
                f"{column}: "
                f"{invalid_count} invalid numerical value(s)"
            )

    # --------------------------------------------------------
    # BASIC SANITY CHECKS
    # --------------------------------------------------------

    # Revenue should not be negative
    if "revenue" in data.columns:

        negative_revenue = (
            data["revenue"].dropna() < 0
        ).sum()

        if negative_revenue > 0:

            report["warnings"].append(
                f"Revenue contains "
                f"{negative_revenue} negative value(s)"
            )

    # Debt/Equity should not normally be negative
    if "debt_equity" in data.columns:

        negative_debt_equity = (
            data["debt_equity"].dropna() < 0
        ).sum()

        if negative_debt_equity > 0:

            report["warnings"].append(
                f"Debt/Equity contains "
                f"{negative_debt_equity} negative value(s)"
            )

    # Margins are percentages in our normalized dataset.
    for column in [
        "operating_margin",
        "net_margin",
    ]:

        if column in data.columns:

            values = data[column].dropna()

            suspicious = (
                (values < -100)
                | (values > 100)
            ).sum()

            if suspicious > 0:

                report["warnings"].append(
                    f"{column}: "
                    f"{suspicious} suspicious "
                    f"percentage value(s)"
                )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    is_valid = (
        len(report["errors"]) == 0
    )

    return is_valid, report


# ============================================================
# PRINT VALIDATION REPORT
# ============================================================

def print_validation_report(report):

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL DATA VALIDATION"
    )

    print(
        "=========================================="
    )

    print(
        f"Symbol  : {report['symbol']}"
    )

    print(
        f"Records : {report['records']}"
    )

    print(
        "\nMissing values:"
    )

    for column, count in (
        report["missing_values"].items()
    ):

        print(
            f"  {column:<20} {count}"
        )

    print(
        "\nDuplicate records:"
    )

    print(
        f"  {report['duplicate_records']}"
    )

    print(
        "\nInvalid periods:"
    )

    print(
        f"  {report['invalid_periods']}"
    )

    print(
        "\nWarnings:"
    )

    if report["warnings"]:

        for warning in report["warnings"]:

            print(
                f"  ⚠ {warning}"
            )

    else:

        print(
            "  None"
        )

    print(
        "\nErrors:"
    )

    if report["errors"]:

        for error in report["errors"]:

            print(
                f"  ❌ {error}"
            )

    else:

        print(
            "  None"
        )

    print(
        "\n------------------------------------------"
    )

    if len(report["errors"]) == 0:

        print(
            "✓ FINANCIAL DATA STRUCTURE VALID"
        )

    else:

        print(
            "❌ FINANCIAL DATA REQUIRES REVIEW"
        )

    print(
        "=========================================="
    )


# ============================================================
# TEST
# ============================================================

def main():

    from backend.data_pipeline.financial_data import (
        fetch_financial_data
    )

    symbol = "INFY"

    data = fetch_financial_data(
        symbol
    )

    valid, report = validate_financial_data(
        symbol,
        data
    )

    print_validation_report(
        report
    )

    if not valid:

        raise SystemExit(1)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()