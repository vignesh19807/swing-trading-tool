"""
Week 12 - Backtest Specification & Constants
=============================================

Defines the authoritative backtesting specification, trade execution rules,
exit rules, performance metric contracts, and trade state definitions for the
Swing Trading Intelligence Platform.

Author: Logic Engineer
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# =============================================================================
# EXPLICIT TRADE SIMULATION RULES & CONSTANTS
# =============================================================================

# Trade Entry Rule:
# If a historical signal on date D is valid (signal_valid=True, is_eligible=True),
# the trade enters on date D+1 (the next available trading day).
# Entry Price P_entry = open_price of date D+1.
ENTRY_PRICE_RULE = "NEXT_DAY_OPEN"

# Exit Rules:
# For each bar t >= D+1:
# 1. Stop Loss: low_t <= stop_loss  --> Exit at min(open_t, stop_loss), reason="STOP_LOSS"
# 2. Target:    high_t >= target     --> Exit at max(open_t, target),    reason="TARGET_REACHED"
# 3. Collision: If low_t <= stop_loss AND high_t >= target on same bar:
#               STOP_LOSS wins (conservative assumption), exit at min(open_t, stop_loss), reason="STOP_LOSS".
SAME_BAR_COLLISION_RULE = "STOP_LOSS_PRIORITY"


# =============================================================================
# TRADE STATES & REASONS
# =============================================================================

class TradeState:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"


class ExitReason:
    STOP_LOSS = "STOP_LOSS"
    TARGET_REACHED = "TARGET_REACHED"
    END_OF_BACKTEST = "END_OF_BACKTEST"
    NOT_TRIGGERED = "NOT_TRIGGERED"
    INVALID_SIGNAL = "INVALID_SIGNAL"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CostModelConfig:
    """Configurable Indian Equities transaction cost and slippage model."""
    brokerage_pct: float = 0.0          # 0.0% delivery brokerage on discount brokers (e.g., Zerodha)
    brokerage_flat: float = 0.0         # Flat brokerage per executed order
    max_brokerage: float = 20.0         # Ceiling per order (e.g., ₹20)
    stt_rate_buy: float = 0.001         # STT 0.1% on equity delivery buy turnover
    stt_rate_sell: float = 0.001        # STT 0.1% on equity delivery sell turnover
    exchange_rate: float = 0.0000297    # NSE transaction charges ~0.00297%
    sebi_rate: float = 0.000001         # SEBI turnover charge ~0.0001% (₹10/crore)
    stamp_duty_buy: float = 0.00015     # Stamp duty 0.015% on buy turnover only
    stamp_duty_sell: float = 0.0        # No stamp duty on sell in India
    gst_rate: float = 0.18              # 18% GST on (Brokerage + Exchange + SEBI charges)
    slippage_pct: float = 0.0005        # 0.05% slippage on entry and exit execution


class EndOfTestPolicy:
    MARK_TO_MARKET = "MARK_TO_MARKET"
    FORCE_CLOSE = "FORCE_CLOSE"


class RejectionReason:
    ALREADY_IN_POSITION = "ALREADY_IN_POSITION"
    MAX_POSITIONS_REACHED = "MAX_POSITIONS_REACHED"
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    INVALID_ENTRY_PRICE = "INVALID_ENTRY_PRICE"
    ZERO_QUANTITY = "ZERO_QUANTITY"
    MISSING_MARKET_DATA = "MISSING_MARKET_DATA"


@dataclass
class PortfolioConfig:
    """Configuration options for sequential portfolio simulation."""
    initial_capital: float = 100000.0            # ₹100,000 default portfolio size
    max_open_positions: int = 5                  # Max 5 simultaneous open positions
    max_allocation_per_position: float = 0.20    # 20% max allocation per position
    end_of_backtest_policy: str = EndOfTestPolicy.MARK_TO_MARKET
    cost_model: CostModelConfig = field(default_factory=CostModelConfig)
    enable_costs: bool = True                    # Whether transaction costs are deducted


@dataclass
class BacktestConfig:
    """Configuration options for a backtesting run."""
    symbols: List[str]
    start_date: str
    end_date: str
    run_id: str = "default_run"
    persist_results: bool = False
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)


def create_trade_record(
    symbol: str,
    evaluation_date: str,
    recommendation: Optional[str] = None,
    signal_valid: bool = False,
    is_eligible: bool = False,
    signal_reason: Optional[str] = None,
    entry_date: Optional[str] = None,
    entry_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    target: Optional[float] = None,
    risk: Optional[float] = None,
    reward: Optional[float] = None,
    risk_reward_ratio: Optional[float] = None,
    exit_date: Optional[str] = None,
    exit_price: Optional[float] = None,
    exit_reason: str = ExitReason.NOT_TRIGGERED,
    status: str = TradeState.INVALID,
    pl: Optional[float] = None,
    return_pct: Optional[float] = None,
    holding_days: int = 0,
    trade_quality: Optional[Dict[str, Any]] = None,
    quantity: int = 1,
    initial_value: Optional[float] = None,
    gross_pl: Optional[float] = None,
    entry_costs: float = 0.0,
    exit_costs: float = 0.0,
    total_costs: float = 0.0,
    net_pl: Optional[float] = None,
    trade_id: Optional[str] = None,
    run_id: Optional[str] = None,
    direction: str = "LONG",
) -> Dict[str, Any]:
    """
    Constructs a standardized, JSON-serializable trade record dictionary.
    Reconciles gross P/L, transaction costs, and net P/L while maintaining
    full backward compatibility with legacy single-share trade callers.
    """
    qty = max(1, int(quantity)) if isinstance(quantity, (int, float)) and quantity > 0 else 1
    ep = round(entry_price, 4) if isinstance(entry_price, (int, float)) else None
    xp = round(exit_price, 4) if isinstance(exit_price, (int, float)) else None

    # Calculate initial position value
    pos_val = round(initial_value, 4) if isinstance(initial_value, (int, float)) else (
        round(ep * qty, 4) if ep is not None else None
    )

    # Reconcile gross and net P/L
    t_costs = round(total_costs, 4) if isinstance(total_costs, (int, float)) else (
        round(entry_costs + exit_costs, 4) if isinstance(entry_costs, (int, float)) and isinstance(exit_costs, (int, float)) else 0.0
    )

    calc_gross_pl = None
    if isinstance(gross_pl, (int, float)):
        calc_gross_pl = round(gross_pl, 4)
    elif isinstance(pl, (int, float)):
        calc_gross_pl = round(pl, 4)
    elif ep is not None and xp is not None:
        calc_gross_pl = round((xp - ep) * qty, 4)

    calc_net_pl = None
    if isinstance(net_pl, (int, float)):
        calc_net_pl = round(net_pl, 4)
    elif calc_gross_pl is not None:
        calc_net_pl = round(calc_gross_pl - t_costs, 4)

    # Legacy 'pl' field is synchronized with calc_net_pl (or calc_gross_pl if 0 costs)
    final_pl = calc_net_pl if calc_net_pl is not None else calc_gross_pl

    # Calculate return percentage
    calc_ret_pct = None
    if isinstance(return_pct, (int, float)):
        calc_ret_pct = round(return_pct, 4)
    elif final_pl is not None and pos_val is not None and pos_val > 0:
        calc_ret_pct = round((final_pl / pos_val) * 100.0, 4)

    return {
        "symbol": symbol,
        "evaluation_date": evaluation_date,
        "recommendation": recommendation,
        "signal_valid": bool(signal_valid),
        "is_eligible": bool(is_eligible),
        "signal_reason": signal_reason,
        "entry_date": entry_date,
        "entry_price": ep,
        "stop_loss": round(stop_loss, 4) if isinstance(stop_loss, (int, float)) else None,
        "target": round(target, 4) if isinstance(target, (int, float)) else None,
        "risk": round(risk, 4) if isinstance(risk, (int, float)) else None,
        "reward": round(reward, 4) if isinstance(reward, (int, float)) else None,
        "risk_reward_ratio": round(risk_reward_ratio, 4) if isinstance(risk_reward_ratio, (int, float)) else None,
        "exit_date": exit_date,
        "exit_price": xp,
        "exit_reason": exit_reason,
        "status": status,
        "pl": final_pl,
        "return_pct": calc_ret_pct,
        "holding_days": int(holding_days),
        "trade_quality": trade_quality or {},
        "quantity": qty,
        "initial_value": pos_val,
        "gross_pl": calc_gross_pl,
        "entry_costs": round(entry_costs, 4) if isinstance(entry_costs, (int, float)) else 0.0,
        "exit_costs": round(exit_costs, 4) if isinstance(exit_costs, (int, float)) else 0.0,
        "total_costs": t_costs,
        "net_pl": calc_net_pl,
        "trade_id": trade_id,
        "run_id": run_id,
        "direction": direction,
    }
