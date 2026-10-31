"""
AUDIT-025 & AUDIT-026: Multi-Year 52-Stock Historical Backtest & Robustness Evaluation
====================================================================================
Evaluates all 52 stocks across 387 trading sessions (2025-04-01 to 2026-10-23).
Computes In-Sample vs Out-of-Sample performance, benchmark comparison, and slippage sensitivity.
Operates on isolated temporary database: docs/audit_artifacts/temp_multiyear_audit_025.db
"""

import os
import sys
import json
import sqlite3
import functools
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch
from collections import Counter

# Suppress pandas dateutil parse warnings during high-throughput loop
warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, os.path.abspath("."))

DB_PATH = Path("docs/audit_artifacts/temp_multiyear_audit_025.db").resolve()
assert DB_PATH.exists(), f"Isolated test database not found at {DB_PATH}"

import backend.data_pipeline.financial_service as financial_service
import backend.data_pipeline.data_service as data_service
import backend.data_pipeline.classification_service as classification_service
import backend.data_pipeline.backtest_result_service as backtest_svc
import backend.engines.financial_engine as financial_engine
from backend.logic.signal_integration import run_signal_pipeline
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig

# Point services to isolated temporary database
patch.object(financial_service, "DATABASE_PATH", DB_PATH).start()
patch.object(data_service, "DATABASE_PATH", DB_PATH).start()
patch.object(classification_service, "DATABASE_PATH", DB_PATH).start()
patch.object(backtest_svc, "DATABASE_PATH", DB_PATH).start()

# Cache expensive financial analyzer calls across the multi-year timeline
# (Financials only change on quarter releases, so caching provides 10-20x speedup while maintaining 100% fidelity)
cached_fin = functools.lru_cache(maxsize=4096)(financial_engine.analyze_financial_health)
patch.object(financial_engine, "analyze_financial_health", cached_fin).start()

conn = sqlite3.connect(DB_PATH)

symbols = [r[0] for r in conn.execute("SELECT symbol FROM companies ORDER BY symbol").fetchall()]
print(f"Loaded {len(symbols)} symbols from isolated database.")

# Fetch all trading dates
all_trading_dates = [r[0] for r in conn.execute("""
    SELECT DISTINCT date FROM daily_prices 
    WHERE date >= '2025-04-01' AND date <= '2026-10-23'
    ORDER BY date ASC
""").fetchall()]
print(f"Total trading dates in multi-year window (2025-04-01 to 2026-10-23): {len(all_trading_dates)}")

# Pre-fetch all daily price bars for all 52 symbols
print("Pre-fetching market data for portfolio simulation...")
market_data = {}
for sym in symbols:
    df = pd.read_sql("""
        SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
        FROM daily_prices dp
        JOIN companies c ON c.id = dp.company_id
        WHERE c.symbol = ? AND dp.date >= '2024-10-23' AND dp.date <= '2026-10-23'
        ORDER BY dp.date ASC
    """, conn, params=(sym,))
    market_data[sym] = df

conn.close()

# Define sub-periods
# In-Sample: 2025-04-01 to 2026-03-31 (248 sessions)
# Out-of-Sample: 2026-04-01 to 2026-10-23 (139 sessions)
# Full Horizon: 2025-04-01 to 2026-10-23 (387 sessions)
date_sets = {
    "FULL_HORIZON": [d for d in all_trading_dates if "2025-04-01" <= d <= "2026-10-23"],
    "IN_SAMPLE": [d for d in all_trading_dates if "2025-04-01" <= d <= "2026-03-31"],
    "OUT_OF_SAMPLE": [d for d in all_trading_dates if "2026-04-01" <= d <= "2026-10-23"],
    "PILOT_PERIOD": [d for d in all_trading_dates if "2025-10-01" <= d <= "2026-03-31"]
}

print(f"Full horizon dates: {len(date_sets['FULL_HORIZON'])}")
print(f"In-sample dates: {len(date_sets['IN_SAMPLE'])}")
print(f"Out-of-sample dates: {len(date_sets['OUT_OF_SAMPLE'])}")
print(f"Pilot period dates: {len(date_sets['PILOT_PERIOD'])}")

# Signal evaluation across full horizon
print("\n--- Starting Full-Horizon Signal Evaluation (52 stocks x 387 dates = 20,124 sessions) ---")
total_sessions = 0
all_signals = []
raw_buys = 0
rejection_counter = Counter()
eligible_signals = []

for idx, sym in enumerate(symbols, 1):
    df_sym = market_data[sym]
    sym_dates = set(df_sym["date"].tolist())
    sym_sessions = 0
    sym_buys = 0
    sym_eligible = 0
    
    for dt in date_sets["FULL_HORIZON"]:
        if dt not in sym_dates:
            continue
        total_sessions += 1
        sym_sessions += 1
        
        sig = run_signal_pipeline(sym, evaluation_date=dt)
        rec = sig.get("recommendation")
        is_eligible = sig.get("is_eligible", False)
        tq = sig.get("trade_quality", {})
        reason = tq.get("eligibility_reason") or sig.get("reason")
        
        if rec == "BUY":
            raw_buys += 1
            sym_buys += 1
            all_signals.append({
                "symbol": sym,
                "date": dt,
                "is_eligible": is_eligible,
                "reason": reason,
                "risk_reward_ratio": sig.get("risk_reward_ratio"),
                "entry_lower": sig.get("entry_lower"),
                "entry_upper": sig.get("entry_upper"),
                "stop_loss": sig.get("stop_loss"),
                "target": sig.get("target")
            })
            if is_eligible:
                eligible_signals.append(sig)
                sym_eligible += 1
            else:
                rejection_counter[reason] += 1
                
    if idx % 10 == 0 or idx == len(symbols):
        print(f"Processed [{idx}/{len(symbols)}] stocks... Total sessions so far: {total_sessions}, Raw BUYs: {raw_buys}, Eligible: {len(eligible_signals)}")

print("\n=== Signal Generation Summary (Full Horizon) ===")
print(f"Total Stock-Sessions Evaluated: {total_sessions}")
print(f"Total Raw BUY Signals: {raw_buys}")
print(f"Total Eligible Signals: {len(eligible_signals)}")
print(f"Total Rejected BUY Signals: {sum(rejection_counter.values())}")
print("\nRejection Breakdown:")
for r, cnt in rejection_counter.most_common():
    pct = cnt / (raw_buys - len(eligible_signals)) * 100 if raw_buys > len(eligible_signals) else 0
    print(f"  {r}: {cnt} ({pct:.2f}%)")

# Benchmark Calculation: Equal-weight buy-and-hold across 52 stocks
print("\n--- Computing 52-Stock Equal-Weight Benchmark ---")
def compute_benchmark(start_dt, end_dt):
    returns = []
    for sym in symbols:
        df_sym = market_data[sym]
        start_bars = df_sym[df_sym["date"] >= start_dt]
        end_bars = df_sym[df_sym["date"] <= end_dt]
        if not start_bars.empty and not end_bars.empty:
            p_start = float(start_bars.iloc[0]["close"])
            p_end = float(end_bars.iloc[-1]["close"])
            ret = (p_end - p_start) / p_start
            returns.append(ret)
    if returns:
        avg_ret = float(np.mean(returns))
        med_ret = float(np.median(returns))
        vol = float(np.std(returns))
        return {
            "period": f"{start_dt} to {end_dt}",
            "mean_return_pct": round(avg_ret * 100, 2),
            "median_return_pct": round(med_ret * 100, 2),
            "cross_sectional_vol_pct": round(vol * 100, 2),
            "stock_count": len(returns)
        }
    return {}

benchmarks = {
    "FULL_HORIZON": compute_benchmark("2025-04-01", "2026-10-23"),
    "IN_SAMPLE": compute_benchmark("2025-04-01", "2026-03-31"),
    "OUT_OF_SAMPLE": compute_benchmark("2026-04-01", "2026-10-23"),
    "PILOT_PERIOD": compute_benchmark("2025-10-01", "2026-03-31")
}
print(json.dumps(benchmarks, indent=2))

# Portfolio Simulations across periods and slippage levels
print("\n--- Running Portfolio Simulations ---")
cfg_default = PortfolioConfig(initial_capital=100000.0, max_open_positions=5, max_allocation_per_position=0.20, slippage_pct=0.001)

def run_simulation(period_name, start_dt, end_dt, slippage=0.001):
    sub_signals = [
        s for s in eligible_signals 
        if start_dt <= s.get("evaluation_date", "") <= end_dt
    ]
    # Sliced market data
    sub_market_data = {}
    for sym, df in market_data.items():
        sub_market_data[sym] = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)].copy()
        
    cfg = PortfolioConfig(
        initial_capital=100000.0,
        max_open_positions=5,
        max_allocation_per_position=0.20,
        slippage_pct=slippage
    )
    
    run_id = f"sim_{period_name}_{int(slippage*10000)}bps"
    res = simulate_portfolio(
        signals=sub_signals,
        market_data_by_symbol=sub_market_data,
        config=cfg,
        run_id=run_id
    )
    return res

results = {
    "full_horizon_10bps": run_simulation("FULL", "2025-04-01", "2026-10-23", 0.001),
    "in_sample_10bps": run_simulation("IS", "2025-04-01", "2026-03-31", 0.001),
    "out_of_sample_10bps": run_simulation("OOS", "2026-04-01", "2026-10-23", 0.001),
    "pilot_period_10bps": run_simulation("PILOT", "2025-10-01", "2026-03-31", 0.001),
    # Slippage sensitivity on full horizon
    "full_horizon_0bps": run_simulation("FULL", "2025-04-01", "2026-10-23", 0.0),
    "full_horizon_20bps": run_simulation("FULL", "2025-04-01", "2026-10-23", 0.002),
}

# Print concise summary
print("\n=== Simulation Metrics Summary ===")
for k, res in results.items():
    tr = res.get("trade_summary", {})
    eq = res.get("equity_summary", {})
    print(f"[{k}]")
    print(f"  Total Trades: {tr.get('total_trades')}, Wins: {tr.get('winning_trades')}, Losses: {tr.get('losing_trades')}")
    print(f"  Net P/L: Rs. {tr.get('net_profit', 0):.2f}, Return: {eq.get('total_return_pct', 0):.2f}%")
    print(f"  Max Drawdown: {eq.get('max_drawdown_pct', 0):.2f}%, Final Capital: Rs. {eq.get('final_capital', 0):.2f}")

# Save full results
output_file = Path("docs/audit_artifacts/audit_025_multiyear_results.json")
with open(output_file, "w") as f:
    json.dump({
        "metadata": {
            "evaluation_universe": len(symbols),
            "trading_sessions": len(all_trading_dates),
            "total_stock_sessions": total_sessions,
            "raw_buys": raw_buys,
            "eligible_signals_count": len(eligible_signals),
            "rejections": dict(rejection_counter),
        },
        "benchmarks": benchmarks,
        "simulations": results,
        "eligible_signals": [
            {
                "symbol": s.get("symbol"),
                "evaluation_date": s.get("evaluation_date"),
                "entry_lower": s.get("entry_lower"),
                "entry_upper": s.get("entry_upper"),
                "stop_loss": s.get("stop_loss"),
                "target": s.get("target"),
                "risk_reward_ratio": s.get("risk_reward_ratio")
            } for s in eligible_signals
        ]
    }, f, indent=2, default=str)

print(f"\nSaved full multi-year results to {output_file}")

