"""
Financial Data Collector
========================

Week 3 Data Engineering Layer

Responsibilities:
    1. Fetch financial data from yfinance
    2. Normalize financial values
    3. Prepare standardized records
    4. Calculate ROCE from financial-statement data when possible

This module does NOT calculate financial scores.
That belongs to the Logic Engineering layer.
"""

import yfinance as yf
import pandas as pd


# ============================================================
# REQUIRED FINANCIAL FIELDS
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
# HELPER FUNCTIONS
# ============================================================

def clean_number(value):
    """
    Convert a financial value into a float.

    Returns None when the value cannot be converted.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None

        return float(value)

    except (TypeError, ValueError):

        return None


def get_statement_value(statement, row_name, period):
    """
    Safely retrieve a value from a yfinance financial statement.
    """

    try:

        if statement is None or statement.empty:
            return None

        if row_name not in statement.index:
            return None

        if period not in statement.columns:
            return None

        return clean_number(
            statement.loc[row_name, period]
        )

    except Exception:

        return None


# ============================================================
# ROCE CALCULATION
# ============================================================

def calculate_roce(ebit, total_assets, current_liabilities):
    """
    Calculate Return on Capital Employed.

    Formula:

        ROCE = EBIT / Capital Employed × 100

    Capital Employed:

        Total Assets - Current Liabilities

    Returns None when the required values are unavailable
    or capital employed is zero.
    """

    ebit = clean_number(ebit)
    total_assets = clean_number(total_assets)
    current_liabilities = clean_number(
        current_liabilities
    )

    if (
        ebit is None
        or total_assets is None
        or current_liabilities is None
    ):
        return None

    capital_employed = (
        total_assets - current_liabilities
    )

    if capital_employed == 0:
        return None

    return (
        ebit / capital_employed
    ) * 100


# ============================================================
# FINANCIAL DATA FETCH
# ============================================================

def fetch_financial_data(symbol):
    """
    Fetch quarterly financial data for one NSE stock.

    Parameters
    ----------
    symbol : str
        NSE symbol without .NS.

    Returns
    -------
    pandas.DataFrame or None

    Standardized columns:

        symbol
        quarter
        revenue
        net_profit
        eps
        roe
        roce
        debt_equity
        operating_margin
        net_margin
    """

    symbol = symbol.upper().strip()

    yahoo_symbol = (
        symbol
        if symbol.endswith(".NS")
        else f"{symbol}.NS"
    )

    print(
        f"\nDownloading financial data "
        f"for {yahoo_symbol}..."
    )

    import time

    try:

        ticker = yf.Ticker(
            yahoo_symbol
        )

        # ----------------------------------------------------
        # RATE LIMITING & RETRY (PHASE 4)
        # ----------------------------------------------------
        max_retries = 3
        base_delay = 5

        income_statement = None
        balance_sheet = None
        info = None

        for attempt in range(1, max_retries + 1):
            try:
                # ----------------------------------------------------
                # FINANCIAL STATEMENTS
                # ----------------------------------------------------
                income_statement = (
                    ticker.quarterly_income_stmt
                )

                balance_sheet = (
                    ticker.quarterly_balance_sheet
                )

                # ----------------------------------------------------
                # COMPANY INFORMATION
                # ----------------------------------------------------
                info = ticker.info
                break # Success
            except Exception as e:
                print(f"WARNING: Rate limit / timeout on {yahoo_symbol} (Attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    raise
                time.sleep(base_delay * attempt)

        if (
            income_statement is None
            or income_statement.empty
        ):

            print(
                f"WARNING: No quarterly income "
                f"statement for {symbol}"
            )

            return None

        # ----------------------------------------------------
        # COMPANY-LEVEL METRICS
        # ----------------------------------------------------

        roe = clean_number(
            info.get("returnOnEquity")
        )

        debt_equity = clean_number(
            info.get("debtToEquity")
        )

        operating_margin = clean_number(
            info.get("operatingMargins")
        )

        net_margin = clean_number(
            info.get("profitMargins")
        )

        # yfinance returns margins as decimal ratios.
        # Convert to percentages for our database.

        if operating_margin is not None:

            operating_margin *= 100

        if net_margin is not None:

            net_margin *= 100

        # ----------------------------------------------------
        # PREPARE RECORDS
        # ----------------------------------------------------

        records = []

        for period in income_statement.columns:

            # ------------------------------------------------
            # Income statement
            # ------------------------------------------------

            revenue = get_statement_value(
                income_statement,
                "Total Revenue",
                period
            )

            net_profit = get_statement_value(
                income_statement,
                "Net Income",
                period
            )

            eps = get_statement_value(
                income_statement,
                "Diluted EPS",
                period
            )

            if eps is None:

                eps = get_statement_value(
                    income_statement,
                    "Basic EPS",
                    period
                )

            # ------------------------------------------------
            # EBIT
            # ------------------------------------------------

            ebit = get_statement_value(
                income_statement,
                "EBIT",
                period
            )

            # Some companies may expose
            # Operating Income instead.

            if ebit is None:

                ebit = get_statement_value(
                    income_statement,
                    "Operating Income",
                    period
                )

            # ------------------------------------------------
            # Balance sheet
            # ------------------------------------------------

            total_assets = get_statement_value(
                balance_sheet,
                "Total Assets",
                period
            )

            current_liabilities = get_statement_value(
                balance_sheet,
                "Current Liabilities",
                period
            )

            # ------------------------------------------------
            # ROCE
            # ------------------------------------------------

            roce = calculate_roce(
                ebit,
                total_assets,
                current_liabilities
            )

            # ------------------------------------------------
            # Reporting period
            # ------------------------------------------------

            if hasattr(period, "strftime"):

                quarter = period.strftime(
                    "%Y-%m-%d"
                )

            else:

                quarter = str(period)

            # ------------------------------------------------
            # Create normalized record
            # ------------------------------------------------

            record = {
                "symbol": symbol,
                "quarter": quarter,
                "revenue": revenue,
                "net_profit": net_profit,
                "eps": eps,
                "roe": roe,
                "roce": roce,
                "debt_equity": debt_equity,
                "operating_margin": operating_margin,
                "net_margin": net_margin,
            }

            records.append(record)

        if not records:

            print(
                f"WARNING: No financial records "
                f"created for {symbol}"
            )

            return None

        data = pd.DataFrame(
            records,
            columns=[
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
        )

        return data

    except Exception as error:

        print(
            f"ERROR: Failed to fetch financial "
            f"data for {symbol}: {error}"
        )

        return None


# ============================================================
# TEST FUNCTION
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        "SWING TRADING PLATFORM"
    )

    print(
        "FINANCIAL DATA COLLECTION TEST"
    )

    print(
        "=========================================="
    )

    symbol = "INFY"

    data = fetch_financial_data(
        symbol
    )

    if data is None:

        print(
            "\n❌ Financial data collection failed."
        )

        return

    print(
        f"\n✓ Records returned: {len(data)}"
    )

    print(
        "\nColumns:"
    )

    print(
        data.columns.tolist()
    )

    print(
        "\nFinancial data:"
    )

    print(
        data.to_string(index=False)
    )

    print(
        "\n=========================================="
    )

    print(
        "FINANCIAL DATA TEST COMPLETE"
    )

    print(
        "=========================================="
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()