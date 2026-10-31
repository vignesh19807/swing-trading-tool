"""
AUDIT-025 & AUDIT-026: Multi-Year 52-Stock Parallel Historical Evaluation
========================================================================
Utilizes multi-process execution across 12 worker processes to evaluate
all 52 stocks across 387 trading sessions (20,124 stock-sessions).
Target DB: docs/audit_artifacts/temp_multiyear_audit_025.db
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
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter

# Suppress pandas dateutil parse warnings
warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, os.path.abspath("."))
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

DB_PATH = Path("docs/audit_artifacts/temp_multiyear_audit_025.db").resolve()
assert DB_PATH.exists(), f"Target DB not found: {DB_PATH}"

def worker_init():
    """Initializer for each subprocess."""
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    import backend.data_pipeline.financial_service as fin
    import backend.data_pipeline.data_service as ds
    import backend.data_pipeline.classification_service as cs
    import backend.data_pipeline.backtest_result_service as b_svc
    import backend.engines.financial_engine as fe
    from unittest.mock import patch

    patch.object(fin, "DATABASE_PATH", DB_PATH).start()
    patch.object(ds, "DATABASE_PATH", DB_PATH).start()
    patch.object(cs, "DATABASE_PATH", DB_PATH).start()
    patch.object(b_svc, "DATABASE_PATH", DB_PATH).start()
    patch.object(fe, "analyze_financial_health", functools.lru_cache(maxsize=4096)(fe.analyze_financial_health)).start()

def evaluate_single_stock(symbol, dates, sym_dates):
    """Evaluates all dates for a single stock."""
    from backend.logic.signal_integration import run_signal_pipeline
    
    sessions = 0
    raw_buys = 0
    rejections = Counter()
    eligible_signals = []
    buy_signals_all = []
    
    for dt in dates:
        if dt not in sym_dates:
            continue
        sessions += 1
        
        try:
            sig = run_signal_pipeline(symbol, evaluation_date=dt)
        except Exception as e:
            continue
            
        rec = sig.get("recommendation")
        is_eligible = sig.get("is_eligible", False)
        tq = sig.get("trade_quality", {})
        reason = tq.get("eligibility_reason") or sig.get("reason")
        
        if rec == "BUY":
            raw_buys += 1
            buy_summary = {
                "symbol": symbol,
                "date": dt,
                "is_eligible": is_eligible,
                "reason": reason,
                "risk_reward_ratio": sig.get("risk_reward_ratio"),
                "entry_lower": sig.get("entry_lower"),
                "entry_upper": sig.get("entry_upper"),
                "stop_loss": sig.get("stop_loss"),
                "target": sig.get("target")
            }
            buy_signals_all.append(buy_summary)
            if is_eligible:
                eligible_signals.append(sig)
            else:
                rejections[reason] += 1
                
    return {
        "symbol": symbol,
        "sessions": sessions,
        "raw_buys": raw_buys,
        "rejections": dict(rejections),
        "eligible_signals": eligible_signals,
        "buy_signals_all": buy_signals_all
    }

def main():
    conn = sqlite3.connect(DB_PATH)
    symbols = [r[0] for r in conn.execute("SELECT symbol FROM companies ORDER BY symbol").fetchall()]
    all_trading_dates = [r[0] for r in conn.execute("""
        SELECT DISTINCT date FROM daily_prices 
        WHERE date >= '2025-04-01' AND date <= '2026-10-23'
        ORDER BY date ASC
    """).fetchall()]
    
    print(f"Total symbols: {len(symbols)}")
    print(f"Total trading dates: {len(all_trading_dates)}")
    
    # Pre-fetch market data for portfolio simulation
    print("Pre-fetching market data for all 52 symbols...")
    market_data = {}
    symbol_dates_map = {}
    for sym in symbols:
        df = pd.read_sql("""
            SELECT dp.date, dp.open, dp.high, dp.low, dp.close, dp.volume
            FROM daily_prices dp
            JOIN companies c ON c.id = dp.company_id
            WHERE c.symbol = ? AND dp.date >= '2024-10-23' AND dp.date <= '2026-10-23'
            ORDER BY dp.date ASC
        """, conn, params=(sym,))
        market_data[sym] = df
        symbol_dates_map[sym] = set(df["date"].tolist())
    conn.close()
    
    cache_file = Path("scratch/multiyear_eval_cache.json")
    if cache_file.exists():
        print(f"Loading cached signal evaluation from {cache_file}...")
        with open(cache_file, "r") as f:
            cache_data = json.load(f)
        total_sessions = cache_data["total_sessions"]
        total_raw_buys = cache_data["total_raw_buys"]
        rejection_counter = Counter(cache_data["rejections"])
        all_eligible_signals = cache_data["all_eligible_signals"]
        all_buy_records = cache_data["all_buy_records"]
    else:
        num_workers = min(12, os.cpu_count() or 4)
        print(f"Launching parallel evaluation across {num_workers} worker processes...")
        
        total_sessions = 0
        total_raw_buys = 0
        rejection_counter = Counter()
        all_eligible_signals = []
        all_buy_records = []
        
        with ProcessPoolExecutor(max_workers=num_workers, initializer=worker_init) as executor:
            futures = {
                executor.submit(evaluate_single_stock, sym, all_trading_dates, symbol_dates_map[sym]): sym
                for sym in symbols
            }
            
            completed = 0
            for f in as_completed(futures):
                res = f.result()
                sym = res["symbol"]
                completed += 1
                total_sessions += res["sessions"]
                total_raw_buys += res["raw_buys"]
                for r, cnt in res["rejections"].items():
                    rejection_counter[r] += cnt
                all_eligible_signals.extend(res["eligible_signals"])
                all_buy_records.extend(res["buy_signals_all"])
                print(f"[{completed}/{len(symbols)}] {sym:<12} | Sessions: {res['sessions']} | Raw BUYs: {res['raw_buys']} | Eligible: {len(res['eligible_signals'])}")
        
        with open(cache_file, "w") as f:
            json.dump({
                "total_sessions": total_sessions,
                "total_raw_buys": total_raw_buys,
                "rejections": dict(rejection_counter),
                "all_eligible_signals": all_eligible_signals,
                "all_buy_records": all_buy_records
            }, f, indent=2, default=str)
            
    print("\n" + "="*60)
    print("SIGNAL EVALUATION COMPLETE")
    print(f"Total Stock-Sessions Evaluated: {total_sessions}")
    print(f"Total Raw BUY Signals: {total_raw_buys}")
    print(f"Total Eligible BUY Signals: {len(all_eligible_signals)}")
    print(f"Total Rejected BUY Signals: {sum(rejection_counter.values())}")
    print("\nRejection Breakdown:")
    for r, cnt in rejection_counter.most_common():
        pct = (cnt / (total_raw_buys - len(all_eligible_signals))) * 100 if total_raw_buys > len(all_eligible_signals) else 0
        print(f"  {r}: {cnt} ({pct:.2f}%)")
        
    # Benchmarks
    print("\n" + "="*60)
    print("COMPUTING BENCHMARKS")
    def compute_benchmark(start_dt, end_dt):
        returns = []
        for sym in symbols:
            df_sym = market_data[sym]
            start_bars = df_sym[df_sym["date"] >= start_dt]
            end_bars = df_sym[df_sym["date"] <= end_dt]
            if not start_bars.empty and not end_bars.empty:
                p_start = float(start_bars.iloc[0]["close"])
                p_end = float(end_bars.iloc[-1]["close"])
                returns.append((p_end - p_start) / p_start)
        if returns:
            return {
                "period": f"{start_dt} to {end_dt}",
                "mean_return_pct": round(float(np.mean(returns)) * 100, 2),
                "median_return_pct": round(float(np.median(returns)) * 100, 2),
                "cross_sectional_vol_pct": round(float(np.std(returns)) * 100, 2),
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
    
    # Portfolio Simulations
    print("\n" + "="*60)
    print("RUNNING PORTFOLIO SIMULATIONS")
    from backend.logic.portfolio_simulator import simulate_portfolio
    from backend.logic.backtest_specification import PortfolioConfig, CostModelConfig
    
    def run_simulation(period_name, start_dt, end_dt, slippage=0.001):
        sub_signals = [
            s for s in all_eligible_signals 
            if start_dt <= s.get("evaluation_date", "") <= end_dt
        ]
        sub_market_data = {}
        for sym, df in market_data.items():
            sub_market_data[sym] = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)].copy()
            
        cfg = PortfolioConfig(
            initial_capital=100000.0,
            max_open_positions=5,
            max_allocation_per_position=0.20,
            cost_model=CostModelConfig(slippage_pct=slippage)
        )
        run_id = f"sim_{period_name}_{int(slippage*10000)}bps"
        return simulate_portfolio(
            signals=sub_signals,
            market_data_by_symbol=sub_market_data,
            config=cfg,
            run_id=run_id
        )

    sim_results = {
        "full_horizon_10bps": run_simulation("FULL", "2025-04-01", "2026-10-23", 0.001),
        "in_sample_10bps": run_simulation("IS", "2025-04-01", "2026-03-31", 0.001),
        "out_of_sample_10bps": run_simulation("OOS", "2026-04-01", "2026-10-23", 0.001),
        "pilot_period_10bps": run_simulation("PILOT", "2025-10-01", "2026-03-31", 0.001),
        "full_horizon_0bps": run_simulation("FULL", "2025-04-01", "2026-10-23", 0.0),
        "full_horizon_20bps": run_simulation("FULL", "2025-04-01", "2026-10-23", 0.002),
    }

    print("\n=== Simulation Summary Table ===")
    for k, res in sim_results.items():
        tr = res.get("trade_summary", {})
        eq = res.get("equity_summary", {})
        print(f"[{k}] Trades: {tr.get('total_trades', 0)} (Wins: {tr.get('winning_trades', 0)}, Losses: {tr.get('losing_trades', 0)}) | Net P/L: Rs. {tr.get('net_profit', 0):.2f} | Return: {eq.get('total_return_pct', 0):.2f}% | MaxDD: {eq.get('max_drawdown_pct', 0):.2f}%")

    output_path = Path("docs/audit_artifacts/audit_025_multiyear_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "metadata": {
                "universe_count": len(symbols),
                "trading_sessions": len(all_trading_dates),
                "total_stock_sessions": total_sessions,
                "raw_buys": total_raw_buys,
                "eligible_buys": len(all_eligible_signals),
                "rejections": dict(rejection_counter)
            },
            "benchmarks": benchmarks,
            "simulations": sim_results,
            "eligible_signals_ledger": [
                {
                    "symbol": s.get("symbol"),
                    "date": s.get("evaluation_date"),
                    "entry_lower": s.get("entry_lower"),
                    "entry_upper": s.get("entry_upper"),
                    "stop_loss": s.get("stop_loss"),
                    "target": s.get("target"),
                    "risk_reward_ratio": s.get("risk_reward_ratio")
                } for s in all_eligible_signals
            ]
        }, f, indent=2, default=str)
    print(f"\nSaved master results artifact to {output_path}")

if __name__ == "__main__":
    main()
