import json

with open("docs/audit_artifacts/audit_043_comparative_results.json", "r") as f:
    d = json.load(f)
sp_trades = d["config_c_pullback"]["trades"]

# 1. By Symbol
sym_stats = {}
for t in sp_trades:
    s = t["symbol"]
    sym_stats.setdefault(s, {"trades": 0, "wins": 0, "net_pnl": 0.0})
    sym_stats[s]["trades"] += 1
    if t.get("net_pl", 0) > 0:
        sym_stats[s]["wins"] += 1
    sym_stats[s]["net_pnl"] += t.get("net_pl", 0)

print("=== SUPPORT PULLBACK BY SYMBOL ===")
for s, stats in sorted(sym_stats.items(), key=lambda x: -x[1]["net_pnl"]):
    t_cnt = stats["trades"]
    w_cnt = stats["wins"]
    pnl = stats["net_pnl"]
    print(f"  {s:12}: {t_cnt} trades | {w_cnt} wins | Net PnL: Rs {pnl:,.2f}")

top_sym = "SHRIRAMFIN"
total_pnl = sum(t["net_pl"] for t in sp_trades)
shriram_pnl = sym_stats[top_sym]["net_pnl"]
total_ex_shriram = sum(t["net_pl"] for t in sp_trades if t["symbol"] != top_sym)
print(f"\nSHRIRAMFIN net PnL: Rs {shriram_pnl:,.2f} out of total Rs {total_pnl:,.2f}")
print(f"Total Net PnL excluding SHRIRAMFIN: Rs {total_ex_shriram:,.2f}")

# 2. Holding Days
holding_days = [t.get("holding_days", 0) for t in sp_trades]
avg_holding = sum(holding_days) / len(holding_days) if holding_days else 0
print(f"Average Holding Period: {avg_holding:.1f} days (min: {min(holding_days)}, max: {max(holding_days)})")

# 3. Quarterly breakdown
from collections import defaultdict
q_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "net_pnl": 0.0})
for t in sp_trades:
    ed = t["entry_date"]
    # e.g. 2025-05-30 -> 2025-Q2
    year = ed[:4]
    month = int(ed[5:7])
    q = (month - 1) // 3 + 1
    q_str = f"{year}-Q{q}"
    q_stats[q_str]["trades"] += 1
    if t.get("net_pl", 0) > 0:
        q_stats[q_str]["wins"] += 1
    q_stats[q_str]["net_pnl"] += t.get("net_pl", 0)

print("\n=== SUPPORT PULLBACK BY CALENDAR QUARTER ===")
for q_str in sorted(q_stats.keys()):
    qs = q_stats[q_str]
    print(f"  {q_str}: {qs['trades']} trades | {qs['wins']} wins | Net PnL: Rs {qs['net_pnl']:,.2f}")

