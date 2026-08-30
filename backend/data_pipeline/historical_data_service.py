"""
Week 13 - Historical Data Service

Purpose:
    Provide a stable Data Engineering contract for retrieving
    historical market data.

Responsibilities:
    - Validate stock symbols
    - Validate date ranges
    - Retrieve historical OHLCV data
    - Optionally include adjusted close
    - Report data quality
    - Preserve timezone-aware timestamps
    - Return normalized DataFrame output

This service does NOT:
    - calculate technical indicators
    - calculate financial scores
    - generate trading signals
    - make trading decisions
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from backend.data_pipeline.data_service import (
    get_stock_data,
    get_stock_data_with_adjusted_close,
)


REQUIRED_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


def _validate_date(value: Optional[str]) -> Optional[str]:
    """Validate YYYY-MM-DD date input."""

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"Invalid date '{value}'. Expected YYYY-MM-DD."
        ) from exc

    return value


def _validate_range(
    start_date: Optional[str],
    end_date: Optional[str],
):
    """Validate historical date range."""

    start = _validate_date(start_date)
    end = _validate_date(end_date)

    if start and end and start > end:
        raise ValueError(
            "start_date must be earlier than or equal to end_date."
        )

    return start, end


def get_historical_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_adjusted_close: bool = False,
) -> dict:
    """
    Return normalized historical market data.

    Returns:
        {
            "symbol": str,
            "status": "VALID" | "EMPTY" | "INVALID",
            "start_date": str | None,
            "end_date": str | None,
            "records": int,
            "columns": list[str],
            "data": pandas.DataFrame,
            "data_quality": {
                "missing_required_columns": list[str],
                "missing_values": int,
            }
        }
    """

    if not isinstance(symbol, str) or not symbol.strip():
        return {
            "symbol": symbol,
            "status": "INVALID",
            "start_date": None,
            "end_date": None,
            "records": 0,
            "columns": [],
            "data": pd.DataFrame(),
            "data_quality": {
                "missing_required_columns": [],
                "missing_values": 0,
            },
        }

    symbol = symbol.strip().upper()

    start, end = _validate_range(
        start_date,
        end_date,
    )

    if include_adjusted_close:
        data = get_stock_data_with_adjusted_close(
            symbol,
            start_date=start,
            end_date=end,
        )
    else:
        data = get_stock_data(
            symbol,
            start_date=start,
            end_date=end,
        )

    data = data.copy()

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        return {
            "symbol": symbol,
            "status": "INVALID",
            "start_date": start,
            "end_date": end,
            "records": len(data),
            "columns": list(data.columns),
            "data": data,
            "data_quality": {
                "missing_required_columns": missing_columns,
                "missing_values": 0,
            },
        }

    if data.empty:
        return {
            "symbol": symbol,
            "status": "EMPTY",
            "start_date": start,
            "end_date": end,
            "records": 0,
            "columns": list(data.columns),
            "data": data,
            "data_quality": {
                "missing_required_columns": [],
                "missing_values": 0,
            },
        }

    data = data.sort_values("date").reset_index(drop=True)

    missing_values = int(
        data[REQUIRED_COLUMNS].isna().sum().sum()
    )

    status = (
        "VALID"
        if missing_values == 0
        else "EMPTY"
    )

    return {
        "symbol": symbol,
        "status": status,
        "start_date": start,
        "end_date": end,
        "records": len(data),
        "columns": list(data.columns),
        "data": data,
        "data_quality": {
            "missing_required_columns": [],
            "missing_values": missing_values,
        },
    }


def main():
    """Simple Week 13 service validation."""

    result = get_historical_data(
        "INFY",
        start_date="2025-08-01",
        end_date="2025-08-28",
        include_adjusted_close=True,
    )

    print("=" * 60)
    print("WEEK 13 - HISTORICAL DATA SERVICE")
    print("=" * 60)

    print("Symbol      :", result["symbol"])
    print("Status      :", result["status"])
    print("Records     :", result["records"])
    print("Start date  :", result["start_date"])
    print("End date    :", result["end_date"])
    print("Columns     :", result["columns"])

    print("\nData quality:")
    print(result["data_quality"])

    if not result["data"].empty:
        print("\nLatest row:")
        print(
            result["data"]
            .tail(1)
            .to_string(index=False)
        )

    print("=" * 60)


if __name__ == "__main__":
    main()