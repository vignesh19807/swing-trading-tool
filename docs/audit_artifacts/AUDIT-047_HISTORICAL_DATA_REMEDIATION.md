# AUDIT-047: Comprehensive Historical Data Integrity Remediation

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `c:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database:** `database/swing_trading.db`  
**Staging Database:** `database/staging_financial_expansion.db`  
**Audit Date:** 2026-11-01  
**Status:** FORENSIC REMEDIATION & VERIFICATION COMPLETE — DATA LIMITATIONS DISCLOSED

---

## 1. Executive Summary & Problem Resolution Summary

AUDIT-047 conducted a thorough forensic investigation and remediation of the five core historical data integrity problems identified in AUDIT-046. In strict accordance with the mandatory safety rules:
- **Zero mutations** were performed on the production database (`database/swing_trading.db`) or staging database (`database/staging_financial_expansion.db`).
- **Zero modifications** were made to protected production strategy files (`strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`).
- Non-destructive research filtering layers, explicit provenance schemas, and governance contracts were implemented.
- All 11 dedicated AUDIT-047 regression tests passed (97 total passing audit tests across 9 audit suites).

### Remediation & Investigation Summary Table

| Problem | Root Cause | Fix Implemented | Regression Test | Evidence | Remaining Limitation | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **1. Financial Publication Timestamps & Fallback** | yfinance rolling quarterly feed lacks regulatory filing timestamps (`NULL`). Multi-quarter requirements (TTM 4Q, YoY 5Q) cause 11-month cold-start blackout. | Verified SEBI LODR Reg 33 deadlines (45d quarterly, 60d annual audited). Enforced verified timestamp priority and fallback lag in `financial_service.py` & `backtesting_dataset_service.py`. Explicitly labeled missing dates as `ESTIMATED_REPORTING_LAG` / `UNVERIFIED`. | `test_01` to `test_04` in `test_audit_047_remediation.py` | SEBI LODR Reg 33(3)(a) & 33(3)(d) provisions; 260 DB records audited. | 260 historical records remain without actual BSE/NSE announcement timestamps until exchange portal feeds are ingested. | **PARTIAL (Code Fixed, Historical Data Limitation Disclosed)** |
| **2. Holiday Flat Bars & Market Anomalies** | Provider (yfinance) carried forward previous trading day closing prices with Volume = 0 on exchange holidays (`2025-03-18` Holi, `2026-01-15` Sankranti/Municipal election). | Implemented non-destructive research filtering layer in `research_market_data_filter.py`. Detects synthetic holiday flat bars, stale flat bars, inverted OHLC, and non-positive prices without altering SQLite records. | `test_05`, `test_06` in `test_audit_047_remediation.py` | 103 holiday carry-forward flat bars and 3 stale bars isolated and categorized across 25,746 rows. | Production DB retains raw records; research backtest pipelines must invoke the filtering layer. | **PASS (Remediated in Research Layer)** |
| **3. Corporate-Action Integrity** | Provider adjusts historical close for dividends/splits in `adjusted_close` but leaves raw OHLC unadjusted. Demergers (e.g. `TMPV` -40.15% on 2025-10-14) produce large price discontinuities. | Authored formal `CorporateActionRecord` metadata schema in `universe_metadata.py`. Integrated large price discontinuity detection (>25% return) in anomaly filter to isolate potential unadjusted corporate actions. Verified raw close is used for execution and adjusted close for return benchmarking. | `test_07`, `test_08` in `test_audit_047_remediation.py` | Isolated 2 large price moves (`TMPV` -40.15%, `TRENT` -33.05%); audited 21,171 rows where adjusted_close != close. | Historical corporate actions table not yet persisted in SQLite database; corporate actions currently identified via ratio analysis. | **PARTIAL (Safeguards Implemented, Corporate Actions Table Pending Ingestion)** |
| **4. Historical Universe & Survivorship Bias** | 52 companies were selected as an institutional large-cap snapshot in August 2026. Delisted or demoted historical constituents prior to 2026 are absent. | Authored `ResearchUniverseMetadata` and `UniverseConstituentRecord` schemas in `universe_metadata.py`. Enforced explicit disclosure tags classifying the sample as `FIXED_SURVIVOR_SAMPLE` and explicitly denying `is_survivorship_bias_free`. | `test_09`, `test_10` in `test_audit_047_remediation.py` | Audited `stock_universe.py` against SQLite `companies`; documented 48 omitted Nifty Next 50 tickers. | Historical index rebalancing events prior to August 2026 cannot be reconstructed point-in-time without historical NSE index archives. | **PARTIAL (Disclosures & Governance Enforced, PIT Universe Pending)** |
| **5. Test Validity vs. Actual Research Validity** | Automated tests passing on synthetic fixtures or mock data does not prove historical strategy alpha or commercial profitability. | Created comprehensive research validation matrix. Audited complete cost model (brokerage ₹0, STT 0.1%, NSE 0.00297%, SEBI ₹10/cr, Stamp Duty 0.015%, GST 18%, and DP fee ₹15.93 per sell leg). Separated code correctness from empirical financial viability. | `test_11` in `test_audit_047_remediation.py` | Reconciled Zerodha equity delivery tariffs; proved Support Pullback net loss of -₹253.86 under 10 bps + DP charges despite passing tests. | Research validity cannot be claimed for fundamental strategies until pre-2025 statements are staged. | **PASS (Framework & Matrix Established)** |

---

## 2. Baseline Checksums & System Invariants

Prior to and following the AUDIT-047 investigation, system baselines were authoritatively verified:
- **Git Branch:** `main`
- **Git HEAD Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`
- **Production Database:** `database/swing_trading.db`
  - SHA-256 Checksum: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**)
  - File Size: `9,068,544 bytes`
- **Staging Database:** `database/staging_financial_expansion.db`
  - SHA-256 Checksum: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**)
  - File Size: `5,410,816 bytes`
- **Protected Files Invariance:**
  - `backend/logic/strategy_engine.py`: Untouched.
  - `backend/logic/signal_engine.py`: Untouched.
  - `backend/logic/trade_quality_engine.py`: Untouched.
  - `backend/logic/portfolio_simulator.py`: Untouched.

---

## 3. Detailed Problem Investigations & Remediation Evidence

### Problem 1: Financial Publication Timestamps and Regulatory Deadlines
- **Regulatory Framework:**
  - *Provision:* Securities and Exchange Board of India (Listing Obligations and Disclosure Requirements) Regulations, 2015 [SEBI LODR].
  - *Regulation 33(3)(a):* Unaudited quarterly financial results must be submitted to the exchange within **forty-five (45) days** from the end of the quarter.
  - *Regulation 33(3)(d):* Annual audited financial results (Q4 / full fiscal year) must be submitted within **sixty (60) days** from the end of the financial year.
- **Code Audit:**
  - Both `financial_service.py` and `backtesting_dataset_service.py` were verified to enforce the 45-day statutory fallback when `publication_date` is `NULL`.
  - When verified publication timestamps are present, the services give strict precedence to the verified timestamp.
  - Fallback availability dates are explicitly tagged as `ESTIMATED_REPORTING_LAG` and `is_financial_publication_verified = False`.
- **Remaining Limitation:**
  - Because public yfinance feeds do not scrape regulatory announcements, all 260 existing quarterly records in `database/swing_trading.db` retain `publication_date = NULL`. They are conservatively modeled via the statutory 45-day lag.

### Problem 2: Holiday Flat Bars & Market-Data Anomalies
- **Forensic Findings:**
  - All 106 flat bars ($O=H=L=C, \text{Volume}=0$) were traced:
    - 51 bars on `2025-03-18`: NSE Exchange Holiday for **Holi**.
    - 52 bars on `2026-01-15`: NSE Exchange Holiday for **Municipal Elections / Makar Sankranti**.
    - 3 isolated stale bars on active trading days: `M&M` (2025-09-08), `ETERNAL` (2025-04-11, 2025-04-15).
  - On these holiday dates, the provider carried forward the previous active session's closing price.
- **Remediation Implementation:**
  - Authored [`backend/data_pipeline/research_market_data_filter.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/research_market_data_filter.py).
  - Provides `detect_market_data_anomalies(df)` and `filter_research_market_data(df)`.
  - Safely tags synthetic holiday bars as `SYNTHETIC_HOLIDAY_BAR` and excludes them from indicator calculation windows and backtest signals without modifying the underlying database.

### Problem 3: Corporate-Action Integrity & Price Discontinuities
- **Discontinuity Scan:**
  - A full cross-sectional scan across all 25,746 bars identified exactly 2 single-day price moves $> 25\%$:
    - `TMPV` on `2025-10-14`: Dropped from ₹660.75 to ₹395.45 (**-40.15%**) due to the corporate demerger of Tata Motors commercial and passenger vehicle divisions.
    - `TRENT` on `2026-01-01`: Dropped from ₹4,279.00 to ₹2,864.93 (**-33.05%**).
- **Price Basis Separation:**
  - Execution prices, entry zones, stop losses, and targets strictly use **raw unadjusted prices**.
  - Total return benchmarking uses **adjusted close** (`adjusted_close`).
- **Remediation Implementation:**
  - Authored `CorporateActionRecord` schema in [`backend/data_pipeline/universe_metadata.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/universe_metadata.py) to standardize future corporate action ingestion.

### Problem 4: Historical Universe & Survivorship Bias
- **Universe Analysis:**
  - The 52 stocks represent surviving large-cap constituents as of August 2026.
  - Omitted historical constituents that exited the Nifty 50 prior to 2026 are not captured.
- **Governance Remediation:**
  - Authored `ResearchUniverseMetadata` in [`backend/data_pipeline/universe_metadata.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/universe_metadata.py).
  - Backtest artifacts and research reports must explicitly label the universe as `FIXED_SURVIVOR_SAMPLE` and disclose that multi-year performance is subject to positive survivorship bias.

### Problem 5: Test Passing vs. Research Validity & Cost Modeling
- **Cost Model Reconciliation:**
  - Statutory equity delivery charges were verified:
    - Brokerage: ₹0 (discount broker equity delivery).
    - STT: 0.1% on buy + 0.1% on sell turnover.
    - NSE Exchange Charges: 0.00297% on turnover.
    - SEBI Turnover Fee: ₹10 per crore (0.0001%).
    - Stamp Duty: 0.015% on buy turnover only.
    - GST: 18% on (Brokerage + Exchange + SEBI charges).
    - Depository Participant (DP) Charge: ₹15.93 (₹13.50 + 18% GST) per sell transaction (CDSL/broker depository fee).
- **Research Validity Distinction:**
  - An algorithmic backtest can pass 100% of software tests while failing economically in real market conditions.
  - AUDIT-045 proved that the Support Pullback prototype produced **-₹253.86 net loss** under 10 bps slippage and DP charges, and that 100% of gross profits were concentrated in a single ticker (`SHRIRAMFIN`). Software test passage does not imply commercial edge.

---

## 4. Research Validation Matrix

| Research Dimension | Test Implementation | Tested Assertion | Data Basis | Empirical Result | Known Research Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PIT Financial Safety** | `test_audit_037` (32 tests) | No quarter selected if period end or fallback lag > eval date | SQLite `quarterly_results` | **PASS** | Relies on 45-day statutory fallback; exact publication hour unverified. |
| **Market Data Boundaries** | `test_audit_046` (Rule 7) | High >= Low; Open/Close bounded in [Low, High] | SQLite `daily_prices` (25,746 bars) | **PASS** | 103 holiday flat bars must be filtered via `research_market_data_filter`. |
| **Multi-Quarter Fundamental Scoring** | `test_audit_040`, `test_audit_041` | Cold-start requires 4Q for TTM and 5Q for YoY growth | Staged quarters | **PASS** | 11-month fundamental blackout (2025-04 to 2026-02) due to lack of pre-2025 data. |
| **Trade Execution Causality** | `test_audit_044` (7 tests) | Evaluation at Day $T$ close; execution at Day $T+1$ open | Historical bar series | **PASS** | Assumes liquid market open; does not model intra-day liquidity constraints. |
| **Transaction Cost Drag** | `test_audit_045` (5 tests) | Complete Zerodha delivery friction including DP fees | Multi-year trade ledger | **PASS** | Proves Support Pullback net negative (-₹253.86 net P&L); high single-stock concentration. |
| **Holiday Bar Filtering** | `test_audit_047` (`test_05`, `test_06`) | Filters known holiday flat bars non-destructively | Synthetic & actual bars | **PASS** | Applies to research filter layer; production SQLite DB retains raw data. |
| **Price Discontinuity Flagging** | `test_audit_047` (`test_07`, `test_08`) | Detects returns > 25% for unadjusted corporate actions | Historical & fixture bars | **PASS** | Corporate actions table not yet populated with historical corporate circulars. |
| **Universe Bias Disclosure** | `test_audit_047` (`test_09`, `test_10`) | Discloses fixed survivor universe limitation | Universe metadata | **PASS** | Point-in-time constituent history prior to August 2026 is unavailable. |

---

## 5. Final Decision Categories

| Category | Description | Status | Evidence & Quantitative Justification |
| :--- | :--- | :---: | :--- |
| **A** | **Market-Data Integrity** | **PASS WITH LIMITATIONS** | 25,746 bars valid; 103 holiday flat bars isolated and filtered via non-destructive research layer. |
| **B** | **Financial Publication-Time Reliability** | **PARTIAL** | Enforced 45d statutory fallback and verified timestamp precedence in code. 260 DB records lack exchange timestamps. |
| **C** | **Point-in-Time Eligibility Implementation**| **PASS** | Explicit 8-rule PIT eligibility contract strictly implemented and enforced across all access services. |
| **D** | **Corporate-Action Integrity** | **PARTIAL** | Price discontinuity detection and metadata schema implemented. Raw vs adjusted close separated. Historical corporate action table pending. |
| **E** | **Historical-Universe Integrity** | **PARTIAL** | Fixed 52-stock survivor sample. Governance metadata added; point-in-time constituent rebalancing history pending. |
| **F** | **Transaction-Cost Accuracy** | **PASS** | Statutorily complete delivery cost model (brokerage, STT, NSE, SEBI, Stamp Duty, GST, and ₹15.93 CDSL DP charges). |
| **G** | **Backtest Accounting Integrity** | **PASS** | Whole-share integer sizing, cash balance reconciliation, and floating-point ledger identity verified down to machine precision. |
| **H** | **Reproducibility** | **PASS** | 100.0% deterministic multi-year trade execution across repeated independent test runs. |
| **I** | **Technical-Only Exploratory Research Readiness** | **PASS WITH LIMITATIONS** | Pure price-action and technical indicator research is feasible on filtered market data across the 52-stock survivor universe. |
| **J** | **Fundamental Research Readiness** | **BLOCKED** | Paralyzed by lack of pre-2025 quarterly statements (11-month cold-start blackout). Blocked until historical quarters are staged. |
| **K** | **Historical Constituent Research Readiness** | **BLOCKED** | Blocked until historical Nifty 50 constituent addition/deletion dates prior to August 2026 are archived. |
| **L** | **Production Integration Readiness** | **STRICTLY BLOCKED** | Prototypes cannot be merged into production engines. |
| **M** | **Live-Trading Readiness** | **STRICTLY BLOCKED** | Automated live capital deployment remains completely prohibited. |

---

## 6. Final Integrity Verifications

1. **Production Database Checksum:**
   ```
   SHA-256: 1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8 (100% Invariant)
   File Size: 9,068,544 bytes
   ```
2. **Staging Database Checksum:**
   ```
   SHA-256: 4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465 (100% Invariant)
   File Size: 5,410,816 bytes
   ```
3. **Audit Regression Test Suite Execution:**
   - Command: `python -m pytest backend/tests/test_audit_047* backend/tests/test_audit_046* backend/tests/test_audit_045* backend/tests/test_audit_044* backend/tests/test_audit_043* backend/tests/test_audit_042* backend/tests/test_audit_041* backend/tests/test_audit_040* backend/tests/test_audit_037* -q`
   - Result: `97 passed, 50 warnings in 1.90s` (100% green across 9 test modules).
4. **Git Working Tree:**
   - Zero commits, zero pushes. Clean uncommitted work tree confined strictly to non-destructive research filters, schemas, audit tests, and audit documentation.

