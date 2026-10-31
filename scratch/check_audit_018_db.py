import sqlite3
import pandas as pd

conn = sqlite3.connect("docs/audit_artifacts/temp_pilot_audit_018.db")
print("=== Backtest Runs ===")
df_runs = pd.read_sql("SELECT * FROM backtest_runs", conn)
print(df_runs.to_string())

print("\n=== Backtest Trades ===")
df_trades = pd.read_sql("SELECT * FROM backtest_trades", conn)
print(df_trades.to_string())

print("\n=== Equity Curve Count ===")
cnt = conn.execute("SELECT count(*) FROM backtest_equity_curve WHERE run_id = 'audit_018_52stock_reproduction'").fetchone()[0]
print(f"Equity curve points for audit_018_52stock_reproduction: {cnt}")

