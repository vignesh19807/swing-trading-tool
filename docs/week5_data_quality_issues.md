# Week 5 Data Quality Issues

## Purpose

This document records known data-quality limitations identified during
the Week 5 consolidated data audit.

These issues are documented rather than silently removed or fabricated.

---

## 1. Market Data

Market data audit:

- Stock universe: 50 stocks
- Daily records: 25,000
- Missing dates: 0
- Missing OHLCV values: 0
- Duplicate records: 0
- Orphan records: 0

### Status

Market data quality is currently acceptable for downstream technical
analysis.

---

## 2. Financial Data

Financial records:

- Stocks: 50
- Financial records: 280
- Duplicate company/quarter records: 0
- Orphan records: 0

### Missing Values

| Field | Missing | Coverage |
|---|---:|---:|
| Revenue | 32 | 88.57% |
| Net Profit | 32 | 88.57% |
| EPS | 33 | 88.21% |
| ROE | 205 | 26.79% |
| ROCE | 186 | 33.57% |
| Debt/Equity | 32 | 88.57% |
| Operating Margin | 0 | 100.00% |
| Net Margin | 0 | 100.00% |

### Important

Missing financial values must not be replaced with fabricated values.

The Logic Engineer must handle missing values explicitly when calculating
financial scores.

---

## 3. Negative Net Profit

The validation system identified three negative net-profit records.

These represent reported losses and should not automatically be treated
as data errors.

Current records:

- ADANIENT — 2026-03-31
- ADANIENT — 2026-06-30
- TMPV — 2025-12-31

### Handling

Negative profits are retained in the database and reported as warnings.

---

## 4. Database Integrity

The Week 5 audit confirmed:

- 50 companies present
- No duplicate financial periods
- No orphan financial records
- No duplicate market records
- Valid financial numeric fields
- Valid market OHLCV fields

---

## 5. Downstream Handling

The Data Engineer is responsible for:

- Collecting data
- Normalizing data
- Validating data
- Storing data
- Providing data through services

The Logic Engineer is responsible for:

- Handling missing financial values in scoring
- Financial analysis
- Technical analysis
- Financial scoring
- Technical scoring
- Trading decision logic

The Data Engineer must not fabricate missing financial values.

---

## Week 5 Audit Status

**CONSOLIDATED DATA AUDIT: PASSED**

Known financial-data limitations remain documented for downstream
processing.