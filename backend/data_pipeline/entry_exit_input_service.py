"""
Week 8 - Entry / Exit Input Service

Provides standardized market and technical inputs required by
the Logic / Risk Engine for:

    - Entry-zone analysis
    - Stop-loss analysis
    - Target analysis
    - Risk/reward analysis

This service DOES NOT:
    - generate BUY/SELL signals
    - make trading decisions
    - calculate position size
    - access the database directly from the Logic/Risk Engine

Data flow:

    Data Service
         ↓
    Technical Engine
         ↓
    Entry / Exit Input Service
         ↓
    Standardized trade-setup inputs
         ↓
    Logic / Risk Engine
"""

from pathlib import Path

import pandas as pd

from backend.data_pipeline.data_service import get_stock_data
from backend.engines.technical_engine import run_technical_pipeline


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# DEFAULT LOOKBACK
# ============================================================

DEFAULT_LOOKBACK = 120


# ============================================================
# REQUIRED MARKET DATA
# ============================================================

REQUIRED_MARKET_COLUMNS = {
    "date",
    "high",
    "low",
    "close",
    "volume",
}


# ============================================================
# HELPERS
# ============================================================

def _validate_market_data(data):
    """
    Validate the OHLCV DataFrame.

    Returns
    -------
    list[str]
        Missing or invalid input descriptions.
    """

    issues = []

    if data is None:

        return ["market_data"]

    if data.empty:

        return ["market_data"]

    missing_columns = (
        REQUIRED_MARKET_COLUMNS
        - set(data.columns)
    )

    for column in sorted(missing_columns):

        issues.append(
            f"missing_market_column:{column}"
        )

    if issues:

        return issues

    # --------------------------------------------------------
    # Check required numeric fields
    # --------------------------------------------------------

    for column in [
        "high",
        "low",
        "close",
    ]:

        numeric = pd.to_numeric(
            data[column],
            errors="coerce",
        )

        if numeric.notna().sum() == 0:

            issues.append(
                f"invalid_market_data:{column}"
            )

    return issues


def _get_latest_valid_value(series):
    """
    Return the latest non-null numeric value.

    Returns None when no valid value exists.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    numeric = numeric.dropna()

    if numeric.empty:

        return None

    return float(numeric.iloc[-1])


def _get_recent_swing_level(
    support_resistance,
    level_type,
):
    """
    Return the most recent available level of the requested type.

    The Technical Engine returns deterministic support/resistance
    zones. The final row ordering is used only to select a
    representative level; no trading decision is made here.
    """

    if support_resistance is None:

        return None

    if support_resistance.empty:

        return None

    rows = support_resistance[
        support_resistance["type"] == level_type
    ]

    if rows.empty:

        return None

    # Use the strongest zone first.
    rows = rows.sort_values(
        by=[
            "strength",
            "touches",
        ],
        ascending=False,
    )

    return float(
        rows.iloc[0]["level"]
    )


def _get_support_levels(
    support_resistance,
):
    """
    Return standardized support-zone records.
    """

    if support_resistance is None:

        return []

    if support_resistance.empty:

        return []

    rows = support_resistance[
        support_resistance["type"] == "support"
    ].copy()

    if rows.empty:

        return []

    rows = rows.sort_values(
        by=[
            "strength",
            "touches",
        ],
        ascending=False,
    )

    levels = []

    for _, row in rows.iterrows():

        levels.append(
            {
                "level": float(row["level"]),
                "zone_low": float(row["zone_low"]),
                "zone_high": float(row["zone_high"]),
                "touches": int(row["touches"]),
                "strength": float(row["strength"]),
            }
        )

    return levels


def _get_resistance_levels(
    support_resistance,
):
    """
    Return standardized resistance-zone records.
    """

    if support_resistance is None:

        return []

    if support_resistance.empty:

        return []

    rows = support_resistance[
        support_resistance["type"] == "resistance"
    ].copy()

    if rows.empty:

        return []

    rows = rows.sort_values(
        by=[
            "strength",
            "touches",
        ],
        ascending=False,
    )

    levels = []

    for _, row in rows.iterrows():

        levels.append(
            {
                "level": float(row["level"]),
                "zone_low": float(row["zone_low"]),
                "zone_high": float(row["zone_high"]),
                "touches": int(row["touches"]),
                "strength": float(row["strength"]),
            }
        )

    return levels


# ============================================================
# MAIN SERVICE
# ============================================================

def get_entry_exit_inputs(
    symbol,
    lookback=DEFAULT_LOOKBACK,
):
    """
    Return standardized entry/exit inputs for one stock.

    Parameters
    ----------
    symbol : str
        NSE stock symbol.

    lookback : int
        Number of recent OHLCV records used for recent
        price-range and support/resistance analysis.

    Returns
    -------
    dict
        Standardized trade-setup input contract.

    The service never invents missing values.
    Missing values are returned as None and listed in
    `missing_inputs`.
    """

    symbol = symbol.upper().strip()

    # --------------------------------------------------------
    # Validate lookback
    # --------------------------------------------------------

    if not isinstance(
        lookback,
        int,
    ) or isinstance(
        lookback,
        bool,
    ):

        raise TypeError(
            "lookback must be an integer"
        )

    if lookback < 1:

        raise ValueError(
            "lookback must be >= 1"
        )

    # --------------------------------------------------------
    # Load historical OHLCV
    # --------------------------------------------------------

    market_data = get_stock_data(
        symbol
    )

    base_result = {
        "symbol": symbol,
        "timestamp": None,
        "current_price": None,
        "recent_high": None,
        "recent_low": None,
        "swing_high": None,
        "swing_low": None,
        "atr_14": None,
        "support_levels": [],
        "resistance_levels": [],
        "data_quality": "INVALID",
        "missing_inputs": [],
        "source": {
            "market_data": "daily_prices via data_service",
            "technical_data": "technical_engine",
            "atr": "technical_engine.calculate_atr",
            "support_resistance": (
                "technical_engine.calculate_support_resistance"
            ),
        },
    }

    # --------------------------------------------------------
    # Validate OHLCV
    # --------------------------------------------------------

    issues = _validate_market_data(
        market_data
    )

    if issues:

        base_result["missing_inputs"] = issues

        return base_result

    # --------------------------------------------------------
    # Standardize chronological order
    # --------------------------------------------------------

    market_data = market_data.copy()

    market_data["date"] = pd.to_datetime(
        market_data["date"],
        errors="coerce",
    )

    market_data = market_data.sort_values(
        "date"
    ).reset_index(drop=True)

    # Remove rows where date is invalid.
    market_data = market_data[
        market_data["date"].notna()
    ].copy()

    if market_data.empty:

        base_result["missing_inputs"] = [
            "valid_timestamp"
        ]

        return base_result

    # --------------------------------------------------------
    # Recent market window
    # --------------------------------------------------------

    recent_data = market_data.tail(
        lookback
    ).copy()

    # --------------------------------------------------------
    # Current price
    # --------------------------------------------------------

    current_price = _get_latest_valid_value(
        recent_data["close"]
    )

    if current_price is None:

        base_result["missing_inputs"].append(
            "current_price"
        )

    else:

        base_result["current_price"] = (
            current_price
        )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    latest_timestamp = recent_data[
        "date"
    ].iloc[-1]

    if pd.isna(latest_timestamp):

        base_result["missing_inputs"].append(
            "timestamp"
        )

    else:

        base_result["timestamp"] = (
            latest_timestamp.isoformat()
        )

    # --------------------------------------------------------
    # Recent high / low
    # --------------------------------------------------------

    recent_high_series = pd.to_numeric(
        recent_data["high"],
        errors="coerce",
    ).dropna()

    recent_low_series = pd.to_numeric(
        recent_data["low"],
        errors="coerce",
    ).dropna()

    if recent_high_series.empty:

        base_result["missing_inputs"].append(
            "recent_high"
        )

    else:

        base_result["recent_high"] = float(
            recent_high_series.max()
        )

    if recent_low_series.empty:

        base_result["missing_inputs"].append(
            "recent_low"
        )

    else:

        base_result["recent_low"] = float(
            recent_low_series.min()
        )

    # --------------------------------------------------------
    # Technical Engine
    # --------------------------------------------------------

    try:

        technical_result = run_technical_pipeline(
            recent_data
        )

    except Exception as error:

        base_result["missing_inputs"].append(
            f"technical_engine_error:{error}"
        )

        return base_result

    indicators = technical_result.get(
        "indicators"
    )

    support_resistance = technical_result.get(
        "support_resistance"
    )

    # --------------------------------------------------------
    # ATR-14
    # --------------------------------------------------------

    if indicators is not None and not indicators.empty:

        atr14 = _get_latest_valid_value(
            indicators["atr14"]
        )

        if atr14 is None:

            base_result["missing_inputs"].append(
                "atr_14"
            )

        else:

            base_result["atr_14"] = atr14

    else:

        base_result["missing_inputs"].append(
            "technical_indicators"
        )

    # --------------------------------------------------------
    # Support / Resistance
    # --------------------------------------------------------

    support_levels = _get_support_levels(
        support_resistance
    )

    resistance_levels = _get_resistance_levels(
        support_resistance
    )

    base_result["support_levels"] = (
        support_levels
    )

    base_result["resistance_levels"] = (
        resistance_levels
    )

    # --------------------------------------------------------
    # Representative swing levels
    # --------------------------------------------------------

    swing_low = _get_recent_swing_level(
        support_resistance,
        "support",
    )

    swing_high = _get_recent_swing_level(
        support_resistance,
        "resistance",
    )

    base_result["swing_low"] = swing_low
    base_result["swing_high"] = swing_high

    if swing_low is None:

        base_result["missing_inputs"].append(
            "swing_low"
        )

    if swing_high is None:

        base_result["missing_inputs"].append(
            "swing_high"
        )

    # --------------------------------------------------------
    # Support / resistance availability
    # --------------------------------------------------------

    if not support_levels:

        base_result["missing_inputs"].append(
            "support_levels"
        )

    if not resistance_levels:

        base_result["missing_inputs"].append(
            "resistance_levels"
        )

    # --------------------------------------------------------
    # Final data-quality status
    # --------------------------------------------------------

    if not base_result["missing_inputs"]:

        base_result["data_quality"] = "VALID"

    else:

        base_result["data_quality"] = "INCOMPLETE"

    return base_result


# ============================================================
# MULTI-STOCK SERVICE
# ============================================================

def get_entry_exit_inputs_for_stocks(
    symbols,
    lookback=DEFAULT_LOOKBACK,
):
    """
    Return standardized entry/exit inputs for multiple stocks.

    Each stock is processed independently.
    One failure does not stop the remaining stocks.
    """

    results = []

    for symbol in symbols:

        try:

            result = get_entry_exit_inputs(
                symbol,
                lookback=lookback,
            )

        except Exception as error:

            result = {
                "symbol": symbol.upper().strip(),
                "timestamp": None,
                "current_price": None,
                "recent_high": None,
                "recent_low": None,
                "swing_high": None,
                "swing_low": None,
                "atr_14": None,
                "support_levels": [],
                "resistance_levels": [],
                "data_quality": "INVALID",
                "missing_inputs": [
                    f"service_error:{error}"
                ],
                "source": {},
            }

        results.append(
            result
        )

    return results


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - ENTRY / EXIT INPUT SERVICE")
    print("=" * 60)

    symbol = "INFY"

    print(
        f"\nProcessing {symbol}..."
    )

    result = get_entry_exit_inputs(
        symbol
    )

    print(
        "\nSTANDARDIZED ENTRY / EXIT INPUTS"
    )

    print("-" * 50)

    print(
        f"Symbol          : {result['symbol']}"
    )

    print(
        f"Timestamp       : {result['timestamp']}"
    )

    print(
        f"Current price   : {result['current_price']}"
    )

    print(
        f"Recent high     : {result['recent_high']}"
    )

    print(
        f"Recent low      : {result['recent_low']}"
    )

    print(
        f"Swing high      : {result['swing_high']}"
    )

    print(
        f"Swing low       : {result['swing_low']}"
    )

    print(
        f"ATR-14          : {result['atr_14']}"
    )

    print(
        f"Support levels  : {len(result['support_levels'])}"
    )

    print(
        f"Resistance lvls : "
        f"{len(result['resistance_levels'])}"
    )

    print(
        f"Data quality    : {result['data_quality']}"
    )

    print(
        f"Missing inputs  : {result['missing_inputs']}"
    )

    print(
        "\nSupport levels:"
    )

    for level in result["support_levels"][:5]:

        print(
            f"  {level}"
        )

    print(
        "\nResistance levels:"
    )

    for level in result["resistance_levels"][:5]:

        print(
            f"  {level}"
        )

    print(
        "\n" + "=" * 60
    )

    if result["data_quality"] == "VALID":

        print(
            "✓ ENTRY / EXIT INPUT SERVICE PASSED"
        )

    else:

        print(
            "⚠ ENTRY / EXIT INPUT SERVICE "
            "RETURNED INCOMPLETE DATA"
        )

    print("=" * 60)


if __name__ == "__main__":

    main()