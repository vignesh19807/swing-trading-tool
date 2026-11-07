# P2.1 — Historical Financial Data Quality & Restatement Integrity Audit

**Target Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Execution Environment:** Windows, Python 3.14.7, SQLite  
**Baseline Git Commit:** `ecbcbde2e78f03e06575b84240634ba3b5c81239`  
**Audit Date:** 2026-11-04  
**Audit Status:** `P2.1 AUDIT COMPLETE — BLOCKING DATA GAPS`  

---

## 1. Executive Summary

As part of Phase P2 (Historical Financial Data Quality & Restatement Integrity), an exhaustive read-only audit of the financial data layer, database schemas, and publication timestamp availability was conducted across both production (`database/swing_trading.db`) and staging (`database/staging_financial_expansion.db`) databases.

### Core Audit Findings
1. **Total Universe Coverage:** 52 tracked Indian equity companies across Nifty 50 and Nifty Next 50.
2. **Total Quarterly Records:** Exactly 260 quarterly records per database (5 quarters per company: `2025-Q1`, `2025-Q2`, `2025-Q3`, `2025-Q4`, `2026-Q1`).
3. **Publication Date Nullity:** **260 of 260 records (100.0%) have `publication_date IS NULL`**. Zero verified publication timestamps exist in either database.
4. **Synthetic Placeholder Contamination:** **258 of 260 records (99.23%) contain identical synthetic placeholder constants** (`revenue = 10000.0`, `net_profit = 1500.0`, `eps = 15.0`, `roe = 0.18`, `roce = 0.22`, `debt_equity = 0.35`, `operating_margin = 0.20`, `net_margin = 0.15`). Only 2 records (`INFY` for `2025-Q4` and `2026-Q1`) possess custom values.
5. **Restatement & Vintage Blindness:** The current schema enforces `UNIQUE(company_id, quarter)` on `quarterly_results`. The database stores a single mutable snapshot per quarter. Any restatement, revision, or audit correction destructively overwrites original numbers in place, creating unavoidable lookahead bias for pre-restatement dates.
6. **Strict P1 Research Starvation:** Because P1 strictly enforces `require_verified_publication_date=True` to eliminate lookahead bias, and 100% of rows have `publication_date IS NULL`, all financial analyzers return `insufficient_data: True`. In strict research mode, every single evaluated date is starved of fundamental signals, preventing BUY recommendations (`Outcome C`).

**Audit Verdict:** `P2.1 AUDIT COMPLETE — BLOCKING DATA GAPS`. The platform cannot perform reliable fundamental swing-trading backtests without an automated ingestion pipeline sourcing verified timestamps and vintage preservation.

---

## 2. Existing Database Schema & Architecture

The platform stores quarterly fundamentals in `quarterly_results` with foreign keys to `companies`.

### 2.1 Table Definition: `quarterly_results`
```sql
CREATE TABLE "quarterly_results" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    quarter TEXT NOT NULL,
    revenue REAL,
    net_profit REAL,
    eps REAL,
    roe REAL,
    roce REAL,
    debt_equity REAL,
    operating_margin REAL,
    net_margin REAL,
    publication_date TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, quarter)
);
```

### 2.2 Schema Constraints & Indexes
* **Primary Key:** `id` (`INTEGER PRIMARY KEY AUTOINCREMENT`).
* **Unique Constraint:** `sqlite_autoindex_quarterly_results_1` on `(company_id, quarter)`.
* **Foreign Key:** `company_id -> companies(id)` (`ON UPDATE NO ACTION`, `ON DELETE NO ACTION`).
* **Explicit Indexes (Production):**
  * `idx_quarterly_results_company_quarter` on `(company_id, quarter)`.
  * `idx_quarterly_results_quarter` on `(quarter)`.
* **Explicit Indexes (Staging):** None (only autoindex).
* **Audit Metadata Columns:** **None**. There are no columns for `created_at`, `updated_at`, `source_url`, `filing_timestamp`, `document_hash`, or `is_restated`.

---

## 3. Financial Data Quality & Completeness Inventory

A complete census was run against all 52 companies and 260 rows. Detailed per-company counts are exported to [`docs/audit_artifacts/P2_1_FINANCIAL_DATA_INVENTORY.csv`](file:///C:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/P2_1_FINANCIAL_DATA_INVENTORY.csv).

### 3.1 Macro Quality Summary

| Metric / Dimension | Production (`swing_trading.db`) | Staging (`staging_financial_expansion.db`) | Status |
| :--- | :--- | :--- | :--- |
| **Tracked Companies** | 52 | 52 | Complete |
| **Total Quarterly Records** | 260 | 260 | Fixed (5 per company) |
| **Unique Quarters** | 5 (`2025-Q1` to `2026-Q1`) | 5 (`2025-Q1` to `2026-Q1`) | Limited span |
| **Verified `publication_date`** | **0 / 260 (0.0%)** | **0 / 260 (0.0%)** | **BLOCKING GAP** |
| **Missing `publication_date`** | **260 / 260 (100.0%)** | **260 / 260 (100.0%)** | **BLOCKING GAP** |
| **Synthetic Placeholder Rows** | **258 / 260 (99.23%)** | **258 / 260 (99.23%)** | **CRITICAL ANOMALY** |
| **Revenue Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **Net Profit Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **EPS Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **ROE Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **ROCE Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **Debt / Equity Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **Operating Margin Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **Net Margin Populated** | 260 / 260 (100.0%) | 260 / 260 (100.0%) | Populated (99.2% fake) |
| **Duplicate `(company_id, quarter)`** | 0 | 0 | Enforced by schema |

### 3.2 The Synthetic Placeholder Anomaly
Investigation into the numerical distribution revealed that 258 of the 260 rows contain carbon-copy numerical values:
* `revenue = 10000.0`
* `net_profit = 1500.0`
* `eps = 15.0`
* `roe = 0.18`
* `roce = 0.22`
* `debt_equity = 0.35`
* `operating_margin = 0.20`
* `net_margin = 0.15`

Only `INFY` has distinct values for `2025-Q4` and `2026-Q1`:
* `INFY 2025-Q4`: Revenue `39000.0`, Net Profit `6800.0`, EPS `17.0`, ROE `0.27`, ROCE `0.34`, D/E `0.05`.
* `INFY 2026-Q1`: Revenue `40000.0`, Net Profit `7000.0`, EPS `18.0`, ROE `0.28`, ROCE `0.35`, D/E `0.05`.

**Implication:** Not only are publication dates absent, but the actual fundamental financials for 51 of the 52 companies are placeholder mock data populated during earlier scaffolding.

---

## 4. Financial Publication Source Investigation (Indian Equities)

Under SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 (LODR), Regulation 33 mandates listed entities to submit quarterly financial results within 45 days of the quarter's end (or 60 days for annual audited results in Q4).

To eliminate lookahead bias and ensure point-in-time veracity, potential announcement sources were evaluated:

### 4.1 Evaluation Matrix of Financial Announcement Sources

| Source | Historical Timestamps | Vintage / Amendment Support | Document Fingerprint / PDF | Automated Ingestion Viability | Compliance & Terms | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. NSE Corporate Announcements API** (`nsearchives.nseindia.com`) | **Yes** (Precise date and time `DD-Mon-YYYY HH:MM:SS`) | **Yes** (Broadcasts separate `SUBJECT` for revised/rectified results) | **Yes** (Direct link to exchange-uploaded PDF) | **High** (JSON endpoint with session cookies / headers) | Public regulatory portal; requires polite rate limiting & headers | **PRIMARY RECOMMENDED SOURCE** |
| **2. BSE Corporate Announcements API** (`api.bseindia.com`) | **Yes** (Filing date and time to the second) | **Yes** (Amendment entries flagged with distinct `SCRIP_CD` / category) | **Yes** (Permanent link to PDF in BSE archives) | **High** (REST API `CorporateAnnouncements`) | Public regulatory portal; robust machine-readable endpoints | **SECONDARY / CROSS-VERIFICATION** |
| **3. Company Investor Relations Disclosures** | Inconsistent (often date only, rarely exact broadcast timestamp) | Poor (websites overwrite older filings with latest PDF) | Yes | **Very Low** (Scraping 52 distinct corporate websites is brittle) | Varies by company | **UNSUITABLE FOR AUTOMATION** |
| **4. Third-Party Data Providers (e.g. yfinance, Yahoo Finance)** | **No** (Yahoo reports period-end date only; earnings timestamp often missing or US-market normalized) | **No** (Overwrites restated values without historical ledger) | No | Moderate | Strict terms against automated redistributive storage | **UNVERIFIED / DISQUALIFIED FOR PIT** |

### 4.2 Primary Source Architecture: NSE / BSE Exchange Announcements
* **NSE Broadcast Metadata:** The National Stock Exchange broadcasts quarterly financial results under the category `Financial Result`. The broadcast payload contains:
  * `symbol`: e.g. `TCS`, `INFY`.
  * `desc`: Description / Subject (e.g., `Financial Result Updates for the quarter ended Dec 31, 2025`).
  * `an_dt`: Broadcast date and time (e.g., `15-Jan-2026 17:45:12`).
  * `attchmntText`: Path to original PDF.
* **Point-in-Time Availability Boundary:** Results announced after 15:30 IST on trading day $T$ cannot influence trading decisions until trading day $T+1$. Results announced prior to 09:15 IST on trading day $T$ become effective on day $T$.

---

## 5. Historical Financial Vintage Architecture (P2.3 Design)

To support multiple restatements and eliminate vintage lookahead bias, the single-row `quarterly_results` model must be superseded by an append-only, multi-vintage ledger.

### 5.1 Proposed Schema: `quarterly_financial_vintages`
```sql
CREATE TABLE quarterly_financial_vintages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    quarter TEXT NOT NULL,                         -- e.g. '2025-Q3'
    period_start_date TEXT NOT NULL,               -- e.g. '2025-07-01'
    period_end_date TEXT NOT NULL,                 -- e.g. '2025-09-30'
    announcement_date TEXT NOT NULL,               -- e.g. '2025-10-18' (YYYY-MM-DD)
    announcement_timestamp TEXT NOT NULL,          -- e.g. '2025-10-18 16:42:10' (IST)
    effective_trading_date TEXT NOT NULL,          -- e.g. '2025-10-21' (Next trading session if filed after-market)
    filing_type TEXT NOT NULL CHECK(filing_type IN ('ORIGINAL', 'AMENDED', 'RESTATED', 'AUDITED_FINAL')),
    version_sequence INTEGER NOT NULL DEFAULT 1,   -- 1 for original, 2 for first revision, etc.
    superseded_by_id INTEGER,                      -- NULL if active, or ID of superseding vintage
    
    -- Financial Metrics
    revenue REAL,
    net_profit REAL,
    eps REAL,
    roe REAL,
    roce REAL,
    debt_equity REAL,
    operating_margin REAL,
    net_margin REAL,
    
    -- Provenance & Audit Metadata
    source_exchange TEXT NOT NULL CHECK(source_exchange IN ('NSE', 'BSE', 'MANUAL_VERIFIED')),
    source_document_url TEXT,
    document_sha256 TEXT,
    ingestion_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('VERIFIED', 'AUDITED', 'PROVISIONAL')),
    
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (superseded_by_id) REFERENCES quarterly_financial_vintages(id),
    UNIQUE(company_id, quarter, version_sequence),
    UNIQUE(company_id, quarter, announcement_timestamp)
);

CREATE INDEX idx_vintages_pit_lookup 
ON quarterly_financial_vintages(company_id, effective_trading_date, quarter);
```

### 5.2 Key Architecture Properties
1. **Append-Only Immutability:** Never run `UPDATE` or `DELETE` on financial metrics. Revisions are inserted as `version_sequence = N + 1` with `filing_type = 'RESTATED'` or `'AMENDED'`.
2. **Effective Trading Date Materialization:** The pipeline computes `effective_trading_date` based on whether the timestamp occurred before market open (09:15), during market hours, or after market close (15:30) on a trading day versus weekend/holiday.
3. **Backward Compatibility View:** A view `quarterly_results_latest_verified` can provide backward compatibility for legacy callers that only request current data.

---

## 6. Point-in-Time Query Logic Design

### 6.1 Point-in-Time Resolution Rule
When a historical backtest evaluates a strategy on date $T_{\text{eval}}$:
1. **Selection Criterion:** Query all filings for the company where `effective_trading_date <= T_eval`.
2. **Vintage Tie-Breaking:** For any quarter that has multiple filings before $T_{\text{eval}}$, select the one with the highest `version_sequence` (or latest `announcement_timestamp`).
3. **Cutoff Exclusion:** Any filing where `effective_trading_date > T_eval` is completely invisible.

### 6.2 SQL Implementation
```sql
WITH ranked_vintages AS (
    SELECT 
        v.*,
        ROW_NUMBER() OVER (
            PARTITION BY v.quarter 
            ORDER BY v.version_sequence DESC, v.announcement_timestamp DESC
        ) as rank
    FROM quarterly_financial_vintages v
    WHERE v.company_id = :company_id
      AND v.effective_trading_date <= :evaluation_date
      AND v.verification_status IN ('VERIFIED', 'AUDITED')
)
SELECT 
    quarter,
    effective_trading_date,
    announcement_timestamp,
    filing_type,
    revenue,
    net_profit,
    eps,
    roe,
    roce,
    debt_equity,
    operating_margin,
    net_margin
FROM ranked_vintages
WHERE rank = 1
ORDER BY period_end_date DESC
LIMIT 4; -- 4 most recent available quarters for TTM analysis
```

### 6.3 Resolution Walkthrough for Audit Scenarios
Suppose Company X has Q1 results ended 2025-06-30:
* **Filing A (Original):** Announced 2025-08-10 at 18:00 IST $\rightarrow$ `effective_trading_date = 2025-08-11`.
* **Filing B (Restated):** Announced 2025-09-15 at 11:00 IST $\rightarrow$ `effective_trading_date = 2025-09-15`.

| Evaluation Date | Available Filings | Selected Filing | Lookahead Prevention Evidence |
| :--- | :--- | :--- | :--- |
| **2025-08-05** | None | None (`insufficient_data: True`) | Q1 results not yet public. Zero lookahead. |
| **2025-08-10 (12:00)** | None | None | Announced after market hours. Ineligible until next trading day. |
| **2025-08-20** | Filing A | Filing A (Original) | Original filing visible; September restatement invisible. |
| **2025-09-10** | Filing A | Filing A (Original) | Still sees original filing. |
| **2025-09-20** | Filing A, Filing B | Filing B (Restated) | Filing B supersedes Filing A because `effective_date <= 2025-09-20`. |

---

## 7. Future Ingestion Pipeline Architecture (P2.4 Design)

```
        +-----------------------------------------------+
        |    NSE / BSE Corporate Announcement Feed      |
        |   (REST API / RSS Feeds / Corporate Discl.)   |
        +-----------------------+-----------------------+
                                |
                                v
        +-----------------------------------------------+
        |           Announcement Discovery               |
        |   - Filters for Category: 'Financial Results' |
        |   - Extracts Symbol, Timestamp, PDF URL       |
        +-----------------------+-----------------------+
                                |
                                v
        +-----------------------------------------------+
        |          Document Archiver & Hash             |
        |   - Downloads PDF to persistent store         |
        |   - Computes SHA-256 document fingerprint     |
        +-----------------------+-----------------------+
                                |
                                v
        +-----------------------------------------------+
        |       Financial Data Parser & Extractor       |
        |   - OCR / XBRL / Table Parser                 |
        |   - Normalizes Revenue, PAT, EPS, Margins     |
        |   - Computes ROE, ROCE, Debt/Equity           |
        +-----------------------+-----------------------+
                                |
                                v
        +-----------------------------------------------+
        |       Validation & Reconciliation Gate        |
        |   - Sanity checks (Revenue > 0, PAT <= Rev)   |
        |   - Checks for existing (company, quarter)    |
        |   - Sets filing_type (ORIGINAL vs RESTATED)   |
        +-----------------------+-----------------------+
                                |
                                v
        +-----------------------------------------------+
        |        Append to 'quarterly_financial_vintages'|
        |   - Sets version_sequence                     |
        |   - Calculates effective_trading_date         |
        |   - Status: VERIFIED                          |
        +-----------------------------------------------+
```

---

## 8. Test Strategy & Verification Scenarios (P2.5)

The implementation phase must validate 12 core test scenarios before merging:
1. **Pre-Announcement Nullity:** Query before announcement date returns empty set.
2. **Post-Announcement Availability:** Query on/after effective date returns original filing.
3. **Mid-Stream Restatement Evolution:** Verification that backtest running across a restatement boundary switches deterministically from original to restated metrics on the exact effective date.
4. **Intraday Announcement Boundary:** Announcement at 16:00 on Day $T$ is not visible on Day $T$; visible on Day $T+1$.
5. **Weekend Announcement Boundary:** Announcement on Saturday is effective Monday morning.
6. **Duplicate Filing Idempotence:** Submitting identical filing hash raises unique constraint or merges idempotently without bumping version.
7. **Conflicting Concurrent Filings:** Handling simultaneous standalone vs. consolidated filings (standardize on Consolidated).
8. **Invalid Date Formatting:** Rejection of non-ISO timestamps or impossible calendar dates.
9. **Extreme Outlier / Unit Detection:** Anomaly filter catching Lakhs vs. Crores scale errors.
10. **Strict-Mode Backward Compatibility:** Legacy `get_financial_data()` seamlessly routes to vintage PIT query when enabled.
11. **Starvation Handling:** Ensuring decision engine returns `INSUFFICIENT_DATA` rather than throwing uncaught exceptions.
12. **Historical Determinism:** Identical backtest run on two separate machines yields identical financial score series.

---

## 9. Risk Assessment Matrix (P2.6)

| Risk ID | Risk Description | Severity | Probability | Impact on Backtesting | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-01** | **Complete Publication Date Absence** (Current state) | **Critical** | **100% (Confirmed)** | Complete signal starvation in strict mode; lookahead bias in legacy mode | Ingest verified NSE/BSE corporate announcements |
| **R-02** | **Synthetic Placeholder Contamination** (Current state) | **Critical** | **100% (Confirmed)** | Backtests run on fake identical financials across 51 stocks | Purge/replace with parsed exchange filings |
| **R-03** | **Restatement Lookahead Overwrite** | High | High | Overestimating historical signal accuracy using revised numbers | Deploy `quarterly_financial_vintages` schema |
| **R-04** | **Standalone vs Consolidated Ambiguity** | High | Medium | Inconsistent margins/ROE between parent and group | Enforce Consolidated results as primary standard |
| **R-05** | **Currency / Unit Scaling (Crores vs Lakhs)** | High | Low | $100\times$ calculation errors in revenue/profit | Enforce automated magnitude sanity checks |
| **R-06** | **Exchange Broadcast Timezone Offsets** | Medium | Medium | 1-day misclassification of after-market filings | Explicitly normalize all timestamps to Asia/Kolkata IST |
| **R-07** | **Survivorship Bias in 52-Stock Universe** | Medium | High | Backtesting only today's index constituents | Document universe limitation; expand point-in-time constituent table in P3 |

---

## 10. Prioritized Implementation Roadmap

* **Phase P2.1 (Current):** Data quality audit, inventory CSV generation, and architecture design. *(Complete)*
* **Phase P2.2:** Schema definition and migration script for `quarterly_financial_vintages` in staging database (`database/staging_financial_expansion.db`).
* **Phase P2.3:** NSE/BSE corporate announcement ingestion client with timestamp parsing and PDF archiving.
* **Phase P2.4:** Extraction and calculation of real fundamental metrics for the 52 tracked companies (replacing 258 placeholder rows).
* **Phase P2.5:** Integration of PIT vintage query into `backend/data_pipeline/financial_service.py` and `backend/engines/financial_engine.py`.
* **Phase P2.6:** Full regression testing and benchmark backtest comparison.

---

## 11. Definition of Done (DoD) for P2 Phase

- [x] **P2.1 Audit Complete:** Detailed audit report and company inventory CSV generated.
- [ ] **Vintage Schema Deployed:** `quarterly_financial_vintages` table created in staging DB.
- [ ] **Verified Publication Timestamps Ingested:** 100% of tracked company quarters possess verified exchange announcement timestamps.
- [ ] **Synthetic Placeholders Replaced:** All 258 placeholder rows replaced with real audited metrics.
- [ ] **PIT Query Integrated:** Financial service queries effective trading dates without lookahead.
- [ ] **Automated Regression Suite:** 12/12 P2 test scenarios passing with zero regressions in P0/P1 suites.
- [ ] **Zero Database Mutations on Production without User Approval.**

---

## 12. Final Verdict

**Verdict:** `P2.1 AUDIT COMPLETE — BLOCKING DATA GAPS`

*Reasoning:* The audit successfully identified that 100% of existing publication dates are NULL and 99.23% of quarterly rows contain synthetic placeholder data. The vintage architecture and query logic are fully designed. Implementation requires human authorization before creating tables or ingesting live exchange data.

