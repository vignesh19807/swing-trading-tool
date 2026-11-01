import os
import json

p = 'scratch/multiyear_eval_cache.json'
print(f"Exists: {os.path.exists(p)}")
if os.path.exists(p):
    with open(p, 'r') as f:
        d = json.load(f)
    print(f"Keys: {list(d.keys())}")
    print(f"total_sessions: {d['total_sessions']}")
    print(f"total_raw_buys: {d['total_raw_buys']}")
    print(f"rejections: {d['rejections']}")
    print(f"all_eligible_signals count: {len(d['all_eligible_signals'])}")
    print(f"all_buy_records count: {len(d['all_buy_records'])}")

