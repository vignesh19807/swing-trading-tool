import json
import sqlite3
import pandas as pd
from collections import defaultdict

with open("docs/audit_artifacts/audit_045_cost_complete_results.json", "r") as f:
    d = json.load(f)

trades = d["trades_cost_complete_10bps"]

con = sqlite3.connect("database/swing_trading.db")
sec_df = pd.read_sql("""
    SELECT c.symbol, s.name as sector, i.name as industry
    FROM companies c
    LEFT JOIN sectors s ON s.id = c.sector_id
    LEFT JOIN industries i ON i.id = c.industry_id
""", con)
con.close()

sym_to_sec = dict(zip(sec_df["symbol"], sec_df["sector"]))

print("=== PER-TRADE COST-COMPLETE BREAKDOWN (10 BPS + DP) ===")
print(f"{'#':<3} | {'Symbol':<12} | {'Sector':<18} | {'Entry':<10} | {'Exit':<10} | {'Gross PnL':<10} | {'DP Cost':<8} | {'Total Cost':<10} | {'Net PnL':<10} | {'Reason'}")
print("-" * 110)

tot_dp = 0.0
for i, t in enumerate(trades, 1):
    sym = t["symbol"]
    sec = sym_to_sec.get(sym, "Unknown")
    ed = t["entry_date"]
    xd = t["exit_date"]
    gross = t["gross_pl"]
    exit_breakdown = t["exit_costs_breakdown"]
    dp_cost = exit_breakdown.get("dp_charges", 0.0) + (exit_breakdown.get("dp_charges", 0.0) * 0.18)
    tot_dp += dp_cost
    tot_c = t["total_costs"]
    net = t["net_pl"]
    reason = t["exit_reason"]
    print(f"{i:<3} | {sym:<12} | {sec:<18} | {ed} | {xd} | Rs {gross:>7.2f} | Rs {dp_cost:>5.2f} | Rs {tot_c:>8.2f} | Rs {net:>8.2f} | {reason}")

print("-" * 110)
print(f"Total DP Charges across 25 trades: Rs {tot_dp:.2f} (Rs {tot_dp/25:.2f} per trade)")

# Sector aggregation
sector_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "gross": 0.0, "net": 0.0, "costs": 0.0})
for t in trades:
    sec = sym_to_sec.get(t["symbol"], "Unknown")
    sector_stats[sec]["trades"] += 1
    if t["net_pl"] > 0:
        sector_stats[sec]["wins"] += 1
    sector_stats[sec]["gross"] += t["gross_pl"]
    sector_stats[sec]["net"] += t["net_pl"]
    sector_stats[sec]["costs"] += t["total_costs"]

print("\n=== SECTOR PERFORMANCE BREAKDOWN (COST-COMPLETE) ===")
print(f"{'Sector':<25} | {'Trades':<6} | {'Wins':<5} | {'Win Rate':<8} | {'Gross PnL':<10} | {'Costs':<10} | {'Net PnL':<10}")
print("-" * 85)
for sec, s in sorted(sector_stats.items(), key=lambda x: -x[1]["net"]):
    wr = (s["wins"] / s["trades"] * 100.0) if s["trades"] else 0.0
    print(f"{sec:<25} | {s['trades']:<6} | {s['wins']:<5} | {wr:>6.1f}%  | Rs {s['gross']:>7.2f} | Rs {s['costs']:>7.2f} | Rs {s['net']:>7.2f}")

# Leave-One-Out Analysis
print("\n=== LEAVE-ONE-SYMBOL-OUT NET P&L ANALYSIS ===")
tot_net_pnl = sum(t["net_pl"] for t in trades)
sym_net = defaultdict(float)
for t in trades:
    sym_net[t["symbol"]] += t["net_pl"]

print(f"Baseline Full Net P&L: Rs {tot_net_pnl:,.2f}")
for sym in sorted(sym_net.keys(), key=lambda s: sym_net[s]):
    loo_pnl = tot_net_pnl - sym_net[sym]
    print(f"  Excluding {sym:<12} ({sym_net[sym]:>+8.2f}): Remaining Net P&L = Rs {loo_pnl:>+8.2f}")

