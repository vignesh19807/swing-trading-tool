"""
Indian Equities Transaction Cost & Slippage Model
=================================================

Calculates realistic execution friction and regulatory charges for Indian equity delivery trading:
- Brokerage: configurable (flat, percentage, or zero delivery model)
- Securities Transaction Tax (STT): 0.1% on buy and 0.1% on sell turnover
- Exchange Transaction Charges (NSE): ~0.00297%
- SEBI Turnover Fee: 0.0001% (₹10 per crore)
- Stamp Duty: 0.015% on buy turnover only
- Goods and Services Tax (GST): 18% on (Brokerage + Exchange + SEBI charges)
- Slippage: percentage adjustment on execution prices
"""

from typing import Dict
from backend.logic.backtest_specification import CostModelConfig


def apply_slippage(price: float, is_buy: bool, slippage_pct: float = 0.0005) -> float:
    """
    Applies slippage penalty to execution price:
    - Long entry (Buy): execution price increases (adverse slippage)
    - Long exit (Sell): execution price decreases (adverse slippage)
    """
    if price <= 0 or slippage_pct <= 0:
        return round(price, 4)
    multiplier = (1.0 + slippage_pct) if is_buy else (1.0 - slippage_pct)
    return round(price * multiplier, 4)


def calculate_trade_costs(
    price: float,
    quantity: int,
    is_buy: bool,
    config: CostModelConfig = None
) -> Dict[str, float]:
    """
    Computes statutory and broker charges for an equity delivery trade in Indian markets.

    Parameters
    ----------
    price : float
        Actual execution price per share.
    quantity : int
        Number of whole shares.
    is_buy : bool
        True if entry (buy), False if exit (sell).
    config : CostModelConfig, optional
        Cost rates and assumptions.

    Returns
    -------
    dict
        Itemized and total trading charges.
    """
    cfg = config or CostModelConfig()
    if price <= 0 or quantity <= 0:
        return {
            "turnover": 0.0,
            "brokerage": 0.0,
            "stt": 0.0,
            "exchange_charges": 0.0,
            "sebi_charges": 0.0,
            "stamp_duty": 0.0,
            "gst": 0.0,
            "total_costs": 0.0
        }

    turnover = round(price * quantity, 4)

    # 1. Brokerage
    if cfg.brokerage_pct > 0:
        raw_brokerage = turnover * cfg.brokerage_pct
        brokerage = min(cfg.max_brokerage, raw_brokerage) if cfg.max_brokerage > 0 else raw_brokerage
    else:
        brokerage = cfg.brokerage_flat

    # 2. STT (0.1% buy, 0.1% sell for delivery)
    stt_rate = cfg.stt_rate_buy if is_buy else cfg.stt_rate_sell
    stt = round(turnover * stt_rate, 4)

    # 3. Exchange transaction charges (NSE delivery ~0.00297%)
    exchange_charges = round(turnover * cfg.exchange_rate, 4)

    # 4. SEBI turnover fee (₹10/crore = 0.0001%)
    sebi_charges = round(turnover * cfg.sebi_rate, 4)

    # 5. Stamp duty (0.015% on buy only)
    stamp_duty_rate = cfg.stamp_duty_buy if is_buy else cfg.stamp_duty_sell
    stamp_duty = round(turnover * stamp_duty_rate, 4)

    # 6. GST (18% on Brokerage + Exchange + SEBI charges)
    gst_base = brokerage + exchange_charges + sebi_charges
    gst = round(gst_base * cfg.gst_rate, 4)

    total_costs = round(brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst, 4)

    return {
        "turnover": turnover,
        "brokerage": round(brokerage, 4),
        "stt": stt,
        "exchange_charges": exchange_charges,
        "sebi_charges": sebi_charges,
        "stamp_duty": stamp_duty,
        "gst": gst,
        "total_costs": total_costs
    }
