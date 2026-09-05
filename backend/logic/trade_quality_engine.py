"""
Week 10 - Trade Quality Engine

Provides a deterministic eligibility layer for trade setups based purely on
the existing final signal contract.
"""

from typing import Any, Dict, Optional

def evaluate_trade_eligibility(signal_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates whether a generated trade setup is eligible according to
    existing approved project rules, and generates structured risk flags and decision context.

    Does not modify Decision Engine scores or calculate new thresholds.

    Parameters
    ----------
    signal_payload : dict
        The final signal dictionary produced by the Signal Engine.

    Returns
    -------
    dict
        A dictionary containing:
        - is_eligible: bool
        - risk_status: str ("ELIGIBLE", "INELIGIBLE", "INVALID", "INCOMPLETE")
        - eligibility_reason: str
        - risk_flags: list[str]
        - signal_reason: str | None
        - missing_inputs: list[str]
    """
    if not isinstance(signal_payload, dict):
        return {
            "is_eligible": False,
            "risk_status": "INVALID",
            "eligibility_reason": "INVALID_PAYLOAD",
            "risk_flags": ["INVALID_PAYLOAD"],
            "signal_reason": None,
            "missing_inputs": []
        }

    recommendation = signal_payload.get("recommendation")
    signal_valid = signal_payload.get("signal_valid", False)
    signal_reason = signal_payload.get("reason")
    missing_inputs = list(signal_payload.get("missing_inputs", []))

    # 1. Non-BUY Recommendation
    if recommendation != "BUY":
        return {
            "is_eligible": False,
            "risk_status": "INELIGIBLE",
            "eligibility_reason": "NOT_A_BUY_RECOMMENDATION",
            "risk_flags": ["NON_BUY_RECOMMENDATION"],
            "signal_reason": signal_reason,
            "missing_inputs": missing_inputs
        }

    # 2. Signal Invalid (Evaluate underlying reason)
    if not signal_valid:
        reason = signal_reason if signal_reason else "SIGNAL_INVALID"

        # Categorize by exact authoritative signal reason
        if reason == "MISSING_OR_INVALID_INPUTS":
            risk_status = "INCOMPLETE"
            eligibility_reason = "MISSING_OR_INVALID_INPUTS"
            risk_flags = ["MISSING_INPUTS"]
        elif reason == "INSUFFICIENT_RISK_REWARD_RATIO":
            risk_status = "INELIGIBLE"
            eligibility_reason = "INSUFFICIENT_RISK_REWARD_RATIO"
            risk_flags = ["INSUFFICIENT_RISK_REWARD"]
        elif reason == "PRICE_OUTSIDE_ENTRY_ZONE":
            risk_status = "INELIGIBLE"
            eligibility_reason = "PRICE_OUTSIDE_ENTRY_ZONE"
            risk_flags = ["INVALID_ENTRY"]
        elif reason in ["STOP_ABOVE_CURRENT_PRICE", "INVALID_STRUCTURAL_STOP"]:
            risk_status = "INVALID"
            eligibility_reason = reason
            risk_flags = ["INVALID_STOP"]
        elif reason in ["TARGET_BELOW_CURRENT_PRICE", "TARGET_BELOW_ENTRY_PRICE"]:
            risk_status = "INVALID"
            eligibility_reason = reason
            risk_flags = ["INVALID_TARGET"]
        elif reason == "NON_POSITIVE_RISK":
            risk_status = "INVALID"
            eligibility_reason = "NON_POSITIVE_RISK"
            risk_flags = ["INVALID_RISK"]
        elif reason == "NON_POSITIVE_REWARD":
            risk_status = "INVALID"
            eligibility_reason = "NON_POSITIVE_REWARD"
            risk_flags = ["INVALID_REWARD"]
        elif reason == "ENTRY_BELOW_STOP_LOSS":
            risk_status = "INVALID"
            eligibility_reason = "ENTRY_BELOW_STOP_LOSS"
            risk_flags = ["INVALID_ENTRY"]
        else:
            risk_status = "INVALID"
            eligibility_reason = reason
            risk_flags = [reason]

        return {
            "is_eligible": False,
            "risk_status": risk_status,
            "eligibility_reason": eligibility_reason,
            "risk_flags": risk_flags,
            "signal_reason": signal_reason,
            "missing_inputs": missing_inputs
        }


    # 3. Eligible Setup
    return {
        "is_eligible": True,
        "risk_status": "ELIGIBLE",
        "eligibility_reason": "ELIGIBLE",
        "risk_flags": [],
        "signal_reason": signal_reason or "VALID_SIGNAL",
        "missing_inputs": missing_inputs
    }
