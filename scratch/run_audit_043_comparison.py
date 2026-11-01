"""
AUDIT-043 4-Way Comparative Backtest Evaluation Script
=====================================================
Evaluates:
- Config A: Existing Baseline (from persisted results)
- Config B: Standalone Momentum Breakout
- Config C: Standalone Support Pullback
- Config D: Dual-Setup Hybrid (Arbitrated)

Runs against the 52-stock multi-year historical data.
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.experimental.dual_setups import MomentumBreakoutSetup, SupportPullbackSetup, DualSetupArbitrator
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig
from backend.engines.technical_engine import calculate_support_resistance

DB_PATH = "database/swing_trading.db"

def run_comparative_audit():
    con = sqlite3.connect(DB_PATH)
    
    # 1. Fetch universe
    companies_df = pd.read_sql("SELECT id, symbol FROM companies ORDER BY symbol", con)
    symbols = companies_df["symbol"].tolist()
    sym_to_id = dict(zip(companies_df["symbol"], companies_df["id"]))

    # 2. Fetch all daily prices & technical indicators
    print(f"Loading market data for {len(symbols)} symbols...")
    market_data = {}
    for sym in symbols:
        cid = sym_to_id[sym]
        query = f"""
            SELECT p.date, p.open, p.high, p.low, p.close, p.volume,
                   t.rsi, t.macd, t.macd_signal, t.macd_histogram,
                   t.ema_20, t.ema_50, t.ema_200, t.atr_14
            FROM daily_prices p
            JOIN technical_indicators t ON t.company_id = p.company_id AND t.date = p.date
            WHERE p.company_id = {cid}
            ORDER BY p.date ASC
        """
        df = pd.read_sql(query, con)
        df["_date_str"] = df["date"]
        market_data[sym] = df

    con.close()

    # Determine unique evaluation trading dates
    sample_df = market_data[symbols[0]]
    # Filter between 2025-04-01 and 2026-10-23
    eval_dates = sample_df[(sample_df["date"] >= "2025-04-01") & (sample_df["date"] <= "2026-10-23")]["date"].tolist()
    print(f"Evaluation dates: {len(eval_dates)} sessions ({eval_dates[0]} to {eval_dates[-1]})")

    breakout_engine = MomentumBreakoutSetup()
    pullback_engine = SupportPullbackSetup()
    arbitrator = DualSetupArbitrator()

    breakout_candidates = []
    pullback_candidates = []
    hybrid_candidates = []

    breakout_signals = []
    pullback_signals = []
    hybrid_signals = []

    # Diagnostics counters
    rejections_breakout = {}
    rejections_pullback = {}

    print("Running session-by-session setup evaluation across 52 stocks...")
    for dt in eval_dates:
        for sym in symbols:
            df_sym = market_data[sym]
            idx = df_sym[df_sym["date"] == dt].index
            if idx.empty:
                continue
            curr_idx = idx[0]
            # Use only history up to curr_idx (strict point-in-time)
            df_hist = df_sym.iloc[:curr_idx + 1]

            # --- SETUP A: BREAKOUT ---
            res_a = breakout_engine.evaluate(sym, dt, df_hist)
            if res_a["is_qualified"]:
                sig_a = {
                    "symbol": sym,
                    "date": dt,
                    "evaluation_date": dt,
                    "opportunity_score": 80.0,
                    "recommendation": "BUY",
                    "signal_valid": True,
                    "is_eligible": True,
                    "entry_lower": res_a["entry_lower"],
                    "entry_upper": res_a["entry_upper"],
                    "stop_loss": res_a["stop_loss"],
                    "target": res_a["target"],
                    "risk_reward_ratio": res_a["risk_reward_ratio"],
                    "setup_id": res_a["setup_id"]
                }
                breakout_signals.append(sig_a)
            else:
                reason = res_a["rejection_reason"]
                rejections_breakout[reason] = rejections_breakout.get(reason, 0) + 1

            # --- SETUP B: PULLBACK ---
            # Calculate point-in-time support & resistance zones using history
            # To be efficient, calculate zones using trailing 120 bars
            sub_hist = df_hist.iloc[-120:] if len(df_hist) >= 120 else df_hist
            curr_price = float(df_hist.iloc[-1]["close"])
            zones_df = calculate_support_resistance(sub_hist["high"], sub_hist["low"], sub_hist["close"])
            
            # Find nearest support strictly below curr_price
            supports = zones_df[(zones_df["type"] == "support") & (zones_df["level"] < curr_price)]
            nearest_supp = None
            if not supports.empty:
                nearest_supp = supports.sort_values(by="level", ascending=False).iloc[0].to_dict()

            # Find nearest resistance strictly above curr_price
            resistances = zones_df[(zones_df["type"] == "resistance") & (zones_df["level"] > curr_price)]
            nearest_res = None
            if not resistances.empty:
                nearest_res = resistances.sort_values(by="level", ascending=True).iloc[0].to_dict()

            res_b = pullback_engine.evaluate(sym, dt, df_hist, nearest_supp, nearest_res)
            if res_b["is_qualified"]:
                sig_b = {
                    "symbol": sym,
                    "date": dt,
                    "evaluation_date": dt,
                    "opportunity_score": 80.0,
                    "recommendation": "BUY",
                    "signal_valid": True,
                    "is_eligible": True,
                    "entry_lower": res_b["entry_lower"],
                    "entry_upper": res_b["entry_upper"],
                    "stop_loss": res_b["stop_loss"],
                    "target": res_b["target"],
                    "risk_reward_ratio": res_b["risk_reward_ratio"],
                    "setup_id": res_b["setup_id"]
                }
                pullback_signals.append(sig_b)
            else:
                reason = res_b["rejection_reason"]
                rejections_pullback[reason] = rejections_pullback.get(reason, 0) + 1

            # --- HYBRID ARBITRATION ---
            chosen, arb_reason = arbitrator.arbitrate(res_a, res_b)
            if chosen is not None:
                sig_h = {
                    "symbol": sym,
                    "date": dt,
                    "evaluation_date": dt,
                    "opportunity_score": 80.0,
                    "recommendation": "BUY",
                    "signal_valid": True,
                    "is_eligible": True,
                    "entry_lower": chosen["entry_lower"],
                    "entry_upper": chosen["entry_upper"],
                    "stop_loss": chosen["stop_loss"],
                    "target": chosen["target"],
                    "risk_reward_ratio": chosen["risk_reward_ratio"],
                    "setup_id": chosen["setup_id"],
                    "arbitration_reason": arb_reason
                }
                hybrid_signals.append(sig_h)

    print(f"\n--- Signal Generation Summary ---")
    print(f"Momentum Breakout Signals: {len(breakout_signals)}")
    print(f"Top Breakout Rejections: {sorted(rejections_breakout.items(), key=lambda x: -x[1])[:5]}")
    print(f"Support Pullback Signals: {len(pullback_signals)}")
    print(f"Top Pullback Rejections: {sorted(rejections_pullback.items(), key=lambda x: -x[1])[:5]}")
    print(f"Hybrid Arbitrated Signals: {len(hybrid_signals)}")

    from backend.logic.backtest_specification import PortfolioConfig, CostModelConfig

    # 3. Simulate Portfolios using identical PortfolioConfig with 10 bps slippage
    cost_cfg = CostModelConfig(slippage_pct=0.0010)
    cfg = PortfolioConfig(
        initial_capital=100000.0,
        max_allocation_per_position=0.20,
        max_open_positions=5,
        cost_model=cost_cfg
    )

    print("\nSimulating Portfolio for Config B (Momentum Breakout)...")
    res_sim_b = simulate_portfolio(breakout_signals, market_data, cfg, run_id="exp_breakout")

    print("Simulating Portfolio for Config C (Support Pullback)...")
    res_sim_c = simulate_portfolio(pullback_signals, market_data, cfg, run_id="exp_pullback")

    print("Simulating Portfolio for Config D (Dual-Setup Hybrid)...")
    res_sim_d = simulate_portfolio(hybrid_signals, market_data, cfg, run_id="exp_hybrid")

    # Load baseline results from audit_025_multiyear_results.json
    with open("docs/audit_artifacts/audit_025_multiyear_results.json", "r") as f:
        audit_025 = json.load(f)
    baseline_sim = audit_025["simulations"]["full_horizon_10bps"]

    output_payload = {
        "metadata": {
            "evaluation_sessions": len(eval_dates),
            "universe_count": len(symbols),
            "stock_sessions": len(eval_dates) * len(symbols),
            "date_range": f"{eval_dates[0]} to {eval_dates[-1]}"
        },
        "config_a_baseline": {
            "name": "Config A: Baseline (Monolithic Decision + Pullback Gate)",
            "signals": len(audit_025["eligible_signals_ledger"]),
            "trades_count": len(baseline_sim["closed_trades"]),
            "portfolio_summary": baseline_sim["portfolio_summary"],
            "trades": baseline_sim["closed_trades"]
        },
        "config_b_breakout": {
            "name": "Config B: Standalone Momentum Breakout",
            "signals": len(breakout_signals),
            "rejections": rejections_breakout,
            "trades_count": len(res_sim_b["closed_trades"]),
            "portfolio_summary": res_sim_b["portfolio_summary"],
            "trades": res_sim_b["closed_trades"]
        },
        "config_c_pullback": {
            "name": "Config C: Standalone Support Pullback",
            "signals": len(pullback_signals),
            "rejections": rejections_pullback,
            "trades_count": len(res_sim_c["closed_trades"]),
            "portfolio_summary": res_sim_c["portfolio_summary"],
            "trades": res_sim_c["closed_trades"]
        },
        "config_d_hybrid": {
            "name": "Config D: Dual-Setup Hybrid (Arbitrated)",
            "signals": len(hybrid_signals),
            "trades_count": len(res_sim_d["closed_trades"]),
            "portfolio_summary": res_sim_d["portfolio_summary"],
            "trades": res_sim_d["closed_trades"]
        }
    }

    out_file = "docs/audit_artifacts/audit_043_comparative_results.json"
    with open(out_file, "w") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\nSaved comparative results to {out_file}")
    
    # Print formatted comparative scorecard
    print("\n" + "="*80)
    print("FOUR-WAY COMPARATIVE SCORECARD (Multi-Year 10 bps Slippage)")
    print("="*80)
    fmt = "{:<25} | {:<8} | {:<8} | {:<12} | {:<10} | {:<10}"
    print(fmt.format("Configuration", "Signals", "Trades", "Net PnL (Rs)", "Return (%)", "Max DD (%)"))
    print("-" * 80)
    
    for key in ["config_a_baseline", "config_b_breakout", "config_c_pullback", "config_d_hybrid"]:
        cfg_data = output_payload[key]
        summary = cfg_data["portfolio_summary"]
        net_pl = summary.get("total_net_pl", 0.0)
        ret_pct = summary.get("total_return_pct", 0.0)
        mdd = summary.get("max_drawdown_pct", 0.0)
        print(fmt.format(
            cfg_data["name"][:25],
            cfg_data["signals"],
            cfg_data["trades_count"],
            f"{net_pl:,.2f}",
            f"{ret_pct:+.2f}%",
            f"{mdd:.2f}%"
        ))
    print("="*80)

if __name__ == "__main__":
    run_comparative_audit()

