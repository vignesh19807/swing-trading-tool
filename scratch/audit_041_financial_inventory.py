import sqlite3
import pandas as pd
from collections import Counter

conn = sqlite3.connect('database/swing_trading.db')

# 1. Inspect table quarterly_results
df_qr = pd.read_sql("""
    SELECT qr.id, c.symbol, c.company_name, c.sector, qr.quarter, 
           qr.revenue, qr.net_profit, qr.eps, qr.roe, qr.roce, 
           qr.debt_equity, qr.operating_margin, qr.net_margin, 
           qr.publication_date
    FROM quarterly_results qr
    JOIN companies c ON c.id = qr.company_id
    ORDER BY c.symbol, qr.quarter
""", conn)

print(f"Total quarterly records: {len(df_qr)}")
print(f"Distinct symbols: {df_qr['symbol'].nunique()}")
print(f"Distinct quarters: {df_qr['quarter'].unique().tolist()}")

# Metric completeness
metrics = ['revenue', 'net_profit', 'eps', 'roe', 'roce', 'debt_equity', 'operating_margin', 'net_margin']
print("\nMetric Null Counts across all 260 rows:")
for m in metrics:
    nulls = df_qr[m].isnull().sum()
    print(f"  {m:20}: {nulls} nulls ({nulls/len(df_qr)*100:.1f}%)")

# Publication date analysis
pub_nulls = df_qr['publication_date'].isnull().sum()
print(f"\npublication_date NULL count: {pub_nulls} out of {len(df_qr)} ({pub_nulls/len(df_qr)*100:.1f}%)")

# Quarters per symbol
q_per_sym = df_qr.groupby('symbol')['quarter'].count()
print(f"Quarters per symbol: min={q_per_sym.min()}, max={q_per_sym.max()}, median={q_per_sym.median()}")
print(f"Distribution of quarters per symbol: {Counter(q_per_sym.values)}")

# Quarter dates mapping
# Standard Indian fiscal quarters:
# 2025-Q1: Ended 2025-03-31 -> 45-day lag -> Eligible 2025-05-15
# 2025-Q2: Ended 2025-06-30 -> 45-day lag -> Eligible 2025-08-14
# 2025-Q3: Ended 2025-09-30 -> 45-day lag -> Eligible 2025-11-14
# 2025-Q4: Ended 2025-12-31 -> 45-day lag -> Eligible 2026-02-14
# 2026-Q1: Ended 2026-03-31 -> 45-day lag -> Eligible 2026-05-15

quarter_meta = [
    {"quarter": "2025-Q1", "period_start": "2025-01-01", "period_end": "2025-03-31", "eligibility_fallback": "2025-05-15"},
    {"quarter": "2025-Q2", "period_start": "2025-04-01", "period_end": "2025-06-30", "eligibility_fallback": "2025-08-14"},
    {"quarter": "2025-Q3", "period_start": "2025-07-01", "period_end": "2025-09-30", "eligibility_fallback": "2025-11-14"},
    {"quarter": "2025-Q4", "period_start": "2025-10-01", "period_end": "2025-12-31", "eligibility_fallback": "2026-02-14"},
    {"quarter": "2026-Q1", "period_start": "2026-01-01", "period_end": "2026-03-31", "eligibility_fallback": "2026-05-15"},
]
print("\nQuarter Metadata & Statutory 45-Day Availability:")
for q in quarter_meta:
    print(f"  {q['quarter']}: Period {q['period_start']} to {q['period_end']} -> Fallback Eligibility Date: {q['eligibility_fallback']}")

conn.close()
