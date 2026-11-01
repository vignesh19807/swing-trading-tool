import json
import sqlite3

with open('docs/audit_artifacts/audit_025_multiyear_results.json', 'r') as f:
    data = json.load(f)

sim = data['simulations']['full_horizon_10bps']
trades = sim['all_trades']

print(f"Total trades: {len(trades)}")
total_gross = sum(t['gross_pl'] for t in trades)
total_costs = sum(t['total_costs'] for t in trades)
total_net = sum(t['net_pl'] for t in trades)
wins = [t for t in trades if t['net_pl'] > 0]
losses = [t for t in trades if t['net_pl'] <= 0]

print(f"Wins: {len(wins)}, Losses: {len(losses)}, Win rate: {len(wins)/len(trades)*100:.2f}%")
print(f"Gross PL: {total_gross:.4f}")
print(f"Total Costs: {total_costs:.4f}")
print(f"Net PL: {total_net:.4f}")

for i, t in enumerate(trades, 1):
    print(f"{i}. {t['symbol']:12} {t['entry_date']} -> {t['exit_date']} | Qty: {t['quantity']:3} | Entry: {t['entry_price']:9.2f} | Exit: {t['exit_price']:9.2f} | Gross: {t['gross_pl']:9.2f} | Costs: {t['total_costs']:6.2f} | Net: {t['net_pl']:9.2f} | Reason: {t['exit_reason']}")

print("\n--- In-Sample vs Out-of-Sample ---")
is_trades = [t for t in trades if t['entry_date'] <= '2026-03-31']
oos_trades = [t for t in trades if t['entry_date'] > '2026-03-31']

print(f"In-Sample Trades (<= 2026-03-31): {len(is_trades)}")
for t in is_trades:
    print(f"  {t['symbol']} {t['entry_date']} -> {t['exit_date']}: Net PL = {t['net_pl']:.2f}")
print(f"  IS Net PL: {sum(t['net_pl'] for t in is_trades):.2f}")

print(f"\nOut-of-Sample Trades (> 2026-03-31): {len(oos_trades)}")
for t in oos_trades:
    print(f"  {t['symbol']} {t['entry_date']} -> {t['exit_date']}: Net PL = {t['net_pl']:.2f}")
print(f"  OOS Net PL: {sum(t['net_pl'] for t in oos_trades):.2f}")

print("\n--- Cost Sensitivity ---")
for sim_key, sim_val in data['simulations'].items():
    s_trades = sim_val.get('all_trades', [])
    s_net = sum(t['net_pl'] for t in s_trades)
    s_gross = sum(t['gross_pl'] for t in s_trades)
    s_costs = sum(t['total_costs'] for t in s_trades)
    print(f"Sim {sim_key:22}: Trades={len(s_trades)}, Gross={s_gross:9.2f}, Costs={s_costs:6.2f}, Net={s_net:9.2f}")

# Check daily prices & indicators in database
conn = sqlite3.connect('database/swing_trading.db')
cursor = conn.cursor()

cursor.execute("SELECT count(*) FROM companies")
companies_count = cursor.fetchone()[0]

cursor.execute("SELECT count(DISTINCT company_id) FROM daily_prices")
symbols_count = cursor.fetchone()[0]

cursor.execute("SELECT count(DISTINCT date) FROM daily_prices")
dates_count = cursor.fetchone()[0]

cursor.execute("SELECT min(date), max(date) FROM daily_prices")
min_date, max_date = cursor.fetchone()

cursor.execute("SELECT count(*) FROM daily_prices")
price_rows = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM technical_indicators")
ti_rows = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM quarterly_results")
qr_rows = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM quarterly_results WHERE publication_date IS NULL")
qr_null_pub = cursor.fetchone()[0]

print(f"\n--- Database Summary ---")
print(f"Companies count: {companies_count}")
print(f"Distinct company_ids in daily_prices: {symbols_count}")
print(f"Distinct Dates: {dates_count} ({min_date} to {max_date})")
print(f"daily_prices rows: {price_rows}")
print(f"technical_indicators rows: {ti_rows}")
print(f"quarterly_results rows: {qr_rows} (null publication_date: {qr_null_pub})")

# Inverted prices check
cursor.execute("SELECT count(*) FROM daily_prices WHERE high < low OR high < open OR high < close OR low > open OR low > close")
inverted_rows = cursor.fetchone()[0]
print(f"Inverted OHLC rows: {inverted_rows}")

cursor.execute("SELECT count(*) FROM daily_prices WHERE open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 OR volume < 0")
invalid_price_rows = cursor.fetchone()[0]
print(f"Invalid price/volume rows: {invalid_price_rows}")

# Null indicator check
cursor.execute("SELECT count(*) FROM technical_indicators WHERE ema_20 IS NULL OR rsi IS NULL")
null_ti = cursor.fetchone()[0]
print(f"Null critical indicators: {null_ti}")

conn.close()
