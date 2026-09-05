"""
Week 11 - Unified Stock Snapshot Service
========================================

Purpose:
    Combine validated Data Engineering datasets into one consistent
    stock-level snapshot for downstream consumers.

Data sources:
    - Market data via Data Service
    - Latest financial data via Financial Data Service
    - Company / sector / industry via Classification Service

This service does NOT:
    - calculate technical scores
    - calculate financial scores
    - calculate opportunity scores
    - generate BUY/SELL decisions

Missing source data is preserved explicitly.
"""

from typing import Any, Dict, Optional
import datetime

from backend.data_pipeline.data_service import (
    get_latest_price,
)
from backend.data_pipeline.financial_service import (
    get_latest_financial_data,
)
from backend.data_pipeline.classification_service import (
    get_company_classification,
)


def _normalize_symbol(symbol: str) -> str:
    """Normalize a stock symbol safely."""
    if not isinstance(symbol, str):
        return ""

    return symbol.strip().upper()


def _validate_evaluation_date(date_str: str) -> None:
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid evaluation_date format: {date_str}. Expected YYYY-MM-DD.")


def get_stock_snapshot(symbol: str, evaluation_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Return a unified validated-data snapshot for one stock.

    Parameters
    ----------
    symbol : str
        NSE stock symbol without .NS.
        
    evaluation_date : str, optional
        Construct snapshot using data available at or before this date (YYYY-MM-DD).

    Returns
    -------
    dict
        Consistent snapshot containing:

        symbol
        identity
        market
        financial
        data_quality
        source

    No trading decision or score is generated.
    """

    symbol = _normalize_symbol(symbol)

    if evaluation_date is not None:
        _validate_evaluation_date(evaluation_date)

    # --------------------------------------------------------
    # Invalid symbol
    # --------------------------------------------------------

    if not symbol:
        return {
            "symbol": symbol,
            "status": "INVALID",
            "identity": None,
            "market": None,
            "financial": None,
            "data_quality": {
                "status": "INVALID",
                "warnings": ["Invalid stock symbol"],
            },
            "source": {},
        }

    # --------------------------------------------------------
    # Identity / classification
    # --------------------------------------------------------

    identity = None

    try:
        identity = get_company_classification(symbol)
    except Exception:
        identity = None

    # --------------------------------------------------------
    # Latest market data
    # --------------------------------------------------------

    market = None

    try:
        latest_price = get_latest_price(symbol, evaluation_date=evaluation_date)

        if latest_price is not None:
            market = latest_price

    except Exception:
        market = None

    # --------------------------------------------------------
    # Latest financial data
    # --------------------------------------------------------

    financial = None

    try:
        financial = get_latest_financial_data(symbol, evaluation_date=evaluation_date)
        if isinstance(financial, dict):
            import pandas as pd
            financial = {k: (None if pd.isna(v) else v) for k, v in financial.items()}
    except Exception:
        financial = None

    # --------------------------------------------------------
    # Determine component availability
    # --------------------------------------------------------

    warnings = []

    if identity is None:
        warnings.append(
            "Company classification unavailable"
        )

    if market is None:
        warnings.append(
            "Latest market data unavailable"
        )

    if financial is None:
        warnings.append(
            "Latest financial data unavailable"
        )

    # --------------------------------------------------------
    # Detect missing fields without replacing them
    # --------------------------------------------------------

    financial_missing_fields = []

    if isinstance(financial, dict):

        financial_fields = [
            "revenue",
            "net_profit",
            "eps",
            "roe",
            "roce",
            "debt_equity",
            "operating_margin",
            "net_margin",
        ]

        for field in financial_fields:

            value = financial.get(field)

            if value is None:

                financial_missing_fields.append(field)

            else:
                try:
                    if value != value:
                        financial_missing_fields.append(field)
                except Exception:
                    pass

    if financial_missing_fields:

        warnings.append(
            "Missing financial fields: "
            + ", ".join(financial_missing_fields)
        )

    # --------------------------------------------------------
    # Overall snapshot status
    # --------------------------------------------------------

    if identity is None or market is None:

        status = "INCOMPLETE"

    elif financial is None:

        status = "PARTIAL"

    elif financial_missing_fields:

        status = "PARTIAL"

    else:

        status = "VALID"

    # --------------------------------------------------------
    # Source traceability
    # --------------------------------------------------------

    source = {
        "identity": "classification_service",
        "market": "data_service",
        "financial": "financial_service",
    }

    # --------------------------------------------------------
    # Return unified snapshot
    # --------------------------------------------------------

    return {
        "symbol": symbol,

        "status": status,

        "identity": identity,

        "market": market,

        "financial": financial,

        "data_quality": {
            "status": status,
            "warnings": warnings,
            "financial_missing_fields":
                financial_missing_fields,
        },

        "source": source,
    }


if __name__ == "__main__":

    import pprint

    for stock in [
        "INFY",
        "TCS",
        "WIPRO",
        "RELIANCE",
        "HDFCBANK",
    ]:

        print("\n" + "=" * 60)
        print(stock)
        print("=" * 60)

        pprint.pp(
            get_stock_snapshot(stock)
        )