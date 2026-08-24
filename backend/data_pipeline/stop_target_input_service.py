"""
Week 8 - Stop / Target Input Service

Provides standardized market-derived inputs for downstream
stop-loss, target, and risk/reward logic.

IMPORTANT:
This service does NOT generate BUY/SELL decisions.
It only prepares measurable inputs for the Logic/Risk Engine.

Data flow:

    Entry/Exit Input Service
             ↓
    Stop/Target Input Service
             ↓
    Logic/Risk Engine
"""

from backend.data_pipeline.entry_exit_input_service import (
    get_entry_exit_inputs,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_ATR_MULTIPLIER = 1.5


# ============================================================
# HELPERS
# ============================================================

def _select_nearest_support(
    current_price,
    support_levels,
):
    """
    Select the strongest support below the current price.

    Returns None if no valid support exists below price.
    """

    if current_price is None:
        return None

    candidates = [
        level
        for level in support_levels
        if level["level"] < current_price
    ]

    if not candidates:
        return None

    # Prefer the nearest valid support below price.
    candidates.sort(
        key=lambda level: (
            current_price - level["level"],
            -level["strength"],
        )
    )

    return candidates[0]


def _select_nearest_resistance(
    current_price,
    resistance_levels,
):
    """
    Select the nearest resistance above the current price.

    Returns None if no valid resistance exists above price.
    """

    if current_price is None:
        return None

    candidates = [
        level
        for level in resistance_levels
        if level["level"] > current_price
    ]

    if not candidates:
        return None

    # Prefer the nearest valid resistance above price.
    candidates.sort(
        key=lambda level: (
            level["level"] - current_price,
            -level["strength"],
        )
    )

    return candidates[0]


# ============================================================
# MAIN SERVICE
# ============================================================

def get_stop_target_inputs(
    symbol,
    lookback=120,
    atr_multiplier=DEFAULT_ATR_MULTIPLIER,
):
    """
    Return standardized stop/target inputs.

    Parameters
    ----------
    symbol : str
        Stock symbol.

    lookback : int
        Historical lookback used by the Entry/Exit service.

    atr_multiplier : float
        ATR distance multiplier used only to calculate an
        ATR-based reference level.

    Returns
    -------
    dict

    No BUY/SELL decision is produced.

    The Logic/Risk Engine remains responsible for deciding
    which stop/target methodology is appropriate.
    """

    if not isinstance(
        atr_multiplier,
        (int, float),
    ) or isinstance(
        atr_multiplier,
        bool,
    ):
        raise TypeError(
            "atr_multiplier must be numeric"
        )

    if atr_multiplier <= 0:
        raise ValueError(
            "atr_multiplier must be greater than 0"
        )

    entry_inputs = get_entry_exit_inputs(
        symbol,
        lookback=lookback,
    )

    result = {
        "symbol": entry_inputs["symbol"],
        "timestamp": entry_inputs["timestamp"],
        "current_price": entry_inputs["current_price"],

        # Market-derived levels
        "atr_14": entry_inputs["atr_14"],
        "swing_high": entry_inputs["swing_high"],
        "swing_low": entry_inputs["swing_low"],

        # Existing zones
        "support_levels": entry_inputs[
            "support_levels"
        ],
        "resistance_levels": entry_inputs[
            "resistance_levels"
        ],

        # Selected reference levels
        "nearest_support": None,
        "nearest_resistance": None,

        # ATR-based reference
        "atr_multiplier": float(
            atr_multiplier
        ),
        "atr_stop_distance": None,
        "atr_stop_reference": None,

        # Risk/reward inputs
        "risk_distance_to_support": None,
        "reward_distance_to_resistance": None,

        "data_quality": "INVALID",
        "missing_inputs": [],

        "decision": None,

        "source": {
            "entry_exit_inputs": (
                "entry_exit_input_service"
            ),
            "atr": (
                "technical_engine.calculate_atr"
            ),
            "support_resistance": (
                "technical_engine.calculate_support_resistance"
            ),
        },
    }

    # --------------------------------------------------------
    # Validate upstream contract
    # --------------------------------------------------------

    if entry_inputs["data_quality"] != "VALID":

        result["data_quality"] = "INCOMPLETE"

        result["missing_inputs"].extend(
            entry_inputs["missing_inputs"]
        )

        return result

    current_price = result[
        "current_price"
    ]

    atr14 = result[
        "atr_14"
    ]

    supports = result[
        "support_levels"
    ]

    resistances = result[
        "resistance_levels"
    ]

    # --------------------------------------------------------
    # Current price
    # --------------------------------------------------------

    if current_price is None:

        result["missing_inputs"].append(
            "current_price"
        )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    if atr14 is None:

        result["missing_inputs"].append(
            "atr_14"
        )

    elif atr14 <= 0:

        result["missing_inputs"].append(
            "invalid_atr_14"
        )

    # --------------------------------------------------------
    # Support
    # --------------------------------------------------------

    nearest_support = (
        _select_nearest_support(
            current_price,
            supports,
        )
    )

    result["nearest_support"] = (
        nearest_support
    )

    if nearest_support is None:

        result["missing_inputs"].append(
            "nearest_support"
        )

    # --------------------------------------------------------
    # Resistance
    # --------------------------------------------------------

    nearest_resistance = (
        _select_nearest_resistance(
            current_price,
            resistances,
        )
    )

    result["nearest_resistance"] = (
        nearest_resistance
    )

    if nearest_resistance is None:

        result["missing_inputs"].append(
            "nearest_resistance"
        )

    # --------------------------------------------------------
    # ATR stop reference
    # --------------------------------------------------------

    if (
        current_price is not None
        and atr14 is not None
        and atr14 > 0
    ):

        atr_distance = (
            atr14
            * atr_multiplier
        )

        result[
            "atr_stop_distance"
        ] = float(atr_distance)

        result[
            "atr_stop_reference"
        ] = float(
            current_price
            - atr_distance
        )

    else:

        result["missing_inputs"].append(
            "atr_stop_reference"
        )

    # --------------------------------------------------------
    # Support risk distance
    # --------------------------------------------------------

    if (
        current_price is not None
        and nearest_support is not None
    ):

        support_price = (
            nearest_support["level"]
        )

        result[
            "risk_distance_to_support"
        ] = float(
            current_price
            - support_price
        )

    # --------------------------------------------------------
    # Resistance reward distance
    # --------------------------------------------------------

    if (
        current_price is not None
        and nearest_resistance is not None
    ):

        resistance_price = (
            nearest_resistance["level"]
        )

        result[
            "reward_distance_to_resistance"
        ] = float(
            resistance_price
            - current_price
        )

    # --------------------------------------------------------
    # Data quality
    # --------------------------------------------------------

    if not result["missing_inputs"]:

        result["data_quality"] = "VALID"

    else:

        result["data_quality"] = "INCOMPLETE"

    return result


# ============================================================
# MULTI-STOCK SERVICE
# ============================================================

def get_stop_target_inputs_for_stocks(
    symbols,
    lookback=120,
    atr_multiplier=DEFAULT_ATR_MULTIPLIER,
):
    """
    Process multiple stocks independently.

    One stock failure does not stop the remaining stocks.
    """

    results = []

    for symbol in symbols:

        try:

            result = get_stop_target_inputs(
                symbol,
                lookback=lookback,
                atr_multiplier=atr_multiplier,
            )

        except Exception as error:

            result = {
                "symbol": symbol.upper().strip(),
                "timestamp": None,
                "current_price": None,
                "atr_14": None,
                "swing_high": None,
                "swing_low": None,
                "support_levels": [],
                "resistance_levels": [],
                "nearest_support": None,
                "nearest_resistance": None,
                "atr_multiplier": float(
                    atr_multiplier
                ),
                "atr_stop_distance": None,
                "atr_stop_reference": None,
                "risk_distance_to_support": None,
                "reward_distance_to_resistance": None,
                "data_quality": "INVALID",
                "missing_inputs": [
                    f"service_error:{error}"
                ],
                "decision": None,
                "source": {},
            }

        results.append(result)

    return results


# ============================================================
# SERVICE TEST
# ============================================================

def main():

    print("=" * 60)
    print("SWING TRADING PLATFORM")
    print("WEEK 8 - STOP / TARGET INPUT SERVICE")
    print("=" * 60)

    symbol = "INFY"

    print(
        f"\nProcessing {symbol}..."
    )

    result = get_stop_target_inputs(
        symbol
    )

    print(
        "\nSTOP / TARGET INPUTS"
    )

    print("-" * 50)

    print(
        f"Symbol                 : "
        f"{result['symbol']}"
    )

    print(
        f"Timestamp              : "
        f"{result['timestamp']}"
    )

    print(
        f"Current price          : "
        f"{result['current_price']}"
    )

    print(
        f"ATR-14                 : "
        f"{result['atr_14']}"
    )

    print(
        f"ATR multiplier         : "
        f"{result['atr_multiplier']}"
    )

    print(
        f"ATR stop distance      : "
        f"{result['atr_stop_distance']}"
    )

    print(
        f"ATR stop reference     : "
        f"{result['atr_stop_reference']}"
    )

    print(
        f"Nearest support        : "
        f"{result['nearest_support']}"
    )

    print(
        f"Nearest resistance     : "
        f"{result['nearest_resistance']}"
    )

    print(
        f"Risk → support         : "
        f"{result['risk_distance_to_support']}"
    )

    print(
        f"Reward → resistance    : "
        f"{result['reward_distance_to_resistance']}"
    )

    print(
        f"Data quality           : "
        f"{result['data_quality']}"
    )

    print(
        f"Missing inputs         : "
        f"{result['missing_inputs']}"
    )

    print(
        f"Decision               : "
        f"{result['decision']}"
    )

    print(
        "\n" + "=" * 60
    )

    if result["data_quality"] == "VALID":

        print(
            "✓ STOP / TARGET INPUT SERVICE PASSED"
        )

        print(
            "✓ No BUY/SELL decision generated"
        )

    else:

        print(
            "⚠ STOP / TARGET INPUT SERVICE "
            "RETURNED INCOMPLETE DATA"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()