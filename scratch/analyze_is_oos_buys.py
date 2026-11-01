import json
from collections import Counter
import pandas as pd

with open('scratch/multiyear_eval_cache.json', 'r') as f:
    d = json.load(f)

buys = d['all_buy_records']
is_buys = [b for b in buys if b['date'] <= '2026-03-31']
oos_buys = [b for b in buys if b['date'] > '2026-03-31']

print(f"Total Raw BUYs in In-Sample (<= 2026-03-31): {len(is_buys)}")
print(f"Total Raw BUYs in Out-of-Sample (> 2026-03-31): {len(oos_buys)}")

print("\nIn-Sample Rejections:")
is_reasons = Counter(b['reason'] for b in is_buys)
for r, cnt in is_reasons.most_common():
    print(f"  {r:35}: {cnt}")

print("\nOut-of-Sample Rejections:")
oos_reasons = Counter(b['reason'] for b in oos_buys)
for r, cnt in oos_reasons.most_common():
    print(f"  {r:35}: {cnt}")

# Let's check by month
df_buys = pd.DataFrame(buys)
df_buys['month'] = df_buys['date'].str.slice(0, 7)
print("\nRaw BUYs by month:")
for month, count in df_buys['month'].value_counts().sort_index().items():
    print(f"  {month}: {count:3} raw BUYs")

