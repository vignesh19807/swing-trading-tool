"""
AUDIT-017: Phase 4 - Verify the 45-day fallback and run lag sensitivity analysis (45, 60, 90 days).
"""

import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("."))

PROD_DB = Path("database/swing_trading.db").resolve()
TEMP_DB = Path("docs/audit_artifacts/temp_pilot_audit_017.db").resolve()

# Connect to check publication timestamp coverage
conn = sqlite3.connect(TEMP_DB)
cur = conn.cursor()
cur.execute("SELECT COUNT(1) FROM quarterly_results WHERE publication_date IS NOT NULL AND publication_date != ''")
verified_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(1) FROM quarterly_results WHERE publication_date IS NULL OR publication_date = ''")
missing_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(1) FROM quarterly_results")
total_count = cur.fetchone()[0]

# Dates in 5-stock universe
symbols = ["TCS", "INFY", "HDFCBANK", "RELIANCE", "ITC"]
cur.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= '2025-10-01' AND date <= '2026-03-31' ORDER BY date")
trading_dates = [r[0] for r in cur.fetchall()]
conn.close()

print(f"Total quarterly records: {total_count}")
print(f"Verified publication timestamps: {verified_count} ({verified_count/total_count*100:.1f}%)")
print(f"Missing publication timestamps: {missing_count} ({missing_count/total_count*100:.1f}%)")

import backend.data_pipeline.financial_service as fin_svc
import backend.data_pipeline.data_service as data_svc
import backend.data_pipeline.classification_service as class_svc
import backend.data_pipeline.backtest_result_service as backtest_svc
from backend.logic.signal_integration import run_signal_pipeline

patch.object(fin_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(data_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(class_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(backtest_svc, "DATABASE_PATH", TEMP_DB).start()

lags = [45, 60, 90]
sensitivity_results = {}

for lag in lags:
    print(f"\n--- Testing Reporting Lag Assumption: {lag} Days ---")
    # Patch default reporting_lag_days in get_financial_data
    orig_get_fin = fin_svc.get_financial_data
    def make_lag_fin(lag_days):
        def custom_get_fin(symbol, evaluation_date=None, reporting_lag_days=lag_days):
            return orig_get_fin(symbol, evaluation_date=evaluation_date, reporting_lag_days=lag_days)
        return custom_get_fin

    fin_svc.get_financial_data = make_lag_fin(lag)
    
    raw_buys = []
    eligible_trades = []
    
    for date_str in trading_dates:
        for sym in symbols:
            try:
                sig = run_signal_pipeline(sym, evaluation_date=date_str)
                if sig.get("recommendation") == "BUY":
                    raw_buys.append({
                        "symbol": sym,
                        "date": date_str,
                        "is_eligible": sig.get("is_eligible"),
                        "reason": sig.get("reason") or sig.get("trade_quality", {}).get("eligibility_reason")
                    })
                    if sig.get("is_eligible"):
                        eligible_trades.append(sig)
            except Exception as e:
                pass

    sensitivity_results[lag] = {
        "raw_buys_count": len(raw_buys),
        "eligible_trades_count": len(eligible_trades),
        "raw_buys": raw_buys
    }
    print(f"Lag {lag}d: Raw BUYs = {len(raw_buys)}, Eligible = {len(eligible_trades)}")
    for b in raw_buys:
        print(f"  {b['symbol']} on {b['date']}: {b['reason']}")

fin_svc.get_financial_data = orig_get_fin

