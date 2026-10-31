import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "docs/audit_artifacts/temp_multiyear_audit_025.db"
conn = sqlite3.connect(DB_PATH)

symbols = [r[0] for r in conn.execute("SELECT symbol FROM companies ORDER BY symbol").fetchall()]
print(f"Total symbols: {len(symbols)}")

# Load all daily prices
df_all = pd.read_sql("""
    SELECT c.symbol, dp.date, dp.close
    FROM daily_prices dp
    JOIN companies c ON c.id = dp.company_id
    WHERE dp.date >= '2025-04-01' AND dp.date <= '2026-10-23'
    ORDER BY c.symbol, dp.date ASC
""", conn)
conn.close()

# Check dates
dates = sorted(df_all["date"].unique())
print(f"Total dates: {len(dates)}")
print(f"Start date: {dates[0]}, End date: {dates[-1]}")

is_dates = [d for d in dates if d <= "2026-03-31"]
oos_dates = [d for d in dates if d >= "2026-04-01"]
pilot_dates = [d for d in dates if "2025-10-01" <= d <= "2026-03-31"]

print(f"IS dates ({len(is_dates)}): {is_dates[0]} to {is_dates[-1]}")
print(f"OOS dates ({len(oos_dates)}): {oos_dates[0]} to {oos_dates[-1]}")
print(f"Pilot dates ({len(pilot_dates)}): {pilot_dates[0]} to {pilot_dates[-1]}")

def get_period_returns(start_dt, end_dt):
    ret_dict = {}
    for sym in symbols:
        sub = df_all[(df_all["symbol"] == sym) & (df_all["date"] >= start_dt) & (df_all["date"] <= end_dt)]
        if not sub.empty:
            p_start = float(sub.iloc[0]["close"])
            p_end = float(sub.iloc[-1]["close"])
            ret_dict[sym] = (p_end - p_start) / p_start
    return pd.Series(ret_dict)

r_full = get_period_returns("2025-04-01", "2026-10-23")
r_is = get_period_returns("2025-04-01", "2026-03-31")
r_oos = get_period_returns("2026-04-01", "2026-10-23")
r_pilot = get_period_returns("2025-10-01", "2026-03-31")

print("\n--- Benchmark Returns Reproduction ---")
print(f"FULL:  mean={r_full.mean()*100:.2f}%, median={r_full.median()*100:.2f}%, std={r_full.std()*100:.2f}%")
print(f"IS:    mean={r_is.mean()*100:.2f}%, median={r_is.median()*100:.2f}%, std={r_is.std()*100:.2f}%")
print(f"OOS:   mean={r_oos.mean()*100:.2f}%, median={r_oos.median()*100:.2f}%, std={r_oos.std()*100:.2f}%")
print(f"PILOT: mean={r_pilot.mean()*100:.2f}%, median={r_pilot.median()*100:.2f}%, std={r_pilot.std()*100:.2f}%")

# Mathematical decomposition of the discrepancy:
# Why is mean(R_full) = +2.92% when mean(R_is) = +0.65% and mean(R_oos) = +1.11%?
# Notice:
# 1) Start of OOS is 2026-04-01 close, NOT 2026-03-31 close!
# Check overnight/session change between 2026-03-31 and 2026-04-01:
r_boundary = {}
for sym in symbols:
    p_31 = df_all[(df_all["symbol"] == sym) & (df_all["date"] == "2026-03-31")]["close"].values
    p_01 = df_all[(df_all["symbol"] == sym) & (df_all["date"] == "2026-04-01")]["close"].values
    if len(p_31) and len(p_01):
        r_boundary[sym] = (p_01[0] - p_31[0]) / p_31[0]
r_boundary = pd.Series(r_boundary)
print(f"\nBoundary session return (2026-03-31 to 2026-04-01): mean={r_boundary.mean()*100:.4f}%")

# 2) If continuous OOS from 2026-03-31 close to 2026-10-23 close:
r_oos_cont = get_period_returns("2026-03-31", "2026-10-23")
print(f"OOS continuous from 2026-03-31 close: mean={r_oos_cont.mean()*100:.4f}%")

# 3) Individual Stock Compounding:
# For stock i: 1 + R_full_i = (1 + R_is_i) * (1 + R_boundary_i) * (1 + R_oos_i)
# What is E[(1 + R_is)(1 + R_oos_cont)]?
# E[(1+X)(1+Y)] - 1 = E[X] + E[Y] + E[X*Y] = E[X] + E[Y] + E[X]*E[Y] + Cov(X, Y)!
cov_xy = np.cov(r_is, r_oos_cont)[0, 1]
print(f"Covariance Cov(R_IS, R_OOS_cont): {cov_xy:.6f} ({cov_xy*100:.4f}%)")
expected_full_from_parts = r_is.mean() + r_oos_cont.mean() + (r_is.mean() * r_oos_cont.mean()) + cov_xy
print(f"Mathematical decomposition: E[R_is] + E[R_oos_cont] + E[R_is]*E[R_oos_cont] + Cov = {expected_full_from_parts*100:.4f}%")
print(f"Actual mean(R_full): {r_full.mean()*100:.4f}%")

# 4) Equal-weight Portfolio Daily Index (Rebalanced Daily vs Buy-and-Hold):
# If an investor holds an equal-weighted portfolio rebalanced daily, what is the daily compounding return?
pivot_df = df_all.pivot(index="date", columns="symbol", values="close")
daily_rets = pivot_df.pct_change().dropna()
ew_daily = daily_rets.mean(axis=1)

ew_cum_full = (1 + ew_daily).prod() - 1
ew_cum_is = (1 + ew_daily.loc[:"2026-03-31"]).prod() - 1
ew_cum_oos = (1 + ew_daily.loc["2026-04-01":]).prod() - 1
ew_cum_pilot = (1 + ew_daily.loc["2025-10-01":"2026-03-31"]).prod() - 1

print("\n--- Daily Rebalanced Equal-Weight Index Returns ---")
print(f"FULL (Daily Rebal):  {ew_cum_full*100:.2f}%")
print(f"IS (Daily Rebal):    {ew_cum_is*100:.2f}%")
print(f"OOS (Daily Rebal):   {ew_cum_oos*100:.2f}%")
print(f"PILOT (Daily Rebal): {ew_cum_pilot*100:.2f}%")

