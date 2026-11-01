import json
import sqlite3

with open('scratch/multiyear_eval_cache.json', 'r') as f:
    d = json.load(f)

buys = d['all_buy_records']
eligible = d['all_eligible_signals']

with open('docs/audit_artifacts/audit_025_multiyear_results.json', 'r') as f:
    res = json.load(f)

sim = res['simulations']['full_horizon_10bps']
executed = sim['all_trades']
executed_keys = {(t['symbol'], t['evaluation_date']) for t in executed}

print(f"Total raw buys: {len(buys)}")
print(f"Total eligible: {len(eligible)}")
print(f"Total executed: {len(executed)}")

# 1. Candidate that became an actual trade
trade_example = executed[0] # SUNPHARMA
print("\n--- Candidate that became an actual trade ---")
print(f"Symbol: {trade_example['symbol']}, Date: {trade_example['evaluation_date']}")
print(f"Entry: {trade_example['entry_price']}, Exit: {trade_example['exit_price']}, Net PL: {trade_example['net_pl']}")

# 2. Candidate that passed all entry conditions but was not executed
unexecuted = [s for s in eligible if (s['symbol'], s['evaluation_date']) not in executed_keys]
print("\n--- Candidate that passed all entry conditions but was not executed ---")
for u in unexecuted:
    print(f"Symbol: {u['symbol']}, Date: {u['evaluation_date']}, Entry zone: [{u['entry_lower']}, {u['entry_upper']}], SL: {u['stop_loss']}, Target: {u['target']}")

# 3. Candidate passing most filters but failing one final condition (e.g. RR ratio)
near_rr = [b for b in buys if b['reason'] == 'INSUFFICIENT_RISK_REWARD_RATIO' and b.get('risk_reward_ratio') is not None]
near_rr.sort(key=lambda x: -x['risk_reward_ratio'])
print("\n--- Candidate failing one final condition (near RR 1.50 threshold) ---")
for b in near_rr[:3]:
    print(f"Symbol: {b['symbol']}, Date: {b['date']}, RR: {b['risk_reward_ratio']:.4f}, Reason: {b['reason']}")

# 4. Candidate rejected by PRICE_OUTSIDE_ENTRY_ZONE barely
barely_outside = []
conn = sqlite3.connect('database/swing_trading.db')
c = conn.cursor()
for b in buys:
    if b['reason'] == 'PRICE_OUTSIDE_ENTRY_ZONE':
        c.execute("SELECT dp.close FROM daily_prices dp JOIN companies c ON c.id = dp.company_id WHERE c.symbol = ? AND dp.date = ?", (b['symbol'], b['date']))
        row = c.fetchone()
        if row:
            cp = row[0]
            eu = b['entry_upper']
            diff = (cp - eu) / eu * 100.0
            barely_outside.append((diff, b, cp))
conn.close()

barely_outside.sort(key=lambda x: x[0])
print("\n--- Candidate barely outside entry zone ---")
for diff, b, cp in barely_outside[:3]:
    print(f"Symbol: {b['symbol']}, Date: {b['date']}, Close: {cp:.2f}, Upper: {b['entry_upper']:.2f}, Exceeded by: {diff:.3f}%")

# 5. Candidate rejected by multiple conditions / missing financial data
# Let's check non-BUY records or stocks with missing data

