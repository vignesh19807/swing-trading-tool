import json
import pandas as pd
import numpy as np

# Load simulation results from docs/audit_artifacts/audit_025_multiyear_results.json
results_file = "docs/audit_artifacts/audit_025_multiyear_results.json"
with open(results_file, "r") as f:
    data = json.load(f)

sim = data["simulations"]["full_horizon_10bps"]
trades = sim["closed_trades"]
summary = sim["portfolio_summary"]
equity_curve = sim["equity_curve"]
open_pos = sim["open_positions"]

print(f"Total trades: {len(trades)}")
print(f"Open positions: {len(open_pos)}")
print(f"Equity curve length: {len(equity_curve)}")

# 1. Independently sum all trade net P&L, gross P&L, and costs
sum_gross_pl = sum(t["gross_pl"] for t in trades)
sum_entry_costs = sum(t["entry_costs"] for t in trades)
sum_exit_costs = sum(t["exit_costs"] for t in trades)
sum_total_costs = sum(t["total_costs"] for t in trades)
sum_net_pl = sum(t["net_pl"] for t in trades)
sum_reported_pl = sum(t["pl"] for t in trades)

print("\n--- Trade Level Sums ---")
print(f"Sum Gross P&L:       Rs. {sum_gross_pl:.4f}")
print(f"Sum Entry Costs:     Rs. {sum_entry_costs:.4f}")
print(f"Sum Exit Costs:      Rs. {sum_exit_costs:.4f}")
print(f"Sum Total Costs:     Rs. {sum_total_costs:.4f}")
print(f"Sum Net P&L:         Rs. {sum_net_pl:.4f}")
print(f"Sum 'pl' field:      Rs. {sum_reported_pl:.4f}")

print("\n--- Portfolio Summary Reconciliation ---")
print(f"Reported Gross P&L:  Rs. {summary['total_gross_pl']:.4f} (Diff: {abs(summary['total_gross_pl'] - sum_gross_pl):.6f})")
print(f"Reported Costs:      Rs. {summary['total_costs']:.4f} (Diff: {abs(summary['total_costs'] - sum_total_costs):.6f})")
print(f"Reported Net P&L:    Rs. {summary['total_net_pl']:.4f} (Diff: {abs(summary['total_net_pl'] - sum_net_pl):.6f})")

initial_capital = summary["initial_capital"]
expected_cash = initial_capital + sum_net_pl
print(f"Initial Capital:     Rs. {initial_capital:.2f}")
print(f"Calculated End Cash: Rs. {expected_cash:.4f}")
print(f"Reported Final Cash: Rs. {summary['final_cash']:.4f} (Diff: {abs(summary['final_cash'] - expected_cash):.6f})")
print(f"Reported Final Eq:   Rs. {summary['final_equity']:.4f} (Diff: {abs(summary['final_equity'] - expected_cash):.6f})")

# 2. Verify Trade Details
print("\n--- Trade Ledger Verification ---")
trade_ids = set()
for idx, t in enumerate(trades, 1):
    tid = t["trade_id"]
    sym = t["symbol"]
    qty = t["quantity"]
    ep = t["entry_price"]
    xp = t["exit_price"]
    ed = t["entry_date"]
    xd = t["exit_date"]
    eval_d = t["evaluation_date"]
    
    # Check trade_id uniqueness
    assert tid not in trade_ids, f"Duplicate trade ID: {tid}"
    trade_ids.add(tid)
    
    # Chronological checks
    assert eval_d < ed, f"Evaluation date {eval_d} not before entry {ed}"
    assert ed <= xd, f"Entry date {ed} after exit date {xd}"
    
    # Sizing check: whole shares
    assert isinstance(qty, int), f"Quantity {qty} not integer"
    assert qty == int(np.floor((initial_capital * 0.20) / ep)), f"Quantity {qty} mismatch for allocated capital"
    
    # P&L arithmetic: gross = (xp - ep) * qty
    calc_gross = (xp - ep) * qty
    gross_diff = abs(calc_gross - t["gross_pl"])
    assert gross_diff < 1e-4, f"Gross P&L mismatch: calc {calc_gross} vs {t['gross_pl']}"
    
    # Net = gross - costs
    calc_net = calc_gross - t["total_costs"]
    net_diff = abs(calc_net - t["net_pl"])
    assert net_diff < 1e-4, f"Net P&L mismatch: calc {calc_net} vs {t['net_pl']}"
    
    # Total costs = entry + exit
    cost_diff = abs(t["entry_costs"] + t["exit_costs"] - t["total_costs"])
    assert cost_diff < 1e-4, f"Cost sum mismatch: {t['entry_costs']} + {t['exit_costs']} != {t['total_costs']}"
    
    print(f"Trade {idx}: {tid} | {sym} Qty:{qty} Entry:{ed} @ {ep:.2f} Exit:{xd} @ {xp:.2f} [{t['exit_reason']}] Net: Rs. {t['net_pl']:.2f}")

# Check for overlapping positions in same symbol
sym_positions = {}
for t in trades:
    sym = t["symbol"]
    if sym in sym_positions:
        prev_xd = sym_positions[sym]
        assert t["entry_date"] > prev_xd, f"Overlapping position in {sym}: prev exit {prev_xd}, new entry {t['entry_date']}"
    sym_positions[sym] = t["exit_date"]
print("\nZero overlapping positions for the same symbol: VERIFIED")

# 3. Verify Maximum Drawdown from daily equity curve
eq_df = pd.DataFrame(equity_curve)
eq_df["peak"] = eq_df["equity"].cummax()
eq_df["drawdown"] = (eq_df["equity"] - eq_df["peak"]) / eq_df["peak"]
max_dd_calc = abs(eq_df["drawdown"].min()) * 100
peak_eq_calc = eq_df["peak"].max()

print("\n--- Equity Curve & Drawdown Verification ---")
print(f"Calculated Peak Equity: Rs. {peak_eq_calc:.2f}")
print(f"Reported Peak Equity:   Rs. {summary['peak_equity']:.2f} (Diff: {abs(summary['peak_equity'] - peak_eq_calc):.4f})")
print(f"Calculated Max DD:      {max_dd_calc:.4f}%")
print(f"Reported Max DD:        {summary['max_drawdown_pct']:.4f}% (Diff: {abs(summary['max_drawdown_pct'] - max_dd_calc):.6f})")

# Check trough date and peak date of Max DD
trough_idx = eq_df["drawdown"].idxmin()
trough_row = eq_df.loc[trough_idx]
peak_prior_to_trough = eq_df.loc[:trough_idx]["equity"].max()
peak_idx = eq_df.loc[:trough_idx]["equity"].idxmax()
peak_row = eq_df.loc[peak_idx]

print(f"Drawdown Peak Date:   {peak_row.get('date', peak_idx)} @ Rs. {peak_row['equity']:.2f}")
print(f"Drawdown Trough Date: {trough_row.get('date', trough_idx)} @ Rs. {trough_row['equity']:.2f}")
print(f"Peak to Trough Loss:  Rs. {peak_row['equity'] - trough_row['equity']:.2f} ({(peak_row['equity'] - trough_row['equity'])/peak_row['equity']*100:.4f}%)")
