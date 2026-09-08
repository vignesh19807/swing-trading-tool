"""
Week 12 - Trade Simulator
=========================

Simulates trade execution and post-signal price bar progression for valid historical signals.
Strictly enforces temporal separation: future market bars are inspected ONLY AFTER the signal
has been generated on or before evaluation_date.

Author: Logic Engineer
"""

from typing import Any, Dict, List, Optional
import pandas as pd

from backend.logic.backtest_specification import (
    TradeState,
    ExitReason,
    create_trade_record,
    SAME_BAR_COLLISION_RULE,
)


def _normalize_date_str(val: Any) -> str:
    """Normalize timestamp or date string to YYYY-MM-DD format."""
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, str):
        return val.split("T")[0].split(" ")[0].strip()
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return str(val).strip()


def simulate_trade(
    signal_payload: Dict[str, Any],
    market_data: pd.DataFrame
) -> Dict[str, Any]:
    """
    Simulates trade execution for a single evaluated historical signal using subsequent price history.

    Parameters
    ----------
    signal_payload : dict
        Point-in-time signal dictionary produced by historical_signal_evaluator.
    market_data : pd.DataFrame
        Market OHLCV data containing columns ['date', 'open', 'high', 'low', 'close'].

    Returns
    -------
    dict
        Structured trade record matching Week 12 contract.
    """
    if not isinstance(signal_payload, dict):
        return create_trade_record(
            symbol="",
            evaluation_date="",
            status=TradeState.INVALID,
            signal_reason="INVALID_SIGNAL_PAYLOAD"
        )

    symbol = signal_payload.get("symbol", "")
    eval_date = _normalize_date_str(signal_payload.get("evaluation_date"))
    recommendation = signal_payload.get("recommendation")
    signal_valid = signal_payload.get("signal_valid", False)
    is_eligible = signal_payload.get("is_eligible", False)
    signal_reason = signal_payload.get("reason")
    stop_loss = signal_payload.get("stop_loss")
    target = signal_payload.get("target")
    risk = signal_payload.get("risk")
    reward = signal_payload.get("reward")
    risk_reward_ratio = signal_payload.get("risk_reward_ratio")
    trade_quality = signal_payload.get("trade_quality", {})

    # 1. Validate Signal Eligibility
    if not signal_valid or not is_eligible or stop_loss is None or target is None:
        return create_trade_record(
            symbol=symbol,
            evaluation_date=eval_date,
            recommendation=recommendation,
            signal_valid=signal_valid,
            is_eligible=is_eligible,
            signal_reason=signal_reason or "INELIGIBLE_SIGNAL",
            stop_loss=stop_loss,
            target=target,
            risk=risk,
            reward=reward,
            risk_reward_ratio=risk_reward_ratio,
            status=TradeState.INVALID,
            exit_reason=ExitReason.INVALID_SIGNAL,
            trade_quality=trade_quality
        )

    if market_data is None or market_data.empty:
        return create_trade_record(
            symbol=symbol,
            evaluation_date=eval_date,
            recommendation=recommendation,
            signal_valid=signal_valid,
            is_eligible=is_eligible,
            signal_reason="MISSING_MARKET_DATA_FOR_SIMULATION",
            stop_loss=stop_loss,
            target=target,
            risk=risk,
            reward=reward,
            risk_reward_ratio=risk_reward_ratio,
            status=TradeState.INCOMPLETE,
            exit_reason=ExitReason.NOT_TRIGGERED,
            trade_quality=trade_quality
        )

    # 2. Filter Future Market Bars (Date > eval_date)
    df = market_data.copy()
    if "date" not in df.columns:
        return create_trade_record(
            symbol=symbol,
            evaluation_date=eval_date,
            recommendation=recommendation,
            signal_valid=signal_valid,
            is_eligible=is_eligible,
            signal_reason="MISSING_DATE_COLUMN_IN_MARKET_DATA",
            status=TradeState.INCOMPLETE,
            exit_reason=ExitReason.NOT_TRIGGERED,
            trade_quality=trade_quality
        )

    df["_date_str"] = df["date"].apply(_normalize_date_str)
    future_bars = df[df["_date_str"] > eval_date].sort_values("_date_str").reset_index(drop=True)

    if future_bars.empty:
        return create_trade_record(
            symbol=symbol,
            evaluation_date=eval_date,
            recommendation=recommendation,
            signal_valid=signal_valid,
            is_eligible=is_eligible,
            signal_reason=signal_reason,
            stop_loss=stop_loss,
            target=target,
            risk=risk,
            reward=reward,
            risk_reward_ratio=risk_reward_ratio,
            status=TradeState.OPEN,
            exit_reason=ExitReason.NOT_TRIGGERED,
            trade_quality=trade_quality
        )

    # 3. Determine Entry on Bar D+1 (NEXT_DAY_OPEN)
    entry_bar = future_bars.iloc[0]
    entry_date = entry_bar["_date_str"]
    try:
        entry_price = float(entry_bar["open"])
    except (ValueError, TypeError):
        try:
            entry_price = float(entry_bar["close"])
        except (ValueError, TypeError):
            return create_trade_record(
                symbol=symbol,
                evaluation_date=eval_date,
                recommendation=recommendation,
                signal_valid=signal_valid,
                is_eligible=is_eligible,
                signal_reason="INVALID_ENTRY_BAR_PRICES",
                status=TradeState.INCOMPLETE,
                trade_quality=trade_quality
            )

    # 4. Simulate Bar-by-Bar progression
    exit_date = None
    exit_price = None
    exit_reason = ExitReason.END_OF_BACKTEST
    status = TradeState.OPEN
    holding_days = 0

    for idx, row in future_bars.iterrows():
        holding_days = idx + 1
        bar_date = row["_date_str"]
        try:
            open_p = float(row["open"])
            high_p = float(row["high"])
            low_p = float(row["low"])
            close_p = float(row["close"])
        except (ValueError, TypeError):
            continue

        hit_stop = (low_p <= stop_loss)
        hit_target = (high_p >= target)

        if hit_stop and hit_target:
            # SAME_BAR_COLLISION_RULE: STOP_LOSS wins (conservative assumption)
            status = TradeState.CLOSED
            exit_reason = ExitReason.STOP_LOSS
            exit_date = bar_date
            exit_price = min(open_p, stop_loss)
            break
        elif hit_stop:
            status = TradeState.CLOSED
            exit_reason = ExitReason.STOP_LOSS
            exit_date = bar_date
            exit_price = min(open_p, stop_loss)
            break
        elif hit_target:
            status = TradeState.CLOSED
            exit_reason = ExitReason.TARGET_REACHED
            exit_date = bar_date
            exit_price = max(open_p, target)
            break

    # If trade remains open at end of simulation, set exit_price to final close for mark-to-market
    if status == TradeState.OPEN:
        try:
            exit_price = float(future_bars.iloc[-1]["close"])
            exit_date = future_bars.iloc[-1]["_date_str"]
        except (ValueError, TypeError, IndexError):
            exit_price = entry_price

    pl = exit_price - entry_price if (exit_price is not None and entry_price is not None) else None
    return_pct = ((exit_price - entry_price) / entry_price * 100.0) if (pl is not None and entry_price and entry_price > 0) else None

    return create_trade_record(
        symbol=symbol,
        evaluation_date=eval_date,
        recommendation=recommendation,
        signal_valid=signal_valid,
        is_eligible=is_eligible,
        signal_reason=signal_reason,
        entry_date=entry_date,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target=target,
        risk=risk,
        reward=reward,
        risk_reward_ratio=risk_reward_ratio,
        exit_date=exit_date,
        exit_price=exit_price,
        exit_reason=exit_reason,
        status=status,
        pl=pl,
        return_pct=return_pct,
        holding_days=holding_days,
        trade_quality=trade_quality
    )


def simulate_trades_for_signals(
    signals: List[Dict[str, Any]],
    market_data: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Simulates trades for a list of historical signal payloads using provided market price history.
    """
    trades = []
    for sig in signals:
        trade = simulate_trade(sig, market_data)
        trades.append(trade)
    return trades
