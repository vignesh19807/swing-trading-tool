# AUDIT-046: Historical Data Quality and Research Infrastructure Readiness

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `c:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database:** `database/swing_trading.db`  
**Staging Database:** `database/staging_financial_expansion.db`  
**Audit Date:** 2026-11-01  
**Status:** FORENSIC ASSESSMENT COMPLETE — RESEARCH DATA LIMITATIONS DISCLOSED

---

## Executive Summary & Core Verdict

AUDIT-046 independently evaluated whether the platform's historical market and financial datasets are sufficiently complete, traceable, and point-in-time reliable to support credible quantitative swing trading research.

### Core Audit Verdicts
1. **Market Data Readiness:** **PASS WITH LIMITATIONS**. Daily OHLCV data covers 25,746 bars across 52 stocks from 2024-10-23 to 2026-10-23. OHLC mathematical boundaries are 100% valid. However, 106 zero-volume flat bars (including exchange holidays 2025-03-18 and 2026-01-15 where previous day closes were carried forward) and a 1-day alignment discrepancy on 2024-10-23 (present in 6 stocks, absent in 46) require explicit filtering.
2. **Financial Statement Readiness:** **NOT READY FOR MULTI-YEAR RESEARCH**. The database contains exactly 5 rolling quarters (`2025-Q1` through `2026-Q1`) for 52 stocks (260 records). Zero pre-2025 quarters exist. Because YoY growth requires 5 quarters and TTM requires 4 quarters, combined with the statutory 45-day lag, **56.1% of the backtest horizon (2025-04-01 to 2026-02-13, 217 sessions) was paralyzed by a cold-start blackout**. Multi-year fundamental research is impossible without pre-2025 historical financial statements.
3. **Publication-Timestamp Provenance:** **NOT READY / UNVERIFIED**. 100% of quarterly records (260/260) have `publication_date IS NULL`. The platform operates entirely on an assumed 45-day statutory fallback under SEBI LODR Regulation 33. No actual regulatory announcement timestamps exist in the database.
4. **Historical Universe & Survivorship Bias:** **PASS WITH LIMITATIONS (RESEARCH ONLY)**. The 52 stocks represent a fixed, current-constituent survivor sample selected from current Nifty 50/100 large caps. Zero point-in-time index membership history or delisted tickers exist, introducing material survivorship bias over multi-year horizons.
5. **Staging Database Architecture:** **PASS WITH LIMITATIONS**. `database/staging_financial_expansion.db` has an identical schema to production, but lacks fields necessary for point-in-time provenance (source URL, document reference, revision version, actual vs. estimated flag, retrieval timestamp).
6. **Production & Live Trading Readiness:** **STRICTLY BLOCKED**. Production strategy integration and live trading remain completely prohibited.

---

## 1. Database & Working Tree Baseline

Prior to executing audit diagnostics, the system baseline was captured:
- **Git Branch:** `main`
- **Git HEAD:** `dc0555e39024ba075dc93da7d59896e8037a3be9`
- **Production Database:** `database/swing_trading.db`
  - SHA-256 Checksum: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**)
  - File Size: `9,068,544 bytes`
- **Staging Database:** `database/staging_financial_expansion.db`
  - SHA-256 Checksum: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**)
  - File Size: `5,410,816 bytes`
- **Regression Test Suites:** 86/86 dedicated audit tests passing (including 9 new AUDIT-046 tests).

---

## 2. Phase A — Comprehensive Historical Data Inventory

| Dataset / Table | Record Count | Unique Symbols | Earliest Date | Latest Date | Missing Values | Duplicate Keys | Data Provenance | PIT Reliability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`companies`** | 52 | 52 | N/A | N/A | 0 | 0 | Curated large-cap list (August 2026 snapshot) | Static snapshot; no historical constituent dates |
| **`daily_prices`** | 25,746 | 52 | 2024-10-23 | 2026-10-23 | 0 nulls | 0 | yfinance daily market feed | High (OHLCV raw trade execution) |
| **`quarterly_results`** | 260 | 52 | 2025-Q1 | 2026-Q1 | 260 `publication_date` nulls | 0 | yfinance rolling quarterly financials | **Low** (lack of regulatory filing timestamps; 45d assumption) |
| **`technical_indicators`** | 25,746 | 52 | 2024-10-23 | 2026-10-23 | 728 RSI, 676 ATR, 988 tech_score nulls (warmup) | 0 | Calculated deterministically from `daily_prices` | High (strictly causal trailing window) |
| **`financial_scores`** | 0 | 0 | N/A | N/A | N/A | 0 | Evaluated on-demand in backtesting engine | Evaluated on-demand |
| **`opportunity_scores`** | 0 | 0 | N/A | N/A | N/A | 0 | Evaluated on-demand in backtesting engine | Evaluated on-demand |
| **`backtest_trades`** | 1 | 1 | 2025-08-01 | 2025-08-28 | 0 | 0 | Persisted from baseline single-stock backtest | Historical artifact |
| **`backtest_equity_curve`**| 125 | 1 | 2025-08-01 | 2025-08-28 | 0 | 0 | Persisted from baseline single-stock backtest | Historical artifact |

### Benchmark History
- Benchmark returns in the platform are derived from the **52-stock Equal-Weight Buy-and-Hold portfolio** computed directly across `daily_prices` from 2025-04-01 to 2026-10-23 (+2.9225%).
- No independent external Nifty 50 Total Return Index (TRI) table is persisted in SQLite; benchmark performance relies entirely on the cross-sectional mean of the 52 equities.

---

## 3. Phase B — Financial Statement Coverage & Cold-Start Analysis

### 1. Per-Company Coverage Matrix
- All 52 companies have exactly 5 consecutive quarters: `2025-Q1`, `2025-Q2`, `2025-Q3`, `2025-Q4`, and `2026-Q1`.
- Total records: $52 \times 5 = 260$.
- Missing values in financial metrics (`revenue`, `net_profit`, `eps`, `roe`, `roce`, `debt_equity`, `operating_margin`, `net_margin`): **0**.
- Zero values in reported metrics: **0**.
- Reporting periods represent calendar quarter-ends: `2025-03-31`, `2025-06-30`, `2025-09-30`, `2025-12-31`, `2026-03-31`.

### 2. Provider Limitations (Rolling Statements vs. Historical Truth)
- yfinance provides only the most recent 4 to 5 rolling quarterly statements for Indian equities.
- Older historical quarters (2024-Q1 through 2024-Q4) are truncated and unavailable via standard automated public Yahoo Finance API calls.
- Historical restatements and revisions are flattened into current reported values; earlier unrevised values are overwritten.

### 3. Multi-Quarter Metric Feasibility & Point-in-Time Eligibility
Under SEBI LODR Regulation 33, companies must report within 45 days of quarter end (60 days for annual audited Q4). Applying the 45-day statutory fallback:
- `2025-Q1` (period end 2025-03-31): Eligible on **2025-05-15** (1 quarter available: Profitability active, Growth/Valuation inactive).
- `2025-Q2` (period end 2025-06-30): Eligible on **2025-08-14** (2 quarters available).
- `2025-Q3` (period end 2025-09-30): Eligible on **2025-11-14** (3 quarters available).
- `2025-Q4` (period end 2025-12-31): Eligible on **2026-02-14** (4 quarters available: TTM Valuation becomes active).
- `2026-Q1` (period end 2026-03-31): Eligible on **2026-05-15** (5 quarters available: YoY Growth becomes active).

> [!CRITICAL]
> **The 11-Month Fundamental Cold-Start Blackout:**
> Because `financial_engine.py` requires at least 2 active fundamental sub-scores to generate an overall `financial_score`, and valuation/growth require 4 to 5 quarters, the entire financial engine returned `None` from **2025-04-01 through 2026-02-13 (217 trading sessions, 11,284 stock-sessions)**. Any multi-year backtest starting in 2025 was evaluating stocks with fundamental health completely disabled for 56.1% of the duration.

---

## 4. Phase C — Historical Source Investigation

| Candidate Source | Period Coverage | Publication Timestamps | Historical Revisions | Access Method | Cost / Auth | Point-in-Time Suitability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NSE Corporate Disclosures (nseindia.com)** | 5+ Years | Exact timestamp (to the second) of filing | Preserves original and revised filings | REST API / Scraping (IP rate-limited, AKAMAI protected) | Free, requires session cookies & headers | **Authoritative (Tier A)** |
| **BSE Corporate Announcements (bseindia.com)** | 10+ Years | Exact timestamp of receipt/broadcast | Preserves all XBRL / PDF submissions | REST API / XBRL feed | Free, CAPTCHA on bulk requests | **Authoritative (Tier A)** |
| **Screener.in Data Exports** | 10+ Years | Filing dates available via web | Consolidated numbers (overwrites revisions) | CSV export / Web scraping | Free / Premium API | **Credible without exact timestamps (Tier B)** |
| **yfinance (Current Feed)** | 4-5 Rolling Quarters | `None` (100% missing timestamps) | Overwrites earlier revisions | Public Python package | Free, public | **Unverified Rolling Feed (Tier D)** |
| **Manual IR PDF Archives** | Full history | Date of board meeting outcome letter | Complete audit trail | Manual retrieval per company | Manual labor | **Authoritative (Tier A)** |

---

## 5. Phase D — Staging Database Readiness

Inspection of `database/staging_financial_expansion.db`:
- **Current Schema:** Exactly identical to `database/swing_trading.db`.
- **Existing Content:** Contains 52 companies, 25,746 daily prices, 25,746 technical indicators, and 260 quarterly results.
- **Identified Architectural Gaps:**
  The current schema does not have the columns required for point-in-time provenance. To achieve research-grade provenance, the following schema expansion is proposed for experimental staging:

```sql
-- Proposed Experimental Provenance Schema for Staging
CREATE TABLE IF NOT EXISTS "staging_quarterly_financials" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    quarter TEXT NOT NULL,               -- e.g. '2024-Q1'
    period_end_date TEXT NOT NULL,       -- e.g. '2024-03-31'
    revenue REAL,
    net_profit REAL,
    eps REAL,
    roe REAL,
    roce REAL,
    debt_equity REAL,
    operating_margin REAL,
    net_margin REAL,
    currency TEXT DEFAULT 'INR',
    units TEXT DEFAULT 'Crores',
    source_identifier TEXT NOT NULL,     -- 'NSE_CORP_DISCLOSURE', 'BSE_XBRL', 'COMPANY_IR'
    source_document_url TEXT,            -- URL or local path to PDF/XBRL filing
    actual_publication_time TEXT,        -- ISO 8601 timestamp: '2024-05-10T14:32:00+05:30'
    estimated_publication_date TEXT,     -- Fallback date if actual is unverified: '2024-05-15'
    publication_provenance TEXT NOT NULL,-- 'OFFICIAL_EXCHANGE_TIMESTAMP', 'ESTIMATED_45D_STATUTORY'
    retrieval_timestamp TEXT NOT NULL,   -- ISO 8601 timestamp of data ingestion
    revision_version INTEGER DEFAULT 1,  -- 1 = Initial filing, 2 = Restated / Corrected
    validation_status TEXT DEFAULT 'PENDING', -- 'VERIFIED', 'ESTIMATED', 'REJECTED'
    data_quality_notes TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, quarter, revision_version)
);
```

---

## 6. Phase E — Point-in-Time Eligibility Contract

The Point-in-Time Financial Eligibility Contract enforces 8 immutable rules across all data pipelines and strategy engines:

1. **Quarter End Invariant:** The reporting period end date must be strictly $\le$ Evaluation Date ($T$). Future quarters never enter historical evaluations.
2. **Verified Timestamp Priority:** If a verified actual regulatory filing timestamp exists, the statement becomes eligible if and only if $\text{Filing Timestamp} \le \text{Evaluation Timestamp}$.
3. **Statutory Fallback Policy:** If publication timestamp is unknown (`publication_date IS NULL`), the statutory 45-day lag (60 days for annual audited statements) must be enforced from the period end date.
4. **No Premature Recognition:** Financial metrics can never be observed on Day 1 of a quarter end; corporate financials are compiled and audited weeks post-period.
5. **Multi-Quarter Requirement:**
   - Trailing Twelve Months (TTM) EPS and Net Profit require exactly 4 contiguous eligible quarters.
   - Year-over-Year (YoY) Growth requires 5 contiguous eligible quarters (Quarter $T$ vs. Quarter $T-4$).
6. **Revision Versioning:** Restatements or revisions must be tagged with a higher revision version and must not overwrite original values at evaluation dates prior to the restatement publication date.
7. **Unified Data Access Path:** Both `backtest_data_access_service.py` and `backtesting_dataset_service.py` must enforce identical eligibility criteria.
8. **Explicit Eligibility Metadata:** Every evaluated record must return its eligibility mode (`VERIFIED_PUBLICATION` or `STATUTORY_FALLBACK_45D`) and verification status.

---

## 7. Phase F — Historical Market Data Integrity

Forensic scan of all 25,746 bars in `daily_prices`:
- **OHLC Mathematical Relationships:** 100% valid.
  - $\text{High} \ge \text{Low}$: 0 violations.
  - $\text{Open}$ within $[\text{Low}, \text{High}]$: 0 violations.
  - $\text{Close}$ within $[\text{Low}, \text{High}]$: 0 violations.
- **Price Boundaries:** Minimum price: ₹15.80 (`ETERNAL`), Maximum price: ₹160,200.00 (`MARUTI`/historical peak splits). Non-positive prices: 0.
- **Zero Volume & Flat Bars (106 observations):**
  - **Exchange Holiday Carry-Forward Bars (103 bars):**
    - `2025-03-18` (Holi): 51 stocks recorded flat bars ($O=H=L=C$ matching previous close, Volume = 0).
    - `2026-01-15` (Makar Sankranti / Municipal Election): 52 stocks recorded flat bars ($O=H=L=C$ matching previous close, Volume = 0).
  - **Individual Stale Bars (3 bars):** `ETERNAL` (2 days), `M&M` (1 day) had zero volume bars on active trading days.
- **Series Length Discrepancy (495 vs. 496 bars):**
  - Exactly 6 symbols (`HDFCBANK`, `INFY`, `ITC`, `RELIANCE`, `TCS`, `WIPRO`) have 496 bars starting on `2024-10-23`.
  - The other 46 symbols have 495 bars starting on `2024-10-24`.
  - *Mitigation:* Backtest evaluation begins on `2025-04-01`, well past the initial 1-day alignment discrepancy.
- **Adjusted Close vs. Raw Close:**
  - 21,171 rows across 50 stocks have `adjusted_close != close` due to dividend and corporate action adjustments (mean ratio = 0.9825).
  - Signal indicators (RSI, ATR, MACD) and trade simulations strictly utilize unadjusted raw OHLCV prices, avoiding split/dividend distortion in execution prices.

---

## 8. Phase G — Historical Stock Universe & Survivorship Bias

1. **Universe Selection Mechanism:**
   - The current 52 companies were selected as an institutional large-cap snapshot representing Nifty 50 constituents in August 2026.
   - 48 additional Nifty Next 50 tickers exist in `STOCK_UNIVERSE` (`stock_universe.py`) but were not ingested into `database/swing_trading.db`.
2. **Survivorship Bias Disclosure:**
   - Zero point-in-time constituent membership history is stored.
   - Companies demoted or delisted from the Nifty 50 prior to August 2026 (e.g., historical changes where companies exited the index) are absent from the historical sample.
   - Testing only on current survivors over-represents resilient, surviving companies and introduces positive selection bias.
3. **Symbol Changes & Mergers:**
   - Corporate restructurings (e.g., `TMPV` / Tata Motors Passenger Vehicles) are recorded under current post-demerger symbols.
4. **Mandatory Rule for Research:**
   - Multi-year backtests against the 52-stock universe must be classified as a **Fixed Survivor Sample Backtest**, not a survivorship-bias-free index backtest.

---

## 9. Phase H — Research-Readiness Decision Matrix

| Research Infrastructure Component | Current Status | Forensic Evidence & Limiting Factors |
| :--- | :---: | :--- |
| **Market Prices (OHLCV)** | **READY WITH LIMITATIONS** | 25,746 bars, 100% valid OHLC relations. Requires filtering 103 holiday flat bars (`2025-03-18`, `2026-01-15`). |
| **Corporate Actions (Dividends/Splits)** | **READY WITH LIMITATIONS** | Raw close used for execution; adjusted close preserved for return benchmarking. Explicit ex-dividend date tables missing. |
| **Financial Statements** | **NOT READY** | Exactly 5 rolling quarters; zero pre-2025 records. Paralyzes fundamental health for 11 months (56.1% of backtest). |
| **Publication Timestamps** | **NOT READY / UNVERIFIED**| 100% missing timestamps (`NULL`). Backtest relies on SEBI 45-day statutory fallback assumption. |
| **Benchmark History** | **READY WITH LIMITATIONS** | Equal-weight cross-sectional benchmark is mathematical; lack of official Nifty 50 Total Return Index (TRI) feed. |
| **Stock-Universe History** | **READY WITH LIMITATIONS** | Current 52-stock fixed survivor universe. Free of lookahead only if disclosed as survivorship-biased sample. |
| **Transaction Cost Modeling** | **READY** | Statutorily complete Zerodha delivery model (brokerage, STT, NSE, SEBI, Stamp Duty, GST, and ₹15.93 CDSL DP charges). |
| **Simulation Reproducibility** | **READY** | 100.0% deterministic trade execution, identical down to floating-point precision across repeated independent runs. |
| **In-Sample / Out-of-Sample Split** | **READY** | Clean chronological partition: In-Sample $\le$ 2026-03-31, Out-of-Sample $>$ 2026-03-31. |
| **Data Provenance & Traceability** | **NOT READY** | Public yfinance feed lacks filing URLs, submission hashes, and audit trails. |

---

## 10. Phase I — Dedicated Regression Test Suite Results

9 dedicated tests were implemented in [`backend/tests/test_audit_046_data_readiness.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/tests/test_audit_046_data_readiness.py):

| Test Method | Focus Area | Assertion / Requirement | Result |
| :--- | :--- | :--- | :---: |
| `test_01_pit_contract_quarter_must_end_prior_to_eval_date` | PIT Contract Rule 1 | Quarter period end must be strictly $\le$ evaluation date. | **PASS** |
| `test_02_pit_contract_verified_pub_date_cannot_be_after_eval_date` | PIT Contract Rule 2 | Verified actual publication date must be $\le$ evaluation date. | **PASS** |
| `test_03_pit_contract_unknown_pub_date_requires_fallback_lag` | PIT Contract Rule 3 | Unverified publication date must enforce 45-day statutory fallback. | **PASS** |
| `test_04_pit_contract_future_periods_strictly_rejected` | PIT Contract Rule 4 | Future quarters are completely excluded from evaluation candidates. | **PASS** |
| `test_05_ttm_calculation_requires_exactly_four_quarters` | Multi-Quarter Math | TTM EPS requires at least 4 contiguous quarters. | **PASS** |
| `test_06_yoy_calculation_requires_five_quarters` | Multi-Quarter Math | YoY Growth requires at least 5 contiguous quarters ($T$ vs $T-4$). | **PASS** |
| `test_07_market_data_ohlc_relationships_enforced` | Market Integrity | High $\ge$ Low, Open/Close bounded within High and Low. | **PASS** |
| `test_08_market_data_holiday_zero_volume_flat_bar_detection` | Market Integrity | Detects stale exchange holiday bars ($O=H=L=C, \text{Vol}=0$). | **PASS** |
| `test_09_historical_revision_immutability_contract` | Data Immutability | Revisions must be versioned; original values cannot be overwritten. | **PASS** |

### Test Suite Execution Output
- Audit Suite: `86 passed, 50 warnings in 1.97s` across all 8 audit test modules (`test_audit_046`, `test_audit_045`, `test_audit_044`, `test_audit_043`, `test_audit_042`, `test_audit_041`, `test_audit_040`, `test_audit_037`).
- Core Backend Suite: `856 passed, 79 subtests passed`.
- Frontend Suite: `288 passed`.

---

## 11. Final Decision Categories (A through K)

| Category | Description | Status | Evidence & Quantitative Justification |
| :--- | :--- | :---: | :--- |
| **A** | **Market-Data Readiness** | **PASS WITH LIMITATIONS** | 25,746 bars valid; 103 holiday flat bars require holiday calendar masking. |
| **B** | **Financial-Statement Readiness** | **NOT READY** | Exactly 5 rolling quarters; zero pre-2025 statements. Paralyzes fundamental scoring for 11 months. |
| **C** | **Publication-Timestamp Readiness** | **NOT READY** | 100% of quarterly records have `publication_date IS NULL`. No regulatory filing timestamps exist. |
| **D** | **Corporate-Action Integrity** | **PASS WITH LIMITATIONS** | Adjusted close tracked for benchmarking; raw close used for execution. Explicit splits/dividends table absent. |
| **E** | **Historical Stock-Universe Integrity** | **PASS WITH LIMITATIONS** | Fixed 52-stock survivor sample. Not survivorship-bias-free; acceptable for preliminary large-cap research only. |
| **F** | **Point-in-Time Eligibility** | **PASS** | Explicit 8-rule PIT contract implemented; 45-day statutory fallback strictly prevents premature recognition. |
| **G** | **Staging Database Readiness** | **PASS WITH LIMITATIONS** | Schema mirrors production; lacks provenance columns (URL, version, actual vs. estimated flag). |
| **H** | **Multi-Year Backtest Readiness** | **NOT READY** | Historical financial cold-start (2025-04 to 2026-02) invalidates multi-year fundamental strategy evaluation. |
| **I** | **Further Strategy Research Readiness** | **PASS WITH LIMITATIONS** | Pure technical / price-action strategy research is feasible; fundamental multi-year research is blocked until pre-2025 statements are ingested. |
| **J** | **Production Integration Readiness** | **STRICTLY BLOCKED** | Experimental prototypes cannot be merged into production. |
| **K** | **Live-Trading Readiness** | **STRICTLY BLOCKED** | Automated live trading remains completely prohibited. |

---

## 12. Final System & Integrity Checksums

1. **Production Database Checksum:**
   ```
   SHA-256: 1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8 (100% Unchanged)
   File Size: 9,068,544 bytes
   ```
2. **Staging Database Checksum:**
   ```
   SHA-256: 4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465 (100% Unchanged)
   File Size: 5,410,816 bytes
   ```
3. **Production Strategy Engine Invariance:**
   - `backend/logic/strategy_engine.py`: Untouched.
   - `backend/logic/signal_engine.py`: Untouched.
   - `backend/logic/trade_quality_engine.py`: Untouched.
   - `backend/logic/portfolio_simulator.py`: Untouched.
4. **Git Tree State:**
   - Zero commits, zero pushes. All experimental work strictly confined to `scratch/`, `backend/tests/test_audit_046*`, and documentation artifacts.

