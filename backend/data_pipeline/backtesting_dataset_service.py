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
) -> tuple[Optional[pd.Series], str]:
    """
    Select the latest reporting period that is not after
    the evaluation date.

    Important limitation:
        quarterly_results currently contains the reporting
        period end date but not the actual public announcement
        / availability date.

    Therefore this function prevents future-period leakage,
    but cannot independently prove point-in-time financial
    availability.
    """

    if financial is None or financial.empty:
        return None, "MISSING"

    if "quarter" not in financial.columns:
        return None, "MISSING_QUARTER_COLUMN"

    data = financial.copy()

    data["_quarter_date"] = pd.to_datetime(
        data["quarter"],
        errors="coerce",
    )

    data = data.dropna(
        subset=["_quarter_date"]
    )

    if data.empty:
        return None, "INVALID_QUARTER_DATA"

    evaluation_timestamp = pd.Timestamp(
        evaluation_date
    )

    # --------------------------------------------------------
    # Never select a reporting period after evaluation_date.
    # --------------------------------------------------------

    eligible = data[
        data["_quarter_date"] <= evaluation_timestamp
    ].copy()

    if eligible.empty:
        return None, "NO_ELIGIBLE_REPORTING_PERIOD"

    eligible = eligible.sort_values(
        "_quarter_date"
    )

    selected = eligible.iloc[-1].copy()

    selected = selected.drop(
        labels=["_quarter_date"]
    )

    return (
        selected,
        "PERIOD_ELIGIBLE_AVAILABILITY_UNVERIFIED",
    )


# ============================================================
# DATASET CONSTRUCTION
# ============================================================

def build_backtesting_dataset(
    symbol: str,
    start_date: str,
    end_date: str,
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
    # FINANCIAL DATA
    # ========================================================

    financial = get_financial_data(
        symbol
    )

    financial_record, financial_status = (
        _prepare_financial_data(
            financial,
            end_date,
        )
    )

    # --------------------------------------------------------
    # Financial data is attached based on reporting period.
    # It is NOT claimed to be point-in-time announcement data.
    # --------------------------------------------------------

    if financial_record is not None:

        for column in [
            "quarter",
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]:

            if column in financial_record.index:
                dataset[column] = (
                    financial_record[column]
                )
            else:
                dataset[column] = None

        dataset["reporting_period"] = (
            financial_record.get("quarter")
        )

        dataset["financial_data_status"] = (
            financial_status
        )

    else:

        for column in [
            "reporting_period",
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]:

            dataset[column] = None

        dataset["financial_data_status"] = (
            financial_status
        )

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
    # LEAKAGE VALIDATION
    # ========================================================

    evaluation_dates = pd.to_datetime(
        dataset["evaluation_date"],
        errors="coerce",
    )

    reporting_dates = pd.to_datetime(
        dataset["reporting_period"],
        errors="coerce",
    )

    future_financial_mask = (
        reporting_dates.notna()
        & evaluation_dates.notna()
        & (reporting_dates > evaluation_dates)
    )

    dataset["leakage_check"] = "PASS"

    dataset.loc[
        future_financial_mask,
        "leakage_check",
    ] = "FAIL_FUTURE_FINANCIAL_PERIOD"

    dataset["financial_availability_status"] = (
        "UNVERIFIED"
    )

    dataset.loc[
        dataset["financial_data_status"] == "MISSING",
        "financial_availability_status",
    ] = "MISSING"

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