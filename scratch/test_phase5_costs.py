import sys
import os
sys.path.insert(0, os.path.abspath("."))

from backend.logic.cost_model import calculate_trade_costs
from backend.logic.backtest_specification import CostModelConfig
from scratch.run_audit_045_simulation import calculate_cost_complete_trade

cfg = CostModelConfig()

# Case 1: 100k buy leg
c1_stat = calculate_trade_costs(100.0, 1000, is_buy=True, config=cfg)
c1_comp = calculate_cost_complete_trade(100.0, 1000, is_buy=True, include_dp=True)

# Case 2: 100k sell leg
c2_stat = calculate_trade_costs(100.0, 1000, is_buy=False, config=cfg)
c2_comp = calculate_cost_complete_trade(100.0, 1000, is_buy=False, include_dp=True)

print("Case 1 (Buy 100k):")
print("  Statutory model:", c1_stat)
print("  Cost-complete (with DP check):", c1_comp)

print("\nCase 2 (Sell 100k):")
print("  Statutory model:", c2_stat)
print("  Cost-complete (with DP check):", c2_comp)

# Round-trip sum
rt_stat = c1_stat['total_costs'] + c2_stat['total_costs']
rt_comp = c1_comp['total_costs'] + c2_comp['total_costs']
print(f"\nRound-trip total (statutory): {rt_stat:.4f}")
print(f"Round-trip total (cost-complete with DP): {rt_comp:.4f}")

# Arithmetic check of reported figures in AUDIT-049:
b_rep = 118.62
s_rep = 119.55
sum_rep = b_rep + s_rep
print(f"\nAUDIT-049 stated: Buy={b_rep}, Sell={s_rep}")
print(f"Direct sum of stated rounded numbers: {sum_rep:.2f}")
print(f"Exact unrounded sum: {c1_comp['total_costs'] + c2_comp['total_costs']:.4f}")
print(f"Exact unrounded rounded to 2 decimals: {round(c1_comp['total_costs'] + c2_comp['total_costs'], 2):.2f}")

# Case 3: Complete buy/sell round trip with profit/loss
# Buy 500 shares @ 200 = 100k, Sell 500 shares @ 210 = 105k
c3_buy = calculate_cost_complete_trade(200.0, 500, is_buy=True, include_dp=True)
c3_sell = calculate_cost_complete_trade(210.0, 500, is_buy=False, include_dp=True)
gross_pnl = (210.0 - 200.0) * 500
total_costs_c3 = c3_buy['total_costs'] + c3_sell['total_costs']
net_pnl = gross_pnl - total_costs_c3
print(f"\nCase 3 (Round-trip trade 100k -> 105k): Gross={gross_pnl:.2f}, Costs={total_costs_c3:.2f}, Net={net_pnl:.2f}")

# Case 4: Partial exit
# Buy 1000 shares @ 100 = 100k, Sell 500 @ 105 = 52.5k
c4_buy = calculate_cost_complete_trade(100.0, 1000, is_buy=True, include_dp=True)
c4_sell_part = calculate_cost_complete_trade(105.0, 500, is_buy=False, include_dp=True)
print(f"\nCase 4 (Partial exit 500 sh @ 105): Sell Costs={c4_sell_part['total_costs']:.4f} (DP={c4_sell_part['dp_charges']})")

# Case 5: Multiple sell legs
# Second sell 500 @ 110 = 55k
c5_sell_part2 = calculate_cost_complete_trade(110.0, 500, is_buy=False, include_dp=True)
print(f"Case 5 (Second exit 500 sh @ 110): Sell Costs={c5_sell_part2['total_costs']:.4f} (DP={c5_sell_part2['dp_charges']})")
print(f"Total DP charges across 2 sell legs: {c4_sell_part['dp_charges'] + c5_sell_part2['dp_charges']:.2f}")

# Case 6: Invalid or zero-value transaction
c6_zero = calculate_trade_costs(0.0, 0, is_buy=True, config=cfg)
print(f"\nCase 6 (Zero transaction): {c6_zero}")

