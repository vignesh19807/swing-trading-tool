import json
import sqlite3
import pandas as pd

with open('scratch/multiyear_eval_cache.json', 'r') as f:
    d = json.load(f)

buys = d['all_buy_records']
outside_zone = [b for b in buys if b['reason'] == 'PRICE_OUTSIDE_ENTRY_ZONE']

# We need current_price for these records.
# Let's get current_price from daily_prices table in database/swing_trading.db
conn = sqlite3.connect('database/swing_trading.db')
c = conn.cursor()

above_upper = 0
below_lower = 0
ratios = []

for b in outside_zone:
    sym = b['symbol']
    dt = b['date']
    c.execute("""
        SELECT dp.close 
        FROM daily_prices dp
        JOIN companies c ON c.id = dp.company_id
        WHERE c.symbol = ? AND dp.date = ?
    """, (sym, dt))
    row = c.fetchone()
    if row:
        cp = row[0]
        el = b['entry_lower']
        eu = b['entry_upper']
        if cp > eu:
            above_upper += 1
            # How far above upper?
            diff_pct = (cp - eu) / eu * 100.0
            ratios.append(diff_pct)
        elif cp < el:
            below_lower += 1

conn.close()

print(f"Total PRICE_OUTSIDE_ENTRY_ZONE: {len(outside_zone)}")
print(f"Price ABOVE entry_upper: {above_upper} ({above_upper/len(outside_zone)*100:.2f}%)")
print(f"Price BELOW entry_lower: {below_lower} ({below_lower/len(outside_zone)*100:.2f}%)")

if ratios:
    ratios.sort()
    import numpy as np
    print(f"Percentage above entry_upper: min = {min(ratios):.2f}%, p25 = {np.percentile(ratios, 25):.2f}%, median = {np.median(ratios):.2f}%, p75 = {np.percentile(ratios, 75):.2f}%, max = {max(ratios):.2f}%")

