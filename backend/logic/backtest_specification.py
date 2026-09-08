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
class BacktestConfig:
    """Configuration options for a backtesting run."""
    symbols: List[str]
    start_date: str
    end_date: str
    run_id: str = "default_run"
    persist_results: bool = False


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
) -> Dict[str, Any]:
    """
    Constructs a standardized, JSON-serializable trade record dictionary.
    """
    return {
        "symbol": symbol,
        "evaluation_date": evaluation_date,
        "recommendation": recommendation,
        "signal_valid": bool(signal_valid),
        "is_eligible": bool(is_eligible),
        "signal_reason": signal_reason,
        "entry_date": entry_date,
        "entry_price": round(entry_price, 4) if isinstance(entry_price, (int, float)) else None,
        "stop_loss": round(stop_loss, 4) if isinstance(stop_loss, (int, float)) else None,
        "target": round(target, 4) if isinstance(target, (int, float)) else None,
        "risk": round(risk, 4) if isinstance(risk, (int, float)) else None,
        "reward": round(reward, 4) if isinstance(reward, (int, float)) else None,
        "risk_reward_ratio": round(risk_reward_ratio, 4) if isinstance(risk_reward_ratio, (int, float)) else None,
        "exit_date": exit_date,
        "exit_price": round(exit_price, 4) if isinstance(exit_price, (int, float)) else None,
        "exit_reason": exit_reason,
        "status": status,
        "pl": round(pl, 4) if isinstance(pl, (int, float)) else None,
        "return_pct": round(return_pct, 4) if isinstance(return_pct, (int, float)) else None,
        "holding_days": int(holding_days),
        "trade_quality": trade_quality or {},
    }
