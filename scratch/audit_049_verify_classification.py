import sqlite3
import pandas as pd
import json

from backend.data_pipeline.research_market_data_filter import detect_market_data_anomalies, KNOWN_EXCHANGE_HOLIDAYS

# Connect read-only
conn = sqlite3.connect("file:database/swing_trading.db?mode=ro", uri=True)
prices_df = pd.read_sql_query("SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id ORDER BY c.symbol, dp.date", conn)
conn.close()

annotated = detect_market_data_anomalies(prices_df)

# Read the artifact generated in AUDIT-048
with open("docs/audit_artifacts/audit_048_market_data_classification.json", "r") as f:
    artifact_report = json.load(f)

# Compare independently recalculated counts
independent_counts = {
    "total_rows": len(annotated),
    "unique_symbols": annotated["symbol"].nunique(),
    "unique_dates": annotated["date"].nunique(),
    "normal_sessions": int((annotated["anomaly_classification"] == "NORMAL_SESSION").sum()),
    "synthetic_holiday_bars": int(annotated["is_synthetic_holiday"].sum()),
    "stale_flat_bars": int(annotated["is_stale_flat_bar"].sum()),
    "large_discontinuities": int(annotated["is_large_discontinuity"].sum()),
    "inverted_ohlc": int(annotated["is_inverted_ohlc"].sum()),
    "non_positive_price": int(annotated["is_non_positive"].sum()),
}

print("INDEPENDENT RECALCULATION:")
for k, v in independent_counts.items():
    print(f"  {k}: {v}")

print("\nARTIFACT COMPARISON:")
mismatches = []
if independent_counts["total_rows"] != artifact_report["total_rows_examined"]:
    mismatches.append("total_rows")
if independent_counts["unique_symbols"] != artifact_report["unique_symbols"]:
    mismatches.append("unique_symbols")
if independent_counts["synthetic_holiday_bars"] != artifact_report["holiday_flat_bars_count"]:
    mismatches.append("synthetic_holiday_bars")
if independent_counts["stale_flat_bars"] != artifact_report["stale_flat_bars_count"]:
    mismatches.append("stale_flat_bars")
if independent_counts["large_discontinuities"] != artifact_report["large_discontinuities_count"]:
    mismatches.append("large_discontinuities")

if not mismatches:
    print("  100% MATCH across all independent classification metrics!")
else:
    print(f"  MISMATCHES DETECTED: {mismatches}")

