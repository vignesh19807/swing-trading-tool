# Week 15 — Data Quality Monitoring Guide & Operating Procedure

**Swing Trading Intelligence Platform | Data Engineering Layer**  
**Specification Version**: 1.0.0 (Week 15)  
**Quality Monitor Script**: `backend/data_pipeline/week15_quality_monitor.py`  
**Report Output**: `reports/week15_quality_monitoring_report.json`

---

## 1. Quality Monitoring Architecture

The Week 15 Data Quality Monitor provides an automated, recurring audit layer designed to verify database integrity, cross-dataset synchronization, and point-in-time historical safety before data is consumed by downstream engines.

```
                    ┌──────────────────────────────┐
                    │    Quality Monitor Runner    │
                    │ (week15_quality_monitor.py)  │
                    └──────────────┬───────────────┘
                                   │ Executes 9 Core Audit Rules
                    ┌──────────────▼───────────────┐
                    │     Audit Classification     │
                    ├──────────────┬───────────────┤
                    │     PASS     │ Zero defects  │
                    │   WARNING    │ Non-blocking  │
                    │   BLOCKING   │ Hard failure  │
                    └──────────────┬───────────────┘
                                   │ Generates Reports
            ┌──────────────────────┴──────────────────────┐
            ▼                                             ▼
  CLI Formatted Summary                   reports/week15_quality_monitoring_report.json
```

---

## 2. Core Validation Rules & Classification Matrix

| Check ID | Quality Rule | Evaluation Logic | Target / Threshold | Classification |
| :---: | :--- | :--- | :--- | :---: |
| **Q1** | **50-Stock Universe Integrity** | Company count, distinct symbols, empty/null check in `companies` table. | Exactly 50 companies, 50 distinct symbols, 0 nulls. | **Hard Blocking** |
| **Q2** | **Market Data Coverage & Dynamic Range** | Distinct companies with price records in `daily_prices`; min/max date span. | 50/50 companies covered, > 0 rows per stock. | **Hard Blocking** |
| **Q3** | **Technical Indicator Synchronization** | 1:1 match on `(company_id, date)` between `daily_prices` and `technical_indicators`. | 0 unmatched daily rows, 0 unmatched technical rows. | **Hard Blocking** |
| **Q4** | **Financial Data Coverage & Completeness** | Distinct companies with financial data; null checks across metrics (ROE, ROCE, EPS, etc.). | 50/50 companies covered (280 quarters); metric-level nulls logged as warnings. | **Warning** (Known upstream limit) |
| **Q5** | **Sector & Industry Mapping** | Verification of foreign keys to `sectors` and `industries` tables. | 16 sectors, 32 industries, 0 unmapped companies. | **Hard Blocking** |
| **Q6** | **Duplicate Record Detection** | Duplicate lookup across `daily_prices`, `technical_indicators`, `quarterly_results`, `backtest_results`. | 0 duplicate records across all core tables. | **Hard Blocking** |
| **Q7** | **Zero-Volume & Price Movement Anomalies** | Detect trading days with `volume == 0` or single-day price movement > 20%. | 0 invalid price records (blocking); volume/move anomalies flagged as audit items. | **Warning** (Operational audit) |
| **Q8** | **Foreign Key & Orphan Row Integrity** | Detect rows without valid matching parent company in `companies`. | 0 orphan records in prices, technicals, or financials. | **Hard Blocking** |
| **Q9** | **Point-in-Time Historical Safety** | Validate `get_backtest_inputs()` service contract across sample stocks. | `reporting_period <= evaluation_date` (0 leakage violations). | **Hard Blocking** |

---

## 3. Handling Known Upstream Data Limitations

### Upstream ROE / ROCE Incompleteness
- **Current Observation**: 50/50 universe companies have quarterly financial records (280 total quarters). However, some individual quarters have missing ROE (`null_count = 205`) and ROCE (`null_count = 186`) values upstream from public feeds.
- **Data Engineer Policy**:
  - The Data Service preserves missing values as standard `None` / `NaN` values without fabricating data or replacing missing metrics with zero.
  - The Quality Monitor reports this as an **Operational Warning**, allowing downstream engines to handle missing scores gracefully without blocking pipeline execution.

### Zero-Volume Trading Days & Extreme Movements
- **Current Observation**: 252 zero-volume rows exist in the historical series (e.g. trading halts, holiday sessions, illiquid trading days).
- **Data Engineer Policy**:
  - Zero-volume records are tracked as **Operational Warnings** to provide full auditability to trading strategies while preventing false pipeline aborts.

---

## 4. Routine Quality Monitoring Execution

### Running the Quality Monitor
To run the quality monitor from the command line:

```bash
.venv\Scripts\python backend/data_pipeline/week15_quality_monitor.py
```

### Exit Codes:
- `0`: Quality audit passed (with or without warnings).
- `1`: Blocking failure detected (pipeline should halt).

### Automated CI / Scheduled Integration:
The quality monitor writes structured JSON to `reports/week15_quality_monitoring_report.json`, suitable for automated ingestion, telemetry, and health reporting.
