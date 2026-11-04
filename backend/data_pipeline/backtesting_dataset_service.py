"""
Week 13 - Backtesting Dataset Service

Purpose:
    Construct a date-aware historical dataset for the backtesting layer.

Data Engineer responsibilities:
    - Retrieve historical market data
    - Align technical indicators to the market evaluation date
    - Select financial reporting periods that are not after the evaluation date
    - Preserve reporting-period information
    - Attach company classification
    - Detect missing and mismatched historical records
    - Expose explicit data-quality and leakage status

This service does NOT:
    - generate trading signals
    - make buy/sell decisions
    - calculate strategy returns
    - evaluate trading performance
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from backend.data_pipeline.historical_data_service import (
    get_historical_data,
)
from backend.data_pipeline.technical_indicator_service import (
    get_technical_indicators,
)
from backend.data_pipeline.financial_service import (
    get_financial_data,
    parse_quarter_period_end,
    _normalize_eval_timestamp,
    _normalize_pub_timestamp,
)
from backend.data_pipeline.classification_service import (
    get_company_classification,
)


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# HELPERS
# ============================================================

def _normalize_date_series(series: pd.Series) -> pd.Series:
    """
    Convert timestamps to calendar dates.

    This is important because daily_prices and
    technical_indicators use different timestamp
    representations for the same Indian trading date.
    """

    values = pd.to_datetime(
        series,
        errors="coerce",
    )

    return values.dt.strftime("%Y-%m-%d")


def _validate_evaluation_date(evaluation_date: str) -> str:
    """
    Validate and normalize the requested evaluation date.
    """

    if not isinstance(evaluation_date, str):
        raise ValueError(
            "evaluation_date must be a string in YYYY-MM-DD format."
        )

    evaluation_date = evaluation_date.strip()

    try:
        parsed = pd.Timestamp(evaluation_date)
    except Exception as exc:
        raise ValueError(
            f"Invalid evaluation_date '{evaluation_date}'. "
            "Expected YYYY-MM-DD."
        ) from exc

    if parsed.strftime("%Y-%m-%d") != evaluation_date:
        raise ValueError(
            f"Invalid evaluation_date '{evaluation_date}'. "
            "Expected YYYY-MM-DD."
        )

    return evaluation_date


def _prepare_financial_data(
    financial: pd.DataFrame,
    evaluation_date: str,
    reporting_lag_days: Optional[int] = 45,
    require_verified_publication_date: bool = False,
) -> tuple[Optional[pd.Series], str]:
    """
    Select the latest eligible financial record as of evaluation_date.

    AUDIT-037 Historical Financial Eligibility Rules:
    -------------------------------------------------
    1. A reporting period ending after evaluation_date must NEVER be selected (future-period leak).
    2. If a verified publication timestamp exists:
       Eligible if and only if publication_timestamp <= evaluation_cutoff.
       Status: 'VERIFIED_POINT_IN_TIME'.
    3. If publication timestamp is NULL, missing, or invalid:
       Eligible if and only if (period_end + reporting_lag_days) <= evaluation_cutoff.
       Status: 'PERIOD_ELIGIBLE_FALLBACK_LAG'.
    4. Missing or invalid publication timestamps must NOT silently become verified availability.
    5. A reporting period ending before evaluation_date must NOT automatically be treated as
       publicly available by evaluation_date without meeting rule 2 or rule 3.
    6. When multiple quarters are eligible, the latest eligible quarter by period_end is selected.
    7. If no quarters are eligible, returns (None, 'NO_ELIGIBLE_RECORDS').
    """
    if financial is None or financial.empty:
        return None, "MISSING"

    if "quarter" not in financial.columns:
        return None, "MISSING_QUARTER_COLUMN"

    eval_ts = _normalize_eval_timestamp(evaluation_date)

    eligible_records = []

    for idx, row in financial.iterrows():
        q_val = row.get("quarter")
        period_end = parse_quarter_period_end(q_val)
        if period_end is None:
            continue
        if period_end.tzinfo is not None:
            period_end = period_end.tz_convert("UTC").tz_localize(None)

        # Rule 1: Never select a future reporting period
        if period_end > eval_ts:
            continue

        # Check publication timestamp
        pub_val = row.get("publication_date") if "publication_date" in financial.columns else None
        pub_ts = _normalize_pub_timestamp(pub_val)

        if pub_ts is not None:
            # Rule 2: Verified publication timestamp
            if pub_ts <= eval_ts:
                avail_date_str = pub_ts.strftime("%Y-%m-%d")
                eligible_records.append((period_end, pub_ts, "VERIFIED_POINT_IN_TIME", True, avail_date_str, row))
        elif not require_verified_publication_date:
            # Rule 3: Missing/invalid timestamp -> estimated reporting-lag fallback (legacy mode only)
            lag = max(0, int(reporting_lag_days)) if reporting_lag_days is not None else 45
            avail_ts = period_end + pd.Timedelta(days=lag)
            if avail_ts <= eval_ts:
                avail_date_str = avail_ts.strftime("%Y-%m-%d")
                eligible_records.append((period_end, avail_ts, "PERIOD_ELIGIBLE_FALLBACK_LAG", False, avail_date_str, row))

    if not eligible_records:
        return None, "NO_ELIGIBLE_RECORDS"

    # Sort eligible records chronologically by period_end then availability date
    eligible_records.sort(key=lambda x: (x[0], x[1]))
    best_period_end, best_avail_ts, best_status, best_is_verified, best_avail_date_str, best_row = eligible_records[-1]

    selected = best_row.copy()
    selected["_is_publication_date_verified"] = best_is_verified
    selected["_availability_status"] = best_status
    selected["_availability_date"] = best_avail_date_str

    return selected, best_status


# ============================================================
# DATASET CONSTRUCTION
# ============================================================

def build_backtesting_dataset(
    symbol: str,
    start_date: str,
    end_date: str,
    reporting_lag_days: int = 45,
    filter_synthetic_holidays: bool = False,
    quarantine_unresolved_anomalies: bool = False,
    require_verified_publication_date: bool = False,
) -> pd.DataFrame:
    """
    Build a historical backtesting input dataset.

    Every output row represents one evaluation date.

    The dataset contains:

        symbol
        evaluation_date

        Market:
            open
            high
            low
            close
            volume
            adjusted_close

        Technical:
            rsi
            macd
            macd_signal
            ema_20
            ema_50
            ema_200
            macd_histogram
            atr_14
            technical_score

        Financial:
            reporting_period
            revenue
            net_profit
            eps
            roe
            roce
            debt_equity
            operating_margin
            net_margin

        Classification:
            company_name
            sector
            industry

        Quality:
            market_data_status
            technical_data_status
            financial_data_status
            financial_availability_status
            leakage_check
    """

    if not symbol or not isinstance(symbol, str):
        return pd.DataFrame()

    symbol = symbol.strip().upper()

    if not symbol:
        return pd.DataFrame()

    start_date = _validate_evaluation_date(
        start_date
    )

    end_date = _validate_evaluation_date(
        end_date
    )

    if pd.Timestamp(start_date) > pd.Timestamp(end_date):
        raise ValueError(
            "start_date must be earlier than or equal to end_date."
        )

    # ========================================================
    # MARKET DATA
    # ========================================================

    market_result = get_historical_data(
        symbol,
        start_date=start_date,
        end_date=end_date,
        include_adjusted_close=True,
        filter_synthetic_holidays=filter_synthetic_holidays,
        quarantine_unresolved_anomalies=quarantine_unresolved_anomalies,
    )

    market = market_result.get("data")

    if market is None or market.empty:
        return pd.DataFrame()

    market = market.copy()

    market["evaluation_date"] = (
        _normalize_date_series(
            market["date"]
        )
    )

    market_data_columns = [
        "evaluation_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
    ]

    market = market[
        [
            column
            for column in market_data_columns
            if column in market.columns
        ]
    ]

    market["market_data_status"] = "AVAILABLE"

    # ========================================================
    # TECHNICAL DATA
    # ========================================================

    technical = get_technical_indicators(
        symbol
    )

    if technical is None:
        technical = pd.DataFrame()

    if not technical.empty:

        technical = technical.copy()

        technical["evaluation_date"] = (
            _normalize_date_series(
                technical["date"]
            )
        )

        technical_columns = [
            "evaluation_date",
            "rsi",
            "macd",
            "macd_signal",
            "ema_20",
            "ema_50",
            "ema_200",
            "macd_histogram",
            "atr_14",
            "technical_score",
        ]

        technical = technical[
            [
                column
                for column in technical_columns
                if column in technical.columns
            ]
        ]

        # Keep one technical observation per evaluation date.
        technical = (
            technical
            .sort_values("evaluation_date")
            .drop_duplicates(
                subset=["evaluation_date"],
                keep="last",
            )
        )

        technical["technical_data_status"] = (
            "AVAILABLE"
        )

    else:

        technical = pd.DataFrame(
            columns=[
                "evaluation_date",
                "technical_data_status",
            ]
        )

    # ========================================================
    # MARKET + TECHNICAL ALIGNMENT
    # ========================================================

    dataset = market.merge(
        technical,
        on="evaluation_date",
        how="left",
    )

    dataset["technical_data_status"] = (
        dataset["technical_data_status"]
        .fillna("MISSING")
    )

    # ========================================================
    # FINANCIAL DATA (Point-in-Time per evaluation date)
    # ========================================================

    financial = get_financial_data(
        symbol
    )

    financial_cols = [
        "revenue",
        "net_profit",
        "eps",
        "roe",
        "roce",
        "debt_equity",
        "operating_margin",
        "net_margin",
    ]

    fin_records = []
    for eval_date in dataset["evaluation_date"]:
        f_rec, f_status = _prepare_financial_data(
            financial,
            eval_date,
            reporting_lag_days=reporting_lag_days,
            require_verified_publication_date=require_verified_publication_date,
        )
        if f_rec is not None:
            r_dict = {col: f_rec.get(col) for col in financial_cols}
            r_dict["reporting_period"] = f_rec.get("quarter")
            r_dict["financial_data_status"] = f_status
            r_dict["publication_date"] = str(f_rec.get("publication_date")).strip() if pd.notna(f_rec.get("publication_date")) and str(f_rec.get("publication_date")).strip() else None
            is_ver = bool(f_rec.get("_is_publication_date_verified", False))
            r_dict["is_financial_publication_verified"] = is_ver
            if is_ver:
                r_dict["financial_availability_status"] = "VERIFIED"
                r_dict["financial_eligibility_mode"] = "VERIFIED_PUBLICATION"
            else:
                r_dict["financial_availability_status"] = "UNVERIFIED"
                r_dict["financial_eligibility_mode"] = "ESTIMATED_REPORTING_LAG"
        else:
            r_dict = {col: None for col in financial_cols}
            r_dict["reporting_period"] = None
            r_dict["financial_data_status"] = f_status
            r_dict["publication_date"] = None
            r_dict["is_financial_publication_verified"] = None
            r_dict["financial_availability_status"] = "MISSING" if f_status == "MISSING" else "UNAVAILABLE"
            r_dict["financial_eligibility_mode"] = f_status
        fin_records.append(r_dict)

    fin_df = pd.DataFrame(fin_records, index=dataset.index)
    for col in [
        "reporting_period",
        "revenue",
        "net_profit",
        "eps",
        "roe",
        "roce",
        "debt_equity",
        "operating_margin",
        "net_margin",
        "financial_data_status",
        "financial_availability_status",
        "financial_eligibility_mode",
        "is_financial_publication_verified",
        "publication_date",
    ]:
        dataset[col] = fin_df[col]

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    classification = get_company_classification(
        symbol
    )

    if not isinstance(
        classification,
        dict,
    ):
        classification = {}

    dataset["symbol"] = symbol

    dataset["company_name"] = (
        classification.get(
            "company_name"
        )
    )

    dataset["sector"] = (
        classification.get(
            "sector"
        )
    )

    dataset["industry"] = (
        classification.get(
            "industry"
        )
    )

    # ========================================================
    # LEAKAGE VALIDATION (AUDIT-037 Point-in-Time Verification)
    # ========================================================

    evaluation_dates = dataset["evaluation_date"].apply(_normalize_eval_timestamp)

    def _parse_period_end_ts(val):
        try:
            p = pd.Period(val)
            return p.end_time
        except Exception:
            return pd.to_datetime(val, errors="coerce")

    reporting_dates = dataset["reporting_period"].apply(_parse_period_end_ts)

    # 1. Reporting period after evaluation date (future quarter)
    future_financial_mask = (
        reporting_dates.notna()
        & evaluation_dates.notna()
        & (reporting_dates > evaluation_dates)
    )

    # 2. Premature publication leak (verified pub date after evaluation date)
    def _parse_pub_ts_naive(val):
        ts = _normalize_pub_timestamp(val)
        if ts is not None and ts.tzinfo is not None:
            return ts.tz_convert("UTC").tz_localize(None)
        return ts

    pub_dates = dataset["publication_date"].apply(_parse_pub_ts_naive)
    future_pub_mask = (
        dataset["is_financial_publication_verified"].eq(True)
        & pub_dates.notna()
        & evaluation_dates.notna()
        & (pub_dates > evaluation_dates)
    )

    # 3. Premature fallback leak (fallback availability date after evaluation date)
    fallback_lag = max(0, int(reporting_lag_days)) if reporting_lag_days is not None else 45
    fallback_avail_dates = reporting_dates + pd.Timedelta(days=fallback_lag)
    future_fallback_mask = (
        dataset["financial_eligibility_mode"].eq("ESTIMATED_REPORTING_LAG")
        & fallback_avail_dates.notna()
        & evaluation_dates.notna()
        & (fallback_avail_dates > evaluation_dates)
    )

    dataset["leakage_check"] = "PASS"

    dataset.loc[
        future_financial_mask,
        "leakage_check",
    ] = "FAIL_FUTURE_FINANCIAL_PERIOD"

    dataset.loc[
        future_pub_mask,
        "leakage_check",
    ] = "FAIL_PRE_PUBLICATION_LEAK"

    dataset.loc[
        future_fallback_mask,
        "leakage_check",
    ] = "FAIL_PRE_AVAILABILITY_LEAK"

    # ========================================================
    # FINAL NORMALIZATION
    # ========================================================

    dataset = dataset.sort_values(
        "evaluation_date"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Duplicate evaluation-date protection
    # --------------------------------------------------------

    dataset = dataset.drop_duplicates(
        subset=[
            "symbol",
            "evaluation_date",
        ],
        keep="last",
    )

    # --------------------------------------------------------
    # Stable column ordering
    # --------------------------------------------------------

    columns = [
        "symbol",
        "evaluation_date",
        "company_name",
        "sector",
        "industry",

        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",

        "rsi",
        "macd",
        "macd_signal",
        "ema_20",
        "ema_50",
        "ema_200",
        "macd_histogram",
        "atr_14",
        "technical_score",

        "reporting_period",
        "revenue",
        "net_profit",
        "eps",
        "roe",
        "roce",
        "debt_equity",
        "operating_margin",
        "net_margin",

        "publication_date",
        "financial_eligibility_mode",
        "is_financial_publication_verified",

        "market_data_status",
        "technical_data_status",
        "financial_data_status",
        "financial_availability_status",
        "leakage_check",
    ]

    dataset = dataset[
        [
            column
            for column in columns
            if column in dataset.columns
        ]
    ]

    return dataset


# ============================================================
# QUALITY REPORT
# ============================================================

def get_dataset_quality_report(
    dataset: pd.DataFrame,
) -> dict:
    """
    Return Data Engineering quality metrics for a
    constructed backtesting dataset.
    """

    if dataset is None or dataset.empty:
        return {
            "status": "EMPTY",
            "rows": 0,
            "duplicate_observations": 0,
            "missing_market_data": 0,
            "missing_technical_data": 0,
            "future_financial_periods": 0,
            "leakage_failures": 0,
        }

    duplicate_count = int(
        dataset.duplicated(
            subset=[
                "symbol",
                "evaluation_date",
            ]
        ).sum()
    )

    missing_market = int(
        dataset["market_data_status"]
        .ne("AVAILABLE")
        .sum()
    )

    missing_technical = int(
        dataset["technical_data_status"]
        .ne("AVAILABLE")
        .sum()
    )

    future_financial = int(
        dataset["leakage_check"]
        .eq("FAIL_FUTURE_FINANCIAL_PERIOD")
        .sum()
    )

    leakage_failures = int(
        dataset["leakage_check"]
        .ne("PASS")
        .sum()
    )

    return {
        "status": "VALID",
        "rows": len(dataset),
        "symbols": int(
            dataset["symbol"].nunique()
        ),
        "first_evaluation_date": (
            dataset["evaluation_date"].min()
        ),
        "last_evaluation_date": (
            dataset["evaluation_date"].max()
        ),
        "duplicate_observations": (
            duplicate_count
        ),
        "missing_market_data": (
            missing_market
        ),
        "missing_technical_data": (
            missing_technical
        ),
        "future_financial_periods": (
            future_financial
        ),
        "leakage_failures": (
            leakage_failures
        ),
    }


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print("=" * 70)
    print("WEEK 13 - BACKTESTING DATASET SERVICE")
    print("=" * 70)

    symbol = "INFY"

    dataset = build_backtesting_dataset(
        symbol,
        start_date="2025-08-01",
        end_date="2025-08-28",
    )

    print("Symbol:", symbol)
    print("Rows:", len(dataset))

    if not dataset.empty:

        print(
            "First evaluation date:",
            dataset["evaluation_date"].min(),
        )

        print(
            "Last evaluation date:",
            dataset["evaluation_date"].max(),
        )

        print("\nColumns:")
        print(list(dataset.columns))

        print("\nFirst 3 observations:")
        print(
            dataset.head(3).to_string(
                index=False
            )
        )

        print("\nQuality report:")
        print(
            get_dataset_quality_report(
                dataset
            )
        )

    print("=" * 70)


if __name__ == "__main__":
    main()