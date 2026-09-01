"""
Signal Engine V1 (Engine 8)
===========================

Calculates explicit trading signals based on the Week 8 Rules Specification.
Currently implements Tuesday's scope: Pullback-to-Support Entry Zone.

Author: Logic Engineer
"""

from typing import Any, Dict, Optional

# Approved V1 Parameters
ENTRY_MULTIPLIER = 0.50
STOP_MULTIPLIER = 1.50
TARGET_MULTIPLIER = 2.00
MIN_RISK_REWARD_RATIO = 1.50


def calculate_entry_zone(
    current_price: Optional[float],
    nearest_support: Optional[Dict[str, Any]],
    atr_14: Optional[float],
    recommendation: Optional[str]
) -> Dict[str, Any]:
    """
    Calculate the Pullback-to-Support entry zone deterministically.

    Parameters
    ----------
    current_price : float
        The current valid stock price.
    nearest_support : dict
        A dictionary containing at minimum a "level" key (float).
    atr_14 : float
        The 14-day Average True Range. Must be > 0.
    recommendation : str
        The Decision Engine recommendation (e.g., "BUY").

    Returns
    -------
    dict
        Structured entry-zone result:
        {
            "entry_valid": bool,
            "entry_lower": float | None,
            "entry_upper": float | None,
            "current_price": float | None,
            "support_level": float | None,
            "atr_14": float | None,
            "reason": str | None,
            "missing_inputs": list[str]
        }
    """
    result = {
        "entry_valid": False,
        "entry_lower": None,
        "entry_upper": None,
        "current_price": current_price,
        "support_level": None,
        "atr_14": atr_14,
        "reason": None,
        "missing_inputs": []
    }

    # Input Validation
    missing = []

    # 1. Price
    if current_price is None:
        missing.append("current_price")

    # 2. ATR
    if atr_14 is None:
        missing.append("atr_14")
    elif atr_14 <= 0:
        # Invalid ATR
        missing.append("invalid_atr_14")

    # 3. Support
    support_level = None
    if nearest_support is None:
        missing.append("nearest_support")
    elif "level" not in nearest_support or nearest_support["level"] is None:
        missing.append("nearest_support_level")
    else:
        try:
            support_level = float(nearest_support["level"])
            result["support_level"] = support_level
        except (ValueError, TypeError):
            missing.append("invalid_support_level")

    # 4. Recommendation
    if recommendation is None:
        missing.append("recommendation")

    if missing:
        result["missing_inputs"] = missing
        result["reason"] = "MISSING_OR_INVALID_INPUTS"
        return result

    # All inputs valid, calculate zone
    lower_bound = support_level
    upper_bound = support_level + (atr_14 * ENTRY_MULTIPLIER)

    result["entry_lower"] = round(lower_bound, 4)
    result["entry_upper"] = round(upper_bound, 4)

    # Check Eligibility
    if recommendation != "BUY":
        result["reason"] = "NOT_A_BUY_RECOMMENDATION"
        return result

    if not (lower_bound <= current_price <= upper_bound):
        result["reason"] = "PRICE_OUTSIDE_ENTRY_ZONE"
        return result

    # Valid Entry
    result["entry_valid"] = True
    result["reason"] = "VALID_PULLBACK_ENTRY"

    return result


def calculate_exit_parameters(
    current_price: Optional[float],
    nearest_support: Optional[Dict[str, Any]],
    nearest_resistance: Optional[Dict[str, Any]],
    atr_14: Optional[float],
    entry_price: Optional[float]
) -> Dict[str, Any]:
    """
    Calculate stop-loss and target parameters deterministically.

    Parameters
    ----------
    current_price : float
        The current valid stock price.
    nearest_support : dict
        A dictionary containing "zone_low" key (float).
    nearest_resistance : dict
        A dictionary containing "zone_low" key (float).
    atr_14 : float
        The 14-day Average True Range. Must be > 0.
    entry_price : float
        The calculated entry price or upper bound of entry zone.

    Returns
    -------
    dict
        Structured stop/target result:
        {
            "exit_valid": bool,
            "stop_loss": float | None,
            "target": float | None,
            "risk": float | None,
            "reward": float | None,
            "reason": str | None,
            "missing_inputs": list[str]
        }
    """
    result = {
        "exit_valid": False,
        "stop_loss": None,
        "target": None,
        "risk": None,
        "reward": None,
        "reason": None,
        "missing_inputs": []
    }

    missing = []

    if current_price is None:
        missing.append("current_price")

    if atr_14 is None:
        missing.append("atr_14")
    elif atr_14 <= 0:
        missing.append("invalid_atr_14")

    if entry_price is None:
        missing.append("entry_price")

    if missing:
        result["missing_inputs"] = missing
        result["reason"] = "MISSING_OR_INVALID_INPUTS"
        return result

    # 1. Stop Loss Calculation
    support_zone_low = None
    if nearest_support and "zone_low" in nearest_support and nearest_support["zone_low"] is not None:
        try:
            support_zone_low = float(nearest_support["zone_low"])
        except (ValueError, TypeError):
            pass  # Fallback to ATR stop

    if support_zone_low is not None:
        stop_loss = support_zone_low - (atr_14 * STOP_MULTIPLIER)
        # Structural check
        if stop_loss >= support_zone_low:
            result["missing_inputs"].append("invalid_stop_vs_support")
            result["reason"] = "INVALID_STRUCTURAL_STOP"
            return result
    else:
        stop_loss = current_price - (atr_14 * STOP_MULTIPLIER)

    # Validate Stop Loss vs Current Price
    if stop_loss >= current_price:
        result["missing_inputs"].append("stop_above_price")
        result["reason"] = "STOP_ABOVE_CURRENT_PRICE"
        return result

    result["stop_loss"] = round(stop_loss, 4)

    # 2. Target Calculation
    resistance_zone_low = None
    if nearest_resistance and "zone_low" in nearest_resistance and nearest_resistance["zone_low"] is not None:
        try:
            resistance_zone_low = float(nearest_resistance["zone_low"])
        except (ValueError, TypeError):
            pass

    if resistance_zone_low is not None:
        target = resistance_zone_low
    else:
        target = current_price + (atr_14 * TARGET_MULTIPLIER)

    # Validate Target vs Current Price and Entry
    if target <= current_price:
        result["missing_inputs"].append("target_below_price")
        result["reason"] = "TARGET_BELOW_CURRENT_PRICE"
        return result

    if target <= entry_price:
        result["missing_inputs"].append("target_below_entry")
        result["reason"] = "TARGET_BELOW_ENTRY_PRICE"
        return result

    result["target"] = round(target, 4)

    # 3. Validation and Risk/Reward
    risk = current_price - stop_loss
    reward = target - current_price

    if risk <= 0:
        result["missing_inputs"].append("non_positive_risk")
        result["reason"] = "NON_POSITIVE_RISK"
        return result

    if reward <= 0:
        result["missing_inputs"].append("non_positive_reward")
        result["reason"] = "NON_POSITIVE_REWARD"
        return result

    if entry_price <= stop_loss:
        result["missing_inputs"].append("entry_below_stop")
        result["reason"] = "ENTRY_BELOW_STOP_LOSS"
        return result

    result["risk"] = round(risk, 4)
    result["reward"] = round(reward, 4)

    result["exit_valid"] = True
    result["reason"] = "VALID_EXIT_PARAMETERS"

    return result


def generate_final_signal(
    current_price: Optional[float],
    nearest_support: Optional[Dict[str, Any]],
    nearest_resistance: Optional[Dict[str, Any]],
    atr_14: Optional[float],
    recommendation: Optional[str]
) -> Dict[str, Any]:
    """
    Generate the final structured trading signal based on entry, exit, and risk rules.

    Parameters
    ----------
    current_price : float
    nearest_support : dict
    nearest_resistance : dict
    atr_14 : float
    recommendation : str

    Returns
    -------
    dict
        Structured signal result:
        {
            "signal_valid": bool,
            "entry_lower": float | None,
            "entry_upper": float | None,
            "stop_loss": float | None,
            "target": float | None,
            "risk": float | None,
            "reward": float | None,
            "risk_reward_ratio": float | None,
            "reason": str | None,
            "missing_inputs": list[str]
        }
    """
    result = {
        "signal_valid": False,
        "entry_lower": None,
        "entry_upper": None,
        "stop_loss": None,
        "target": None,
        "risk": None,
        "reward": None,
        "risk_reward_ratio": None,
        "reason": None,
        "missing_inputs": []
    }

    # 1. Entry Zone Validation
    entry_result = calculate_entry_zone(current_price, nearest_support, atr_14, recommendation)

    result["entry_lower"] = entry_result.get("entry_lower")
    result["entry_upper"] = entry_result.get("entry_upper")

    if not entry_result["entry_valid"]:
        result["reason"] = entry_result.get("reason")
        result["missing_inputs"] = entry_result.get("missing_inputs", [])
        return result

    # 2. Exit Parameters Validation
    # Use entry_upper as the entry_price to ensure target is strictly above the highest entry
    exit_result = calculate_exit_parameters(
        current_price, nearest_support, nearest_resistance, atr_14, entry_result["entry_upper"]
    )

    result["stop_loss"] = exit_result.get("stop_loss")
    result["target"] = exit_result.get("target")
    result["risk"] = exit_result.get("risk")
    result["reward"] = exit_result.get("reward")

    if not exit_result["exit_valid"]:
        result["reason"] = exit_result.get("reason")
        missing_inputs = exit_result.get("missing_inputs", [])
        for m in missing_inputs:
            if m not in result["missing_inputs"]:
                result["missing_inputs"].append(m)
        return result

    # 3. Risk/Reward Ratio Validation
    risk = exit_result["risk"]
    reward = exit_result["reward"]

    # Double check positive risk/reward (already checked by calculate_exit_parameters but explicit here per checklist)
    if risk <= 0:
        result["reason"] = "NON_POSITIVE_RISK"
        result["missing_inputs"].append("invalid_risk")
        return result

    if reward <= 0:
        result["reason"] = "NON_POSITIVE_REWARD"
        result["missing_inputs"].append("invalid_reward")
        return result

    risk_reward_ratio = reward / risk
    result["risk_reward_ratio"] = round(risk_reward_ratio, 4)

    if risk_reward_ratio < MIN_RISK_REWARD_RATIO:
        result["reason"] = "INSUFFICIENT_RISK_REWARD_RATIO"
        return result

    # 4. Final Signal Validation
    result["signal_valid"] = True
    result["reason"] = "VALID_SIGNAL"
    return result
