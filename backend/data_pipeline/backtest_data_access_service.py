"""
Week 14 - Backtest Data Access Service

Provides a clean interface for downstream backtesting components to access
historical-only market, technical, and financial inputs for a specific date
or date range.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.data_pipeline.backtesting_dataset_service import (
    build_backtesting_dataset,
)


def _validate_date_format(date_str: str) -> str:
    """Validate that date is a string in YYYY-MM-DD format."""
    if not isinstance(date_str, str):
        raise ValueError("Date must be a string in YYYY-MM-DD format.")

    date_str = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid calendar date '{date_str}'.") from exc

    return date_str


def _validate_not_future_date(date_str: str) -> None:
    """Ensure that the evaluation date is not in the future relative to the current local system date."""
    now_date = datetime.now().strftime("%Y-%m-%d")
    if date_str > now_date:
        raise ValueError(f"Evaluation date '{date_str}' is in the future. Today is {now_date}.")


def get_backtest_input(symbol: str, evaluation_date: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve historical backtesting input data for a single symbol on a single date.

    Returns:
        Dict representation of the row if available, else None.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")

    symbol_clean = symbol.strip().upper()
    if not symbol_clean:
        raise ValueError("Symbol must be a non-empty string.")

    date_clean = _validate_date_format(evaluation_date)
    _validate_not_future_date(date_clean)

    df = build_backtesting_dataset(
        symbol=symbol_clean,
        start_date=date_clean,
        end_date=date_clean,
    )

    if df is None or df.empty:
        return None

    # Extract first row as a dictionary
    return df.iloc[0].to_dict()


def get_backtest_inputs(symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Retrieve historical backtesting input data for a single symbol over a date range.

    Returns:
        List of Dict representations of the rows.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")

    symbol_clean = symbol.strip().upper()
    if not symbol_clean:
        raise ValueError("Symbol must be a non-empty string.")

    start_clean = _validate_date_format(start_date)
    end_clean = _validate_date_format(end_date)

    if start_clean > end_clean:
        raise ValueError(f"start_date '{start_clean}' cannot be after end_date '{end_clean}'.")

    _validate_not_future_date(end_clean)

    df = build_backtesting_dataset(
        symbol=symbol_clean,
        start_date=start_clean,
        end_date=end_clean,
    )

    if df is None or df.empty:
        return []

    # Return as list of dictionaries
    return df.to_dict(orient="records")
