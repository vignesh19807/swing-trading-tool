# MASTER DATA QUALITY REPORT: HISTORICAL & REAL-TIME DATA PIPELINES

**Audit ID:** AUDIT-020  
**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Database File:** `database/swing_trading.db` (SHA-256: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`)  
**Audit Date:** 2026-10-30  
**Auditor:** Financial Data Engineer & Database Reliability Engineer  

---

## 1. Executive Summary

This master report provides an exhaustive, automated evaluation of historical market prices, quarterly fundamentals, technical indicators, and data ingestion resilience for the active 52-stock Indian equities universe.

| Data Dimension | Evaluated Scope | Identified Defects | Integrity Status |
| :--- | :--- | :--- | :--- |
| **Universe Definition** | 52 companies in `companies` | 0 duplicate symbols, 0 malformed tickers | **PASS** |
| **Price Data (`daily_prices`)** | 25,746 bars (2024-10-23 to 2026-10-23) | 0 non-positive prices, 0 geometric inconsistencies, 0 extreme return spikes | **PASS** |
| **Indicator Data (`technical_indicators`)** | 25,746 rows across 11 indicator fields | 0 unexpected NULLs; initial warmup window correctly preserves mathematical nulls | **PASS** |
| **Fundamental Data (`quarterly_results`)** | 260 rows (5 quarters x 52 stocks) | 260 / 260 rows lack regulatory publication dates (`NULL`) | **LIMITATION DOCUMENTED** |
| **Pipeline Resilience** | Provider failures, retries, duplicate ingestion | 28 automated resilience tests passed | **PASS** |

---

## 2. Universe Completeness & Symbol Normalization

- **Total Registered Companies:** 52
- **Exchange Affiliation:** National Stock Exchange of India (NSE)
- **Symbol Normalization:** All symbols are stored in clean uppercase text without exchange suffixes (e.g. `INFY`, `TCS`, `RELIANCE` rather than `INFY.NS`).
- **Classification Coverage:**
  - Macro Sectors (`sectors`): 17 distinct sectors
  - Granular Industries (`industries`): 45 distinct industries
  - Company-to-Sector Mappings: 52 / 52 complete (100% mapped)
  - Company-to-Industry Mappings: 52 / 52 complete (100% mapped)
- **Universe Limitation (`FND-002`):** The target platform design scope is 100 stocks (Nifty 100). The active database contains 52 large-cap stocks.

---

## 3. Historical Price Data Audit (`daily_prices`)

Across the entire dataset of 25,746 daily price records:

### 1. Numeric & Geometric Validity
- **Non-Positive Prices:**
  - `Open <= 0`: 0 records
  - `High <= 0`: 0 records
  - `Low <= 0`: 0 records
  - `Close <= 0`: 0 records
- **Geometric Inconsistencies:**
  - $High < Low$: 0 records
  - $High < Open$: 0 records
  - $High < Close$: 0 records
  - $Low > Open$: 0 records
  - $Low > Close$: 0 records
- **Negative Volume:** 0 records
- **Zero Volume:** 106 records (0.41% of bars; confirmed to represent trading holidays, partial sessions, or technical halts).

### 2. Temporal & Trading Calendar Alignment
- **Historical Span:** 496 unique trading dates (`2024-10-23` to `2026-10-23`).
- **Bar Count per Stock:**
  - 6 stocks have 496 bars (covering initial date `2024-10-23`).
  - 46 stocks have 495 bars (commencing on `2024-10-24`).
- **Missing Dates / Calendar Gaps:** Within each stock's active date range, there are zero missing days relative to the official NSE trading calendar.
- **Duplicate Prevention:** Exactly 0 duplicate `(company_id, date)` entries exist in `daily_prices`.

### 3. Corporate Action & Split Anomaly Audit
- An automated scan for single-day unadjusted price jumps $(|\Delta P / P| > 50\%)$ detected **0 anomalies**.
- Price series have been properly dividend-adjusted and split-adjusted by yfinance at ingestion.

---

## 4. Technical Indicator Quality Audit (`technical_indicators`)

The table `technical_indicators` contains 25,746 records, mapping 1:1 with `daily_prices`:

| Indicator Column | Total Rows | Valid Count | NULL Count | Reason for NULLs |
| :--- | :--- | :--- | :--- | :--- |
| `ema_20` | 25,746 | 25,746 | 0 | Warmup pre-calculated |
| `ema_50` | 25,746 | 25,746 | 0 | Warmup pre-calculated |
| `ema_200` | 25,746 | 25,746 | 0 | Warmup pre-calculated |
| `rsi` | 25,746 | 25,018 | 728 | 14-period Wilder smoothing window ($52 \times 14 = 728$) |
| `atr_14` | 25,746 | 25,070 | 676 | 13-period True Range initial smoothing window |
| `macd` | 25,746 | 25,746 | 0 | Fast/Slow EMA pre-calculated |
| `macd_signal` | 25,746 | 25,746 | 0 | Pre-calculated |
| `macd_histogram` | 25,746 | 25,746 | 0 | Pre-calculated |
| `technical_score` | 25,746 | 24,758 | 988 | Multi-indicator aggregation warmup period |

All NULL values are strictly confined to the mathematically mandatory warmup periods. There is zero evidence of data corruption or missing indicator rows.

---

## 5. Fundamental Data Integrity & The Publication Date Gap

The table `quarterly_results` contains 260 rows, providing exactly 5 quarters of financial statements for all 52 companies:
- Quarters covered: `2025-Q1`, `2025-Q2`, `2025-Q3`, `2025-Q4`, `2026-Q1`.
- Metrics per quarter: `revenue`, `net_profit`, `eps`, `roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin`.
- **Non-positive revenue:** 0 records.
- **NULL net profit:** 0 records.

### The Regulatory Filing Date Limitation (`FND-001`)
- **Status:** **260 out of 260 quarterly results have `publication_date IS NULL` (100.0% missing)**.
- **Operational Policy:** As established in `backend/data_pipeline/financial_service.py`, when `publication_date` is `NULL`, the platform enforces an empirical fallback of **45 calendar days post quarter-end** ($T_{\text{quarter\_end}} + 45 \text{ days}$), aligned with SEBI LODR Regulation 33.
- **Sensitivity Audit:** Lag sensitivity analysis across 45, 60, and 90-day assumptions in AUDIT-017 showed that trading decisions are invariant to these assumptions for the pilot universe. However, because actual historical announcement timestamps cannot be proven from this database, **the platform must not claim unconditional point-in-time regulatory certification**.

---

## 6. Pipeline Resilience & Error Handling

Automated tests verified the following ingestion guarantees:
1. **Duplicate Ingestion (`test_duplicate_update.py`):** Re-running daily update jobs does not create duplicate price or indicator rows (`INSERT OR REPLACE` / uniqueness constraints enforce idempotency).
2. **Provider Failures (`test_provider_failure.py`):** When Yahoo Finance / external API times out or returns malformed data, the pipeline catches exceptions, logs failures, and preserves existing data without corrupting database state.
3. **Failure Isolation (`test_stock_failure_isolation.py`):** A failure on one stock does not abort updates for remaining stocks.
4. **Retry Behavior (`test_failed_stock_retry.py`):** Failed stocks are tracked in failure logs and retried with exponential backoff.

---

## 7. Conclusion

The data engineering layer is robust, clean, and mathematically consistent. The two material data limitations are explicitly tracked:
1. `FND-001`: 100% missing regulatory publication timestamps in `quarterly_results`.
2. `FND-002`: Active universe covers 52 stocks instead of the 100-stock design target.

