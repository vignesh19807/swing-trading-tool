"""
Sequential Portfolio Simulator
==============================

Simulates a realistic, capital-constrained trading portfolio across multiple symbols over time:
- Chronological, session-by-session execution without forward-looking data leakage
- Whole-share deterministic position sizing: Quantity = floor(Allocated Capital / Entry Price)
- Cash management: Cash balance prevents over-allocation; position allocation limits enforced
- One position per symbol: Re-entry prohibited while a position in the symbol is open
- Exits processed prior to entries on each session to release available cash
- Indian equity transaction costs (brokerage, STT, exchange, SEBI, stamp duty, GST) and slippage
- Same-bar collision rule (STOP_LOSS priority)
- Explicit Mark-to-Market vs Force-Close end-of-backtest policy
- Chronological portfolio equity curve and drawdown tracking
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.logic.backtest_specification import (
    TradeState,
    ExitReason,
    RejectionReason,
    EndOfTestPolicy,
    SAME_BAR_COLLISION_RULE,
    PortfolioConfig,
    create_trade_record,
)
from backend.logic.cost_model import calculate_trade_costs, apply_slippage


def _normalize_date(val: Any) -> str:
    """Normalize date representation to YYYY-MM-DD string."""
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, str):
        return val.split("T")[0].split(" ")[0].strip()
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return str(val).strip()


def _get_bar_for_date(df: pd.DataFrame, date_str: str) -> Optional[pd.Series]:
    """Retrieve row corresponding to date_str from OHLCV dataframe."""
    if df is None or df.empty or "_date_str" not in df.columns:
        return None
    matched = df[df["_date_str"] == date_str]
    if matched.empty:
        return None
    return matched.iloc[0]


def _count_trading_days(df: pd.DataFrame, start_date: str, end_date: str) -> int:
    """Count trading bars between start_date and end_date inclusive."""
    if df is None or df.empty or "_date_str" not in df.columns:
        return 0
    in_range = df[(df["_date_str"] >= start_date) & (df["_date_str"] <= end_date)]
    return len(in_range)


def _evaluate_position_exit(
    pos: Dict[str, Any],
    bar: Any,
    slippage_pct: float
) -> Optional[Tuple[str, float]]:
    """
    Evaluates whether an open position hits stop loss or target during a bar.
    Returns (exit_reason, exit_price) if exit triggered, else None.
    Uses SAME_BAR_COLLISION_RULE (STOP_LOSS priority) on collision.
    """
    try:
        open_p = float(bar["open"])
        high_p = float(bar["high"])
        low_p = float(bar["low"])
    except (ValueError, TypeError, KeyError):
        return None

    stop_loss = float(pos["stop_loss"])
    target = float(pos["target"])

    hit_stop = (low_p <= stop_loss)
    hit_target = (high_p >= target)

    if hit_stop and hit_target:
        # SAME_BAR_COLLISION_RULE: STOP_LOSS wins (conservative assumption)
        raw_exit_p = min(open_p, stop_loss)
        exit_p = apply_slippage(raw_exit_p, is_buy=False, slippage_pct=slippage_pct)
        return (ExitReason.STOP_LOSS, exit_p)
    elif hit_stop:
        raw_exit_p = min(open_p, stop_loss)
        exit_p = apply_slippage(raw_exit_p, is_buy=False, slippage_pct=slippage_pct)
        return (ExitReason.STOP_LOSS, exit_p)
    elif hit_target:
        raw_exit_p = max(open_p, target)
        exit_p = apply_slippage(raw_exit_p, is_buy=False, slippage_pct=slippage_pct)
        return (ExitReason.TARGET_REACHED, exit_p)

    return None


def _close_position_record(
    pos: Dict[str, Any],
    exit_reason: str,
    exit_p: float,
    exit_date: str,
    run_id: str,
    cfg: PortfolioConfig,
    norm_market: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, Any], float]:
    """
    Creates a closed trade record and computes cash returned (sales proceeds minus exit costs).
    Returns (closed_trade_record, cash_returned).
    """
    sym = pos["symbol"]
    qty = pos["quantity"]
    entry_p = pos["entry_price"]
    entry_costs = pos["entry_costs"]

    exit_cost_res = calculate_trade_costs(exit_p, qty, is_buy=False, config=cfg.cost_model) if cfg.enable_costs else {"total_costs": 0.0}
    exit_costs = exit_cost_res["total_costs"]
    total_costs = round(entry_costs + exit_costs, 4)

    gross_pl = round((exit_p - entry_p) * qty, 4)
    net_pl = round(gross_pl - total_costs, 4)
    pos_cost_basis = round(entry_p * qty + entry_costs, 4)
    ret_pct = round((net_pl / pos_cost_basis) * 100.0, 4) if pos_cost_basis > 0 else 0.0

    cash_returned = round((exit_p * qty) - exit_costs, 4)
    df_sym = norm_market.get(sym)
    holding_days = _count_trading_days(df_sym, pos["entry_date"], exit_date)

    closed_trade = create_trade_record(
        symbol=sym,
        evaluation_date=pos["evaluation_date"],
        recommendation=pos.get("recommendation"),
        signal_valid=True,
        is_eligible=True,
        signal_reason=pos.get("signal_reason"),
        entry_date=pos["entry_date"],
        entry_price=entry_p,
        stop_loss=pos["stop_loss"],
        target=pos["target"],
        risk=pos.get("risk"),
        reward=pos.get("reward"),
        risk_reward_ratio=pos.get("risk_reward_ratio"),
        exit_date=exit_date,
        exit_price=exit_p,
        exit_reason=exit_reason,
        status=TradeState.CLOSED,
        pl=net_pl,
        return_pct=ret_pct,
        holding_days=holding_days,
        trade_quality=pos.get("trade_quality"),
        quantity=qty,
        initial_value=pos["initial_value"],
        gross_pl=gross_pl,
        entry_costs=entry_costs,
        exit_costs=exit_costs,
        total_costs=total_costs,
        net_pl=net_pl,
        trade_id=pos["trade_id"],
        run_id=run_id,
        direction="LONG"
    )
    return closed_trade, cash_returned


def simulate_portfolio(
    signals: List[Dict[str, Any]],
    market_data_by_symbol: Dict[str, pd.DataFrame],
    config: Optional[PortfolioConfig] = None,
    run_id: str = "default_run"
) -> Dict[str, Any]:
    """
    Executes a sequential, portfolio-level backtest across multiple assets.

    Parameters
    ----------
    signals : list of dict
        Candidate trading signals generated at historical evaluation dates.
    market_data_by_symbol : dict of str -> pd.DataFrame
        Daily OHLCV price histories for symbols in the universe.
    config : PortfolioConfig, optional
        Capital limits, position caps, and transaction cost settings.
    run_id : str
        Unique identifier for the simulation run.

    Returns
    -------
    dict
        Comprehensive portfolio backtest execution results:
        all_trades, closed_trades, open_positions, rejected_signals,
        equity_curve, and portfolio_summary.
    """
    cfg = config or PortfolioConfig()

    # Normalize market dataframes
    norm_market: Dict[str, pd.DataFrame] = {}
    all_dates_set = set()

    for sym, df in market_data_by_symbol.items():
        if df is not None and not df.empty and "date" in df.columns:
            cdf = df.copy()
            cdf["_date_str"] = cdf["date"].apply(_normalize_date)
            # Ensure chronological order
            cdf = cdf.sort_values("_date_str").reset_index(drop=True)
            norm_market[sym] = cdf
            for d in cdf["_date_str"]:
                if d:
                    all_dates_set.add(d)

    sorted_dates = sorted(list(all_dates_set))
    if not sorted_dates:
        return {
            "run_id": run_id,
            "all_trades": [],
            "closed_trades": [],
            "open_positions": [],
            "rejected_signals": [],
            "equity_curve": [],
            "portfolio_summary": {
                "initial_capital": cfg.initial_capital,
                "final_cash": cfg.initial_capital,
                "final_equity": cfg.initial_capital,
                "total_gross_pl": 0.0,
                "total_costs": 0.0,
                "total_net_pl": 0.0,
                "max_drawdown_pct": 0.0
            }
        }

    # Group valid signals by evaluation_date
    signals_by_eval_date = defaultdict(list)
    for sig in signals:
        if not isinstance(sig, dict):
            continue
        if sig.get("signal_valid") and sig.get("is_eligible") and sig.get("stop_loss") is not None and sig.get("target") is not None:
            ed = _normalize_date(sig.get("evaluation_date"))
            if ed:
                signals_by_eval_date[ed].append(sig)

    cash = float(cfg.initial_capital)
    open_positions: Dict[str, Dict[str, Any]] = {}
    closed_trades: List[Dict[str, Any]] = []
    rejected_signals: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []

    peak_equity = float(cfg.initial_capital)
    max_drawdown_pct = 0.0
    trade_counter = 0

    prev_date = None

    for current_date in sorted_dates:
        # -------------------------------------------------------------
        # STEP 1: Process Exits for existing open positions on current_date
        # -------------------------------------------------------------
        symbols_to_close = []
        for sym, pos in list(open_positions.items()):
            df_sym = norm_market.get(sym)
            bar = _get_bar_for_date(df_sym, current_date)
            if bar is None:
                continue

            eval_res = _evaluate_position_exit(pos, bar, cfg.cost_model.slippage_pct)
            if eval_res is not None:
                symbols_to_close.append((sym, eval_res[0], eval_res[1], current_date))

        # Finalize position exits and credit cash
        for sym, exit_reason, exit_p, exit_date in symbols_to_close:
            pos = open_positions.pop(sym)
            closed_trade, cash_returned = _close_position_record(
                pos, exit_reason, exit_p, exit_date, run_id, cfg, norm_market
            )
            cash += cash_returned
            closed_trades.append(closed_trade)

        # -------------------------------------------------------------
        # STEP 2: Process Candidate Entries from Previous Session (D-1)
        # Entry rule: NEXT_DAY_OPEN on current_date
        # -------------------------------------------------------------
        newly_opened_syms = []
        if prev_date and prev_date in signals_by_eval_date:
            candidates = list(signals_by_eval_date[prev_date])
            # Deterministic sorting: Opportunity score descending, then Symbol ascending
            candidates.sort(
                key=lambda s: (
                    -float(s.get("opportunity_score") or s.get("trade_quality", {}).get("trade_score") or 0.0),
                    s.get("symbol", "")
                )
            )

            max_alloc_amount = cfg.initial_capital * cfg.max_allocation_per_position

            for sig in candidates:
                sym = sig.get("symbol", "").strip().upper()
                if not sym:
                    continue

                # Rule 1: No duplicate position in same symbol
                if sym in open_positions:
                    rejected_signals.append({
                        "symbol": sym,
                        "date": current_date,
                        "signal_date": prev_date,
                        "reason": RejectionReason.ALREADY_IN_POSITION
                    })
                    continue

                # Rule 2: Max open positions cap
                if len(open_positions) >= cfg.max_open_positions:
                    rejected_signals.append({
                        "symbol": sym,
                        "date": current_date,
                        "signal_date": prev_date,
                        "reason": RejectionReason.MAX_POSITIONS_REACHED
                    })
                    continue

                # Rule 3: Valid market bar on entry date
                df_sym = norm_market.get(sym)
                bar = _get_bar_for_date(df_sym, current_date)
                if bar is None:
                    rejected_signals.append({
                        "symbol": sym,
                        "date": current_date,
                        "signal_date": prev_date,
                        "reason": RejectionReason.MISSING_MARKET_DATA
                    })
                    continue

                try:
                    raw_open = float(bar["open"])
                except (ValueError, TypeError):
                    raw_open = 0.0

                if raw_open <= 0:
                    try:
                        raw_open = float(bar["close"])
                    except (ValueError, TypeError):
                        raw_open = 0.0

                if raw_open <= 0:
                    rejected_signals.append({
                        "symbol": sym,
                        "date": current_date,
                        "signal_date": prev_date,
                        "reason": RejectionReason.INVALID_ENTRY_PRICE
                    })
                    continue

                entry_p = apply_slippage(raw_open, is_buy=True, slippage_pct=cfg.cost_model.slippage_pct)

                # Rule 4: Sizing and available cash
                alloc_cap = min(cash, max_alloc_amount)
                qty = int(alloc_cap // entry_p)

                if qty <= 0:
                    rejected_signals.append({
                        "symbol": sym,
                        "date": current_date,
                        "signal_date": prev_date,
                        "reason": RejectionReason.INSUFFICIENT_CASH if alloc_cap < entry_p else RejectionReason.ZERO_QUANTITY
                    })
                    continue

                entry_cost_res = calculate_trade_costs(entry_p, qty, is_buy=True, config=cfg.cost_model) if cfg.enable_costs else {"total_costs": 0.0}
                entry_costs = entry_cost_res["total_costs"]
                total_required = (entry_p * qty) + entry_costs

                if total_required > cash:
                    # Adjust quantity down to accommodate transaction friction
                    qty = int((cash - entry_costs) // entry_p)
                    if qty <= 0:
                        rejected_signals.append({
                            "symbol": sym,
                            "date": current_date,
                            "signal_date": prev_date,
                            "reason": RejectionReason.INSUFFICIENT_CASH
                        })
                        continue
                    entry_cost_res = calculate_trade_costs(entry_p, qty, is_buy=True, config=cfg.cost_model) if cfg.enable_costs else {"total_costs": 0.0}
                    entry_costs = entry_cost_res["total_costs"]
                    total_required = (entry_p * qty) + entry_costs
                    if total_required > cash:
                        rejected_signals.append({
                            "symbol": sym,
                            "date": current_date,
                            "signal_date": prev_date,
                            "reason": RejectionReason.INSUFFICIENT_CASH
                        })
                        continue

                # Execute entry and deduct cash
                cash = round(cash - total_required, 4)
                trade_counter += 1
                trade_uid = f"{run_id}_{sym}_{current_date}_{trade_counter}"

                open_positions[sym] = {
                    "trade_id": trade_uid,
                    "symbol": sym,
                    "evaluation_date": prev_date,
                    "entry_date": current_date,
                    "entry_price": entry_p,
                    "quantity": qty,
                    "initial_value": round(entry_p * qty, 4),
                    "stop_loss": sig["stop_loss"],
                    "target": sig["target"],
                    "risk": sig.get("risk"),
                    "reward": sig.get("reward"),
                    "risk_reward_ratio": sig.get("risk_reward_ratio"),
                    "recommendation": sig.get("recommendation"),
                    "signal_reason": sig.get("reason"),
                    "entry_costs": entry_costs,
                    "trade_quality": sig.get("trade_quality", {}),
                }
                newly_opened_syms.append(sym)

        # -------------------------------------------------------------
        # STEP 2.5: Process Same-Day Exits for Newly Opened Positions
        # Positions entered at today's open may breach stop-loss or hit target during today's session
        # -------------------------------------------------------------
        same_day_exits = []
        for sym in newly_opened_syms:
            if sym not in open_positions:
                continue
            pos = open_positions[sym]
            df_sym = norm_market.get(sym)
            bar = _get_bar_for_date(df_sym, current_date)
            if bar is None:
                continue

            eval_res = _evaluate_position_exit(pos, bar, cfg.cost_model.slippage_pct)
            if eval_res is not None:
                same_day_exits.append((sym, eval_res[0], eval_res[1], current_date))

        for sym, exit_reason, exit_p, exit_date in same_day_exits:
            pos = open_positions.pop(sym)
            closed_trade, cash_returned = _close_position_record(
                pos, exit_reason, exit_p, exit_date, run_id, cfg, norm_market
            )
            cash += cash_returned
            closed_trades.append(closed_trade)

        # -------------------------------------------------------------
        # STEP 3: Mark to Market at end of current_date
        # -------------------------------------------------------------
        positions_val = 0.0
        for sym, pos in open_positions.items():
            df_sym = norm_market.get(sym)
            bar = _get_bar_for_date(df_sym, current_date)
            try:
                mark_p = float(bar["close"]) if (bar is not None and pd.notna(bar.get("close"))) else pos["entry_price"]
            except (ValueError, TypeError):
                mark_p = pos["entry_price"]
            positions_val += round(mark_p * pos["quantity"], 4)

        current_equity = round(cash + positions_val, 2)
        if current_equity > peak_equity:
            peak_equity = current_equity
        dd = peak_equity - current_equity
        dd_pct = round((dd / peak_equity) * 100.0, 4) if peak_equity > 0 else 0.0
        if dd_pct > max_drawdown_pct:
            max_drawdown_pct = dd_pct

        equity_curve.append({
            "date": current_date,
            "cash": round(cash, 2),
            "positions_value": round(positions_val, 2),
            "equity": current_equity,
            "drawdown_pct": dd_pct
        })

        prev_date = current_date

    # -------------------------------------------------------------
    # STEP 4: End-of-Backtest Policy for Open Positions
    # -------------------------------------------------------------
    open_trade_records = []
    final_date = sorted_dates[-1]

    for sym, pos in list(open_positions.items()):
        df_sym = norm_market.get(sym)
        try:
            last_close = float(df_sym.iloc[-1]["close"]) if df_sym is not None and not df_sym.empty else pos["entry_price"]
            last_date = str(df_sym.iloc[-1]["_date_str"]) if df_sym is not None and not df_sym.empty else final_date
        except (ValueError, TypeError, IndexError):
            last_close = pos["entry_price"]
            last_date = final_date

        qty = pos["quantity"]
        entry_p = pos["entry_price"]
        entry_costs = pos["entry_costs"]

        if cfg.end_of_backtest_policy == EndOfTestPolicy.FORCE_CLOSE:
            # Force liquidation at final close
            exit_p = apply_slippage(last_close, is_buy=False, slippage_pct=cfg.cost_model.slippage_pct)
            exit_cost_res = calculate_trade_costs(exit_p, qty, is_buy=False, config=cfg.cost_model) if cfg.enable_costs else {"total_costs": 0.0}
            exit_costs = exit_cost_res["total_costs"]
            total_costs = round(entry_costs + exit_costs, 4)
            gross_pl = round((exit_p - entry_p) * qty, 4)
            net_pl = round(gross_pl - total_costs, 4)
            pos_cost_basis = round(entry_p * qty + entry_costs, 4)
            ret_pct = round((net_pl / pos_cost_basis) * 100.0, 4) if pos_cost_basis > 0 else 0.0
            cash += round((exit_p * qty) - exit_costs, 4)
            holding_days = _count_trading_days(df_sym, pos["entry_date"], last_date)

            record = create_trade_record(
                symbol=sym,
                evaluation_date=pos["evaluation_date"],
                recommendation=pos.get("recommendation"),
                signal_valid=True,
                is_eligible=True,
                signal_reason=pos.get("signal_reason"),
                entry_date=pos["entry_date"],
                entry_price=entry_p,
                stop_loss=pos["stop_loss"],
                target=pos["target"],
                risk=pos.get("risk"),
                reward=pos.get("reward"),
                risk_reward_ratio=pos.get("risk_reward_ratio"),
                exit_date=last_date,
                exit_price=exit_p,
                exit_reason=ExitReason.END_OF_BACKTEST,
                status=TradeState.CLOSED,
                pl=net_pl,
                return_pct=ret_pct,
                holding_days=holding_days,
                trade_quality=pos.get("trade_quality"),
                quantity=qty,
                initial_value=pos["initial_value"],
                gross_pl=gross_pl,
                entry_costs=entry_costs,
                exit_costs=exit_costs,
                total_costs=total_costs,
                net_pl=net_pl,
                trade_id=pos["trade_id"],
                run_id=run_id,
                direction="LONG"
            )
            closed_trades.append(record)
        else:
            # MARK_TO_MARKET: Remains OPEN
            gross_unrealized_pl = round((last_close - entry_p) * qty, 4)
            net_unrealized_pl = round(gross_unrealized_pl - entry_costs, 4)
            pos_cost_basis = round(entry_p * qty + entry_costs, 4)
            ret_pct = round((net_unrealized_pl / pos_cost_basis) * 100.0, 4) if pos_cost_basis > 0 else 0.0
            holding_days = _count_trading_days(df_sym, pos["entry_date"], last_date)

            record = create_trade_record(
                symbol=sym,
                evaluation_date=pos["evaluation_date"],
                recommendation=pos.get("recommendation"),
                signal_valid=True,
                is_eligible=True,
                signal_reason=pos.get("signal_reason"),
                entry_date=pos["entry_date"],
                entry_price=entry_p,
                stop_loss=pos["stop_loss"],
                target=pos["target"],
                risk=pos.get("risk"),
                reward=pos.get("reward"),
                risk_reward_ratio=pos.get("risk_reward_ratio"),
                exit_date=last_date,
                exit_price=last_close,
                exit_reason=ExitReason.END_OF_BACKTEST,
                status=TradeState.OPEN,
                pl=net_unrealized_pl,
                return_pct=ret_pct,
                holding_days=holding_days,
                trade_quality=pos.get("trade_quality"),
                quantity=qty,
                initial_value=pos["initial_value"],
                gross_pl=gross_unrealized_pl,
                entry_costs=entry_costs,
                exit_costs=0.0,
                total_costs=entry_costs,
                net_pl=net_unrealized_pl,
                trade_id=pos["trade_id"],
                run_id=run_id,
                direction="LONG"
            )
            open_trade_records.append(record)

    all_trades = closed_trades + open_trade_records

    # Portfolio final summary and accounting reconciliation
    final_equity = equity_curve[-1]["equity"] if equity_curve else cfg.initial_capital
    final_cash = cash
    total_gross_pl = round(sum(t.get("gross_pl", 0.0) or 0.0 for t in closed_trades), 4)
    total_costs = round(sum(t.get("total_costs", 0.0) or 0.0 for t in closed_trades), 4)
    total_net_pl = round(sum(t.get("net_pl", 0.0) or 0.0 for t in closed_trades), 4)

    return {
        "run_id": run_id,
        "all_trades": all_trades,
        "closed_trades": closed_trades,
        "open_positions": open_trade_records,
        "rejected_signals": rejected_signals,
        "equity_curve": equity_curve,
        "portfolio_summary": {
            "initial_capital": cfg.initial_capital,
            "final_cash": round(final_cash, 2),
            "final_equity": round(final_equity, 2),
            "total_gross_pl": total_gross_pl,
            "total_costs": total_costs,
            "total_net_pl": total_net_pl,
            "peak_equity": round(peak_equity, 2),
            "max_drawdown_pct": max_drawdown_pct,
            "total_return_pct": round(((final_equity - cfg.initial_capital) / cfg.initial_capital) * 100.0, 4)
        }
    }
