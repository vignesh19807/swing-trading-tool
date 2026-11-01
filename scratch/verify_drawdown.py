import json

with open('docs/audit_artifacts/audit_025_multiyear_results.json', 'r') as f:
    data = json.load(f)

sim = data['simulations']['full_horizon_10bps']
eq_curve = sim['equity_curve']
print(f"Equity curve points: {len(eq_curve)}")

# Find peak, trough, max drawdown
peak = 100000.0
max_dd = 0.0
peak_date = None
trough_date = None

for pt in eq_curve:
    d = pt['date']
    eq = pt['equity']
    if eq > peak:
        peak = eq
        p_date = d
    dd = (peak - eq) / peak
    if dd > max_dd:
        max_dd = dd
        peak_date = p_date
        trough_date = d
        trough_eq = eq
        peak_val = peak

print(f"Initial equity: {eq_curve[0]['equity']:.2f}")
print(f"Final equity: {eq_curve[-1]['equity']:.2f}")
print(f"Peak Equity: {peak_val:.2f} on {peak_date}")
print(f"Trough Equity: {trough_eq:.2f} on {trough_date}")
print(f"Max Drawdown (from peak): {max_dd*100:.4f}%")

# Max drawdown from initial capital 100,000:
min_eq = min(pt['equity'] for pt in eq_curve)
print(f"Min Equity: {min_eq:.2f}, Drawdown from 100k capital: {(100000.0 - min_eq)/100000.0*100:.4f}%")
