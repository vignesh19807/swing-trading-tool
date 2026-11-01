import sqlite3
import pandas as pd
import json

conn = sqlite3.connect('database/swing_trading.db')
prices_df = pd.read_sql_query('SELECT dp.*, c.symbol FROM daily_prices dp JOIN companies c ON dp.company_id = c.id ORDER BY c.symbol, dp.date', conn)
conn.close()

from backend.data_pipeline.research_market_data_filter import detect_market_data_anomalies, KNOWN_EXCHANGE_HOLIDAYS

annotated = detect_market_data_anomalies(prices_df)

total_rows = len(annotated)
unique_syms = annotated['symbol'].nunique()
unique_dates = annotated['date'].nunique()

print(f"Total Rows: {total_rows}")
print(f"Unique Symbols: {unique_syms}")
print(f"Unique Dates: {unique_dates}")

# Classification counts
class_counts = annotated['anomaly_classification'].value_counts().to_dict()
print(f"\nAnomaly Classification Counts: {class_counts}")

# Breakdown of flat bars
flat_bars = annotated[(annotated['open'] == annotated['high']) & (annotated['high'] == annotated['low']) & (annotated['low'] == annotated['close'])]
print(f"\nTotal Flat Bars (O=H=L=C): {len(flat_bars)}")
print(f"  - On Known Holidays: {len(flat_bars[flat_bars['date'].isin(KNOWN_EXCHANGE_HOLIDAYS)])}")
print(f"  - On Other Sessions: {len(flat_bars[~flat_bars['date'].isin(KNOWN_EXCHANGE_HOLIDAYS)])}")

# Large discontinuities
large_moves = annotated[annotated['is_large_discontinuity']]
print(f"\nLarge Discontinuities (>25% move): {len(large_moves)}")
for idx, r in large_moves.iterrows():
    print(f"  - {r['symbol']} on {r['date']}: close={r['close']}, prev_day_diff")

# Per symbol breakdown of non-normal sessions
non_normal = annotated[annotated['anomaly_classification'] != 'NORMAL_SESSION']
print(f"\nNon-normal sessions by symbol (top 15):")
print(non_normal['symbol'].value_counts().head(15))

# Export machine-readable classification JSON
summary_report = {
    "total_rows_examined": total_rows,
    "unique_symbols": unique_syms,
    "unique_dates": unique_dates,
    "date_range": [annotated['date'].min(), annotated['date'].max()],
    "classification_counts": class_counts,
    "known_exchange_holidays": list(KNOWN_EXCHANGE_HOLIDAYS),
    "holiday_flat_bars_count": int(annotated['is_synthetic_holiday'].sum()),
    "stale_flat_bars_count": int(annotated['is_stale_flat_bar'].sum()),
    "large_discontinuities_count": int(annotated['is_large_discontinuity'].sum()),
    "inverted_ohlc_count": int(annotated['is_inverted_ohlc'].sum()),
    "non_positive_price_count": int(annotated['is_non_positive'].sum()),
    "per_symbol_anomaly_counts": non_normal['symbol'].value_counts().to_dict()
}

with open('docs/audit_artifacts/audit_048_market_data_classification.json', 'w') as f:
    json.dump(summary_report, f, indent=2)

print("\nSuccessfully exported docs/audit_artifacts/audit_048_market_data_classification.json")

