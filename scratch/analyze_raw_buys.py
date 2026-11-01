import json
import numpy as np
import pandas as pd
from collections import Counter

with open('scratch/multiyear_eval_cache.json', 'r') as f:
    d = json.load(f)

buys = d['all_buy_records']
print(f"Total Raw BUY records: {len(buys)}")

reasons = Counter(b['reason'] for b in buys)
print("\nRejection Breakdown:")
for r, cnt in reasons.most_common():
    print(f"  {r:35}: {cnt:5} ({cnt/len(buys)*100:6.2f}%)")

# Let's inspect the 1407 PRICE_OUTSIDE_ENTRY_ZONE cases
outside_zone = [b for b in buys if b['reason'] == 'PRICE_OUTSIDE_ENTRY_ZONE']
print(f"\nPRICE_OUTSIDE_ENTRY_ZONE count: {len(outside_zone)}")

# Let's inspect the 305 INSUFFICIENT_RISK_REWARD_RATIO cases
insufficient_rr = [b for b in buys if b['reason'] == 'INSUFFICIENT_RISK_REWARD_RATIO']
print(f"INSUFFICIENT_RISK_REWARD_RATIO count: {len(insufficient_rr)}")
rr_values = [b['risk_reward_ratio'] for b in insufficient_rr if b['risk_reward_ratio'] is not None]
if rr_values:
    print(f"  RR values min: {min(rr_values):.4f}, median: {np.median(rr_values):.4f}, max: {max(rr_values):.4f}")
    print(f"  RR < 1.0: {sum(1 for x in rr_values if x < 1.0)}")
    print(f"  1.0 <= RR < 1.5: {sum(1 for x in rr_values if 1.0 <= x < 1.5)}")

# Let's inspect TARGET_BELOW_ENTRY_PRICE (84) and TARGET_BELOW_CURRENT_PRICE (18)
target_below_entry = [b for b in buys if b['reason'] == 'TARGET_BELOW_ENTRY_PRICE']
target_below_current = [b for b in buys if b['reason'] == 'TARGET_BELOW_CURRENT_PRICE']
print(f"TARGET_BELOW_ENTRY_PRICE count: {len(target_below_entry)}")
print(f"TARGET_BELOW_CURRENT_PRICE count: {len(target_below_current)}")

# Stock distribution among raw BUYs
stock_counts = Counter(b['symbol'] for b in buys)
print(f"\nUnique stocks generating raw BUYs: {len(stock_counts)} out of 52")
print("Top 10 stocks by raw BUY count:")
for sym, cnt in stock_counts.most_common(10):
    print(f"  {sym:15}: {cnt:4} raw BUYs")

print("Bottom 10 stocks by raw BUY count:")
for sym, cnt in stock_counts.most_common()[:-11:-1]:
    print(f"  {sym:15}: {cnt:4} raw BUYs")

# Dates distribution among raw BUYs
date_counts = Counter(b['date'] for b in buys)
print(f"\nUnique dates with at least one raw BUY: {len(date_counts)} out of 387")

