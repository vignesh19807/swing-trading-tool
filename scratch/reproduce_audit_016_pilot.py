"""
Reproduce the 5-stock pilot (TCS, INFY, HDFCBANK, RELIANCE, ITC)
over 2025-10-01 to 2026-03-31 on isolated temp_pilot_audit_017.db.
"""

import os
import sys
import shutil
import sqlite3
import json
import pandas as pd
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("."))

from pathlib import Path

PROD_DB = Path("database/swing_trading.db").resolve()
TEMP_DB = Path("docs/audit_artifacts/temp_pilot_audit_017.db").resolve()

# Create clean isolated copy
shutil.copyfile(PROD_DB, TEMP_DB)

import backend.data_pipeline.financial_service as fin_svc
import backend.data_pipeline.data_service as data_svc
import backend.data_pipeline.classification_service as class_svc
import backend.data_pipeline.backtest_result_service as backtest_svc
from backend.logic.signal_integration import run_signal_pipeline
from backend.engines.decision_engine import calculate_opportunity_score

# Patch all database access to TEMP_DB
patch.object(fin_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(data_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(class_svc, "DATABASE_PATH", TEMP_DB).start()
patch.object(backtest_svc, "DATABASE_PATH", TEMP_DB).start()

# Connect to get all distinct trading dates between 2025-10-01 and 2026-03-31
conn = sqlite3.connect(TEMP_DB)
cursor = conn.cursor()
cursor.execute("""
    SELECT DISTINCT date FROM daily_prices
    WHERE date >= '2025-10-01' AND date <= '2026-03-31'
    ORDER BY date
""")
trading_dates = [r[0] for r in cursor.fetchall()]
conn.close()

symbols = ["TCS", "INFY", "HDFCBANK", "RELIANCE", "ITC"]

print(f"Total trading days: {len(trading_dates)}")
print(f"Total stock-sessions: {len(trading_dates) * len(symbols)}")

all_signals = []
raw_buys = []

for date_str in trading_dates:
    for sym in symbols:
        try:
            signal = run_signal_pipeline(sym, evaluation_date=date_str)
            all_signals.append(signal)
            rec = signal.get("recommendation")
            if rec == "BUY":
                raw_buys.append(signal)
                print(f"[RAW BUY] {sym} on {date_str}: is_eligible={signal.get('is_eligible')} reason={signal.get('reason') or signal.get('trade_quality', {}).get('eligibility_reason')}")
        except Exception as e:
            print(f"Error on {sym} {date_str}: {e}")

print(f"\nTotal signals evaluated: {len(all_signals)}")
print(f"Total RAW BUYS: {len(raw_buys)}")
eligible_buys = [s for s in raw_buys if s.get("is_eligible")]
print(f"Total Eligible BUYS: {len(eligible_buys)}")

with open("scratch/audit_017_raw_buys.json", "w") as f:
    json.dump(raw_buys, f, indent=2, default=str)
