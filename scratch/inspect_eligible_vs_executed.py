import json

with open('docs/audit_artifacts/audit_025_multiyear_results.json', 'r') as f:
    data = json.load(f)

sim = data['simulations']['full_horizon_10bps']
rejected = sim.get('rejected_signals', [])
print(f"Rejected signals in simulation: {len(rejected)}")
for r in rejected:
    print(r)

print("\n--- All 11 Eligible Signals ---")
eligible = data.get('eligible_signals_ledger', [])
print(f"Eligible signals: {len(eligible)}")
for i, s in enumerate(eligible, 1):
    print(f"{i}. {s['symbol']:12} on {s['date']} | Entry: [{s['entry_lower']}, {s['entry_upper']}] | SL: {s['stop_loss']} | Tgt: {s['target']} | RR: {s['risk_reward_ratio']}")

executed_trades = sim['all_trades']
executed_keys = {(t['symbol'], t['evaluation_date']) for t in executed_trades}
print(f"\nExecuted trades: {len(executed_trades)}")

print("\nUnexecuted eligible signals:")
for s in eligible:
    key = (s['symbol'], s['date'])
    if key not in executed_keys:
        print(f"  UNEXECUTED: {s['symbol']} on {s['date']}")

