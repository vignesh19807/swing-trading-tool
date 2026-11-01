import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
import sqlite3
import pandas as pd
from backend.experimental.dual_setups import SupportPullbackSetup
from backend.engines.technical_engine import calculate_support_resistance
from backend.logic.portfolio_simulator import simulate_portfolio
from backend.logic.backtest_specification import PortfolioConfig, CostModelConfig

con = sqlite3.connect("database/swing_trading.db")
companies_df = pd.read_sql("SELECT id, symbol FROM companies ORDER BY symbol", con)
symbols = companies_df["symbol"].tolist()
sym_to_id = dict(zip(companies_df["symbol"], companies_df["id"]))

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

sample_df = market_data[symbols[0]]
eval_dates = sample_df[(sample_df["date"] >= "2025-04-01") & (sample_df["date"] <= "2026-10-23")]["date"].tolist()

pullback_engine = SupportPullbackSetup()
pullback_signals = []

for dt in eval_dates:
    for sym in symbols:
        df_sym = market_data[sym]
        idx = df_sym[df_sym["date"] == dt].index
        if idx.empty:
            continue
        curr_idx = idx[0]
        df_hist = df_sym.iloc[:curr_idx + 1]

        sub_hist = df_hist.iloc[-120:] if len(df_hist) >= 120 else df_hist
        curr_price = float(df_hist.iloc[-1]["close"])
        zones_df = calculate_support_resistance(sub_hist["high"], sub_hist["low"], sub_hist["close"])
        
        supports = zones_df[(zones_df["type"] == "support") & (zones_df["level"] < curr_price)]
        nearest_supp = supports.sort_values(by="level", ascending=False).iloc[0].to_dict() if not supports.empty else None

        resistances = zones_df[(zones_df["type"] == "resistance") & (zones_df["level"] > curr_price)]
        nearest_res = resistances.sort_values(by="level", ascending=True).iloc[0].to_dict() if not resistances.empty else None

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

print(f"Total Pullback Signals: {len(pullback_signals)}")

for bps, slip in [(0, 0.0), (10, 0.0010), (20, 0.0020)]:
    cost_cfg = CostModelConfig(slippage_pct=slip)
    cfg = PortfolioConfig(
        initial_capital=100000.0,
        max_allocation_per_position=0.20,
        max_open_positions=5,
        cost_model=cost_cfg
    )
    sim = simulate_portfolio(pullback_signals, market_data, cfg, run_id=f"pullback_{bps}bps")
    summary = sim["portfolio_summary"]
    trades = sim["closed_trades"]
    wins = len([t for t in trades if t.get("net_pl", 0) > 0])
    print(f"\nSlippage {bps:2d} bps:")
    print(f"  Trades: {len(trades)} | Wins: {wins} | Net PnL: Rs {summary['total_net_pl']:,.2f} | Return: {summary['total_return_pct']:+.2f}% | Max DD: {summary['max_drawdown_pct']:.2f}% | Costs: Rs {summary['total_costs']:,.2f}")
