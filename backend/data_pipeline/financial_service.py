from typing import Optional, Dict, Any
"""
Financial Data Service
======================

Week 3 / Week 11 Data Engineering Layer

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
# HELPER: PARSE QUARTER PERIOD END & TIMESTAMPS
# ============================================================

def parse_quarter_period_end(quarter_val):
    """
    Parse a quarter string (e.g., '2025-Q1' or '2025-03-31') into its period-end Timestamp.
    Returns None if parsing fails.
    """
    if pd.isna(quarter_val) or quarter_val is None:
        return None
    val_str = str(quarter_val).strip()
    if not val_str:
        return None
    try:
        p = pd.Period(val_str)
        return p.end_time
    except Exception:
        pass
    try:
        ts = pd.to_datetime(val_str)
        return pd.Period(ts, freq="Q").end_time
    except Exception:
        pass
    return None


def _normalize_eval_timestamp(evaluation_date) -> pd.Timestamp:
    """
    Parse an evaluation_date into a timezone-naive UTC pd.Timestamp.
    Applies end-of-day semantics (23:59:59.999999) to date-only strings (YYYY-MM-DD).
    """
    eval_str = str(evaluation_date).strip()
    try:
        if len(eval_str) == 10 and eval_str.count("-") == 2:
            ts = pd.Timestamp(f"{eval_str} 23:59:59.999999")
        else:
            ts = pd.to_datetime(eval_str)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        return ts
    except Exception as exc:
        raise ValueError(
            f"Invalid evaluation_date '{evaluation_date}'. Expected YYYY-MM-DD or timestamp."
        ) from exc


def _normalize_pub_timestamp(pub_val) -> Optional[pd.Timestamp]:
    """Parse a publication_date into a timezone-naive UTC pd.Timestamp."""
    if pd.isna(pub_val) or pub_val is None:
        return None
    val_str = str(pub_val).strip()
    if not val_str:
        return None
    try:
        ts = pd.to_datetime(val_str)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        return ts
    except Exception:
        return None


# ============================================================
# GET FINANCIAL DATA
# ============================================================

def get_financial_data(symbol, evaluation_date=None, reporting_lag_days=45):
    """
    Return quarterly financial data for one stock, optionally filtered by historical evaluation_date.

    Parameters
    ----------
    symbol : str
        NSE symbol without .NS.
    evaluation_date : Optional[str]
        Point-in-time cutoff date (e.g. '2025-01-15' or ISO timestamp).
        If provided, only quarters eligible as of evaluation_date are returned.
        If None, all quarters in database are returned (latest current snapshot).
    reporting_lag_days : int
        Conservative fallback lag in calendar days when publication_date is NULL/missing (default: 45).

    Returns
    -------
    pandas.DataFrame

        Standardized financial records ordered
        from oldest to newest quarter.

    Returns an empty DataFrame if the symbol
    does not exist or has no eligible financial records.
    """

    symbol = symbol.upper().strip()

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(quarterly_results)")
        table_cols = [row[1] for row in cursor.fetchall()]
        has_pub_date = "publication_date" in table_cols

        pub_col_sql = ", quarterly_results.publication_date" if has_pub_date else ", NULL AS publication_date"

        query = f"""
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
                {pub_col_sql}

            FROM quarterly_results

            INNER JOIN companies
                ON companies.id =
                   quarterly_results.company_id

            WHERE companies.symbol = ?

            ORDER BY quarterly_results.quarter ASC
        """

        data = pd.read_sql_query(
            query,
            connection,
            params=(symbol,)
        )

    finally:
        connection.close()

    if data.empty:
        empty_df = pd.DataFrame(columns=FINANCIAL_COLUMNS)
        empty_df.attrs["data_eligibility_status"] = "NO_ELIGIBLE_RECORDS" if evaluation_date else "NO_RECORDS"
        empty_df.attrs["evaluation_date"] = evaluation_date
        return empty_df

    # --------------------------------------------------------
    # Point-in-time historical filtering vs Latest Current
    # --------------------------------------------------------
    overall_status = "LATEST_CURRENT"
    if evaluation_date is not None:
        eval_ts = _normalize_eval_timestamp(evaluation_date)
        eligible_indices = []
        statuses = []

        for idx, row in data.iterrows():
            q_val = row.get("quarter")
            pub_val = row.get("publication_date")

            period_end = parse_quarter_period_end(q_val)
            if period_end is None:
                continue
            if period_end.tzinfo is not None:
                period_end = period_end.tz_convert("UTC").tz_localize(None)

            pub_ts = _normalize_pub_timestamp(pub_val)
            if pub_ts is not None:
                if pub_ts <= eval_ts:
                    eligible_indices.append(idx)
                    statuses.append("VERIFIED_POINT_IN_TIME")
            else:
                lag = max(0, int(reporting_lag_days)) if reporting_lag_days is not None else 45
                avail_ts = period_end + pd.Timedelta(days=lag)
                if avail_ts <= eval_ts:
                    eligible_indices.append(idx)
                    statuses.append("PERIOD_ELIGIBLE_FALLBACK_LAG")

        if not eligible_indices:
            empty_df = pd.DataFrame(columns=FINANCIAL_COLUMNS)
            empty_df.attrs["data_eligibility_status"] = "NO_ELIGIBLE_RECORDS"
            empty_df.attrs["evaluation_date"] = evaluation_date
            return empty_df

        data = data.loc[eligible_indices].copy()
        if all(s == "VERIFIED_POINT_IN_TIME" for s in statuses):
            overall_status = "VERIFIED_POINT_IN_TIME"
        else:
            overall_status = "PERIOD_ELIGIBLE_FALLBACK_LAG"

    # --------------------------------------------------------
    # Ensure consistent columns
    # --------------------------------------------------------

    for column in FINANCIAL_COLUMNS:

        if column not in data.columns:

            data[column] = None

    result_df = data[
        FINANCIAL_COLUMNS
    ].copy()
    result_df.attrs["data_eligibility_status"] = overall_status
    result_df.attrs["evaluation_date"] = evaluation_date

    return result_df


# ============================================================
# GET LATEST FINANCIAL DATA
# ============================================================

def get_latest_financial_data(symbol, evaluation_date=None, reporting_lag_days=45):
    """
    Return the most recent available financial record for a stock,
    strictly enforcing point-in-time public availability on evaluation_date.

    Point-in-Time Availability Rules:
    ---------------------------------
    1. If publication_date is recorded for a quarterly record:
       The record is eligible IF AND ONLY IF publication_date <= evaluation_timestamp.
       Availability status: 'VERIFIED_POINT_IN_TIME'.
    2. If publication_date is missing / NULL:
       The record's availability is conservatively approximated as:
       period_end + reporting_lag_days (default 45 days, following SEBI LODR Reg 33).
       Availability status: 'PERIOD_ELIGIBLE_FALLBACK_LAG'.
       Future periods where (period_end + lag) > evaluation_timestamp are strictly excluded.
    3. If evaluation_date is None:
       Returns the latest record in the database.
       Availability status: 'LATEST_CURRENT'.

    Returns None when no financial record exists or no record was available
    as of the evaluation date.
    """

    symbol = symbol.upper().strip()

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(quarterly_results)")
        table_cols = [row[1] for row in cursor.fetchall()]
        has_pub_date = "publication_date" in table_cols

        pub_col_sql = ", quarterly_results.publication_date" if has_pub_date else ", NULL AS publication_date"

        query = f"""
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
                {pub_col_sql}

            FROM quarterly_results

            INNER JOIN companies
                ON companies.id =
                   quarterly_results.company_id

            WHERE companies.symbol = ?

            ORDER BY quarterly_results.quarter ASC
        """

        data = pd.read_sql_query(
            query,
            connection,
            params=(symbol,)
        )

    finally:
        connection.close()

    # --------------------------------------------------------
    # No financial records exist for symbol
    # --------------------------------------------------------
    if data.empty:
        return None

    # --------------------------------------------------------
    # Point-in-time historical filtering vs Latest Current
    # --------------------------------------------------------
    if evaluation_date is None:
        selected_row = data.iloc[-1].copy()
        pub_raw = selected_row.get("publication_date")
        record_status = "LATEST_CURRENT"
        is_verified = pd.notna(pub_raw) and bool(str(pub_raw).strip())
    else:
        eval_ts = _normalize_eval_timestamp(evaluation_date)

        eligible_indices = []
        statuses = {}
        verified_flags = {}

        for idx, row in data.iterrows():
            q_val = row.get("quarter")
            pub_val = row.get("publication_date")

            period_end = parse_quarter_period_end(q_val)
            if period_end is None:
                continue
            if period_end.tzinfo is not None:
                period_end = period_end.tz_convert("UTC").tz_localize(None)

            pub_ts = _normalize_pub_timestamp(pub_val)
            if pub_ts is not None:
                if pub_ts <= eval_ts:
                    eligible_indices.append(idx)
                    statuses[idx] = "VERIFIED_POINT_IN_TIME"
                    verified_flags[idx] = True
            else:
                # Conservative fallback lag under SEBI LODR Reg 33
                lag = max(0, int(reporting_lag_days)) if reporting_lag_days is not None else 45
                avail_ts = period_end + pd.Timedelta(days=lag)
                if avail_ts <= eval_ts:
                    eligible_indices.append(idx)
                    statuses[idx] = "PERIOD_ELIGIBLE_FALLBACK_LAG"
                    verified_flags[idx] = False

        if not eligible_indices:
            return None

        # Sort eligible records chronologically; latest is the last index
        latest_idx = eligible_indices[-1]
        selected_row = data.loc[latest_idx].copy()
        record_status = statuses[latest_idx]
        is_verified = verified_flags[latest_idx]

    # --------------------------------------------------------
    # Build standardized return dictionary with numeric casts
    # --------------------------------------------------------
    numeric_columns = [
        "revenue",
        "net_profit",
        "eps",
        "roe",
        "roce",
        "debt_equity",
        "operating_margin",
        "net_margin",
    ]

    res_dict = {}
    for col in FINANCIAL_COLUMNS:
        val = selected_row.get(col)
        if col in numeric_columns:
            try:
                res_dict[col] = float(val) if pd.notna(val) else None
            except (ValueError, TypeError):
                res_dict[col] = None
        else:
            res_dict[col] = val if pd.notna(val) else None

    # Attach point-in-time audit metadata
    pub_raw = selected_row.get("publication_date")
    res_dict["publication_date"] = str(pub_raw).strip() if pd.notna(pub_raw) and str(pub_raw).strip() else None
    res_dict["availability_status"] = record_status
    res_dict["is_publication_date_verified"] = is_verified

    return res_dict



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
# SAVE FINANCIAL HEALTH SCORES
# ============================================================

def save_financial_health_scores(
    symbol: str,
    date: str = None
) -> bool:
    """
    Calculates and persists Financial Health Score
    metrics for a stock symbol into the
    financial_scores database table.

    Parameters
    ----------
    symbol : str
        Stock symbol (e.g. "TCS", "INFY").

    date : str, optional
        Snapshot calculation date (YYYY-MM-DD).
        Defaults to current UTC date if None.

    Returns
    -------
    bool
        True if persisted successfully,
        False if skipped (e.g. INSUFFICIENT score
        or unknown company symbol).
    """

    from datetime import datetime, timezone

    from backend.engines.financial_engine import (
        analyze_financial_health
    )

    if (
        not symbol
        or not isinstance(symbol, str)
        or not symbol.strip()
    ):
        return False

    symbol = symbol.strip().upper()

    # --------------------------------------------------------
    # Calculate scores via pure financial engine
    # --------------------------------------------------------

    score_dict = analyze_financial_health(
        symbol
    )

    # --------------------------------------------------------
    # Check score availability
    # --------------------------------------------------------

    overall_score = score_dict.get(
        "overall_score"
    )

    if (
        overall_score is None
        or score_dict.get("status") == "INSUFFICIENT"
    ):
        return False

    # --------------------------------------------------------
    # Resolve date
    # --------------------------------------------------------

    if (
        not date
        or not isinstance(date, str)
        or not date.strip()
    ):

        date_str = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

    else:

        date_str = date.strip()

    # --------------------------------------------------------
    # Resolve company ID
    # --------------------------------------------------------

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        cursor = connection.cursor()

        cursor.execute(
            "PRAGMA foreign_keys = ON"
        )

        cursor.execute(
            """
            SELECT id
            FROM companies
            WHERE symbol = ?
            """,
            (symbol,),
        )

        row = cursor.fetchone()

        if not row:

            return False

        company_id = row[0]

        profitability_score = (
            score_dict.get(
                "profitability_score"
            )
        )

        growth_score = (
            score_dict.get(
                "growth_score"
            )
        )

        valuation_score = (
            score_dict.get(
                "valuation_score"
            )
        )

        # ----------------------------------------------------
        # Idempotent persistence
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM financial_scores
            WHERE company_id = ?
              AND date = ?
            """,
            (
                company_id,
                date_str,
            ),
        )

        cursor.execute(
            """
            INSERT INTO financial_scores (
                company_id,
                date,
                profitability_score,
                growth_score,
                valuation_score,
                overall_score
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                date_str,
                profitability_score,
                growth_score,
                valuation_score,
                overall_score,
            ),
        )

        connection.commit()

        return True

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


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