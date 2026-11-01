import json
import sqlite3
from collections import Counter

# Load multiyear eval cache
with open('scratch/multiyear_eval_cache.json', 'r') as f:
    cache = json.load(f)

# Load master multiyear results
with open('docs/audit_artifacts/audit_025_multiyear_results.json', 'r') as f:
    res = json.load(f)

sim = res['simulations']['full_horizon_10bps']

total_sessions = cache['total_sessions']
total_raw_buys = cache['total_raw_buys']
rejections = cache['rejections']
eligible_signals = cache['all_eligible_signals']
executed_trades = sim['all_trades']
rejected_sim = sim.get('rejected_signals', [])

print("=== BASELINE METRICS REPRODUCTION ===")
print(f"Total Evaluated Stock-Sessions: {total_sessions}")
print(f"Total Raw BUY Candidates: {total_raw_buys}")
print("Rejection Breakdown:")
for r, cnt in sorted(rejections.items(), key=lambda x: -x[1]):
    print(f"  {r:35}: {cnt:5} ({cnt/total_raw_buys*100:6.2f}%)")

print(f"Total Rejected BUY Signals: {sum(rejections.values())}")
print(f"Total Eligible BUY Signals: {len(eligible_signals)}")
print(f"Rejection reconciliation check: {sum(rejections.values()) + len(eligible_signals)} == {total_raw_buys} -> {sum(rejections.values()) + len(eligible_signals) == total_raw_buys}")

print(f"\nEligible Signals reaching Portfolio Simulator: {len(eligible_signals)}")
print(f"Signals Blocked by Portfolio Constraints: {len(rejected_sim)}")
for r in rejected_sim:
    print(f"  Blocked: {r['symbol']} on {r['date']} ({r['reason']})")

print(f"Executed Trades: {len(executed_trades)}")
print(f"Execution reconciliation check: {len(executed_trades)} + {len(rejected_sim)} == {len(eligible_signals)} -> {len(executed_trades) + len(rejected_sim) == len(eligible_signals)}")

# Open positions at end of backtest:
open_positions = sim.get('open_positions', [])
print(f"Open Positions at end of backtest: {len(open_positions)}")

