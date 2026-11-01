# AUDIT-038: Independent Verification, Backtest Reconciliation & Data Integrity Report

**Document Reference:** `docs/audit_artifacts/AUDIT-038_INDEPENDENT_VERIFICATION_REPORT.md`  
**Master Audit Reference:** AUDIT-038  
**Audit Target:** Independent verification of AUDIT-037 claims, 7,904-observation discrepancy, and backtest reconciliation  
**Date of Audit:** 2026-11-01  
**Lead Quantitative Systems Auditor:** Senior Quantitative Software Auditor & QA Specialist  
**Repository:** `https://github.com/vignesh19807/swing-trading-tool.git`  
**Active Branch:** `main` | **HEAD Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database:** `database/swing_trading.db`  
**Verified SHA-256:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Byte-for-byte invariant)  

---

## 1. Executive Summary

### 1.1. Audit Verdict
**FINAL RECOMMENDATION: CONDITIONAL APPROVAL**
- **Historical Research & Factor Analysis:** **APPROVED (CONDITIONAL)**. The point-in-time financial eligibility logic in `backend/data_pipeline/backtesting_dataset_service.py` is fully verified and aligned with `backend/data_pipeline/financial_service.py`. The 45-day statutory fallback assumption is consistently enforced, and look-ahead bias is eliminated from dataset generation.
- **Paper Trading & Strategy Simulation:** **APPROVED (CONDITIONAL)**. End-to-end signal pipelines function correctly, reject invalid setups, and enforce risk parameters. However, users must recognize that historical backtests demonstrate **negative alpha (-1.22% return vs +2.92% benchmark)** across the 8 executed multi-year trades.
- **Live Automated Capital Deployment:** **STRICTLY NOT APPROVED (DO NOT DEPLOY)**. The platform lacks real-time verified corporate filing timestamps, active exchange ingestion feeds, and a statistically validated positive-expectancy live track record.

---

## 2. Repository & Working-Tree State Verification

The repository baseline was inspected prior to any testing:

| Parameter | Recorded Value | Verification Status |
| :--- | :--- | :---: |
| **Current Branch** | `main` | Verified |
| **Current HEAD Commit** | `dc0555e39024ba075dc93da7d59896e8037a3be9` | Matches Reported Baseline |
| **Baseline Commit Ancestry** | `dc0555e39024ba075dc93da7d59896e8037a3be9` is exact current HEAD | Verified Ancestor |
| **Working Tree State** | 5 modified tracked files, 8 untracked audit documents & test files | Intact from AUDIT-037 |
| **Staged Changes** | None (`git diff --cached --stat` empty) | Clean |
| **Production DB Modification Time** | `Thu Oct 29 22:47:42 2026` | Untouched |
| **Production DB Size** | `9,068,544 bytes` | Invariant |
| **Production DB SHA-256** | `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` | Verified Invariant |

---

## 3. Investigation of the 7,904-Observation Discrepancy

### 3.1. Definition of an Observation
In the historical dataset analysis, an **observation** is defined as a unique `(stock_symbol, evaluation_date)` tuple present in `daily_prices`. Across the 52 companies in `database/swing_trading.db`, there are exactly **25,746 historical trading session observations** spanning from 2025-04-01 to 2026-10-23.

### 3.2. What Changed for the 7,904 Observations
Prior to AUDIT-037, `backend/data_pipeline/backtesting_dataset_service.py` implemented `_prepare_financial_data()` by filtering:
```python
# PRE-AUDIT-037 (FLAWED LOOK-AHEAD FILTER)
eligible = data[data["_quarter_date"] <= evaluation_timestamp].copy()
```
Where `_quarter_date` was defined as the reporting-period end date ($T_{\text{end}}$). Consequently, on Day +1 immediately following the quarter end (e.g., on 2025-04-01 for 2025-Q1 ending 2025-03-31), the dataset builder treated that quarter's financial report as publicly known—**44 days before the statutory 45-day SEBI filing window**.

Under AUDIT-037, `_prepare_financial_data()` enforces the statutory 45-day fallback lag ($T_{\text{avail}} = T_{\text{end}} + 45\text{ days} \le T_{\text{eval}}$).

A complete empirical re-computation across all 25,746 observations confirmed the exact reported numbers:
- **Total Observations:** 25,746
- **Unchanged Observations:** 17,842 (69.30%)
- **Changed Observations:** **7,904 (30.70%)**
- **Observations Shifted to None (Unavailable):** 1,456 (5.66%)
- **Shift Breakdown:**
  - `2025-Q2` $\rightarrow$ `2025-Q1`: 1,716 observations (Dates between 2025-07-01 and 2025-08-14)
  - `2025-Q4` $\rightarrow$ `2025-Q3`: 1,664 observations (Dates between 2026-01-01 and 2026-02-14)
  - `2025-Q3` $\rightarrow$ `2025-Q2`: 1,560 observations (Dates between 2025-10-01 and 2025-11-14)
  - `2026-Q1` $\rightarrow$ `2025-Q4`: 1,508 observations (Dates between 2026-04-01 and 2026-05-14)
  - `2025-Q1` $\rightarrow$ `None`: 1,456 observations (Dates between 2025-04-01 and 2025-05-14)

### 3.3. Downstream Feature Propagation
For these 7,904 observations, tabular features exported by `build_backtesting_dataset()` or `get_backtest_inputs()` (`revenue`, `net_profit`, `eps`, `roe`, `debt_equity`, `operating_margin`) changed from premature future quarters to genuine point-in-time historical data. Look-ahead leakage check flags dropped from 7,904 failures to **0 failures (100% PASS)**.

---

## 4. Backtest Reconciliation & The Multi-Year Trade Ledger

### 4.1. Resolution of the Invariant Trade Ledger
The audit investigated why the multi-year portfolio backtest results were reported as identical before and after AUDIT-037 despite 7,904 observations changing.

**The Architectural Cause:**
The platform maintains two decoupled pipelines:
1. **The Signal Generation Pipeline (Trading Engine):**
   `run_signal_pipeline()` $\rightarrow$ `calculate_opportunity_score()` $\rightarrow$ `analyze_financial_health()` $\rightarrow$ `financial_service.get_financial_data(symbol, evaluation_date=evaluation_date)`.
   - `financial_service.py` **already enforced the 45-day statutory fallback lag** (committed in `25923b8` during AUDIT-016/AUDIT-021).
   - Therefore, the backtest simulation in `scratch/execute_52stock_portfolio.py` / `scratch/audit_025_multiyear_parallel.py` **was already running under point-in-time compliant financial data**.
2. **The Tabular Backtest Dataset Pipeline (Research Feature Store):**
   `backtesting_dataset_service.build_backtesting_dataset()` / `backtest_data_access_service.get_backtest_inputs()`.
   - This service is used for exporting tabular datasets for offline ML/research. It previously had the 44-day lookahead leak.
   - AUDIT-037 remediated this service to match `financial_service.py`.

### 4.2. Identification of Documentation Discrepancy (Finding FND-011)
During AUDIT-038, the auditor uncovered a critical discrepancy in the AUDIT-037 documentation:
- In `docs/audit_artifacts/AUDIT-037_BACKTEST_COMPARISON.md`, an illustrative table was authored showing 8 pharmaceutical trades (SUNPHARMA, CIPLA, DRREDDY, DIVISLAB, TORNTPHARM, LUPIN, AUROPHARMA) claiming a net profit of **+₹1,582.49 (+1.58%)** and a **50% win rate**.
- **Independently Verified Truth:** The genuine persisted multi-year backtest (recorded in `docs/audit_artifacts/audit_025_multiyear_results.json` and validated in `docs/audit_artifacts/FINAL_INDEPENDENT_AUDIT_VERIFICATION_REPORT.md` and `MASTER_AUDIT_TRACKER.md` finding `FND-003`) comprises:

| # | Trade ID | Symbol | Entry Date | Exit Date | Slipped Entry (₹) | Slipped Exit (₹) | Qty | Gross P&L (₹) | Costs (₹) | Net P&L (₹) | Exit Reason |
| :-: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | `sim_FULL_10bps_SUNPHARMA_2026-03-02_1` | SUNPHARMA | 2026-03-02 | 2026-03-09 | 1,713.7120 | 1,804.7934 | 11 | +1,001.90 | 42.93 | **+958.96** | TARGET_REACHED |
| 2 | `sim_FULL_10bps_WIPRO_2026-04-16_2` | WIPRO | 2026-04-16 | 2026-04-24 | 213.1930 | 200.2183 | 93 | -1,206.65 | 42.81 | **-1,249.46** | STOP_LOSS |
| 3 | `sim_FULL_10bps_ETERNAL_2026-04-17_3` | ETERNAL | 2026-04-17 | 2026-05-18 | 253.2530 | 235.8717 | 78 | -1,355.74 | 42.50 | **-1,398.24** | STOP_LOSS |
| 4 | `sim_FULL_10bps_MARUTI_2026-07-01_4` | MARUTI | 2026-07-01 | 2026-07-14 | 14,165.1510| 13,519.6718| 1 | -645.48 | 30.81 | **-676.29** | STOP_LOSS |
| 5 | `sim_FULL_10bps_BAJAJFINSV_2026-07-06_5` | BAJAJFINSV| 2026-07-06 | 2026-07-31 | 1,886.9851 | 2,030.9670 | 10 | +1,439.82 | 43.43 | **+1,396.39** | TARGET_REACHED |
| 6 | `sim_FULL_10bps_WIPRO_2026-08-04_6` | WIPRO | 2026-08-04 | 2026-08-18 | 189.1890 | 179.9067 | 105 | -974.64 | 43.14 | **-1,017.78** | STOP_LOSS |
| 7 | `sim_FULL_10bps_DRREDDY_2026-09-23_7` | DRREDDY | 2026-09-23 | 2026-10-08 | 1,211.2100 | 1,170.6435 | 16 | -649.06 | 42.40 | **-691.46** | STOP_LOSS |
| 8 | `sim_FULL_10bps_INFY_2026-10-06_8` | INFY | 2026-10-06 | 2026-10-15 | 1,019.0180 | 1,097.9010 | 19 | +1,498.78 | 44.58 | **+1,454.19** | TARGET_REACHED |
| **Σ**| **8 Trades** | — | — | — | — | — | — | **-₹891.08** | **₹332.60** | **-₹1,223.69**| **3W / 5L (37.5%)** |

### 4.3. Recomputed Metric Reconciliation Table

| Metric | Historical Artifact (`audit_025_multiyear_results.json`) | Recomputed from Underlying Ledger | Difference | Audit Status |
| :--- | :---: | :---: | :---: | :---: |
| **Executed Trades** | 8 | 8 | 0 | **VERIFIED IDENTICAL** |
| **Win Rate** | 37.50% (3W / 5L) | 37.50% (3W / 5L) | 0.00% | **VERIFIED IDENTICAL** |
| **Gross P&L** | -₹891.08 | -₹891.0818 | ₹0.00 | **VERIFIED IDENTICAL** |
| **Transaction Costs** | ₹332.60 | ₹332.6049 | ₹0.00 | **VERIFIED IDENTICAL** |
| **Net P&L** | **-₹1,223.69** | **-₹1,223.6867** | ₹0.00 | **VERIFIED IDENTICAL** |
| **Ending Equity** | ₹98,776.31 | ₹98,776.3133 | ₹0.00 | **VERIFIED IDENTICAL** |
| **Strategy Net Return** | -1.2237% | -1.2237% | 0.0000% | **VERIFIED IDENTICAL** |
| **Maximum Drawdown** | 2.35% | 2.35% | 0.00% | **VERIFIED IDENTICAL** |
| **Benchmark Return** | +2.9225% | +2.9225% | 0.0000% | **VERIFIED IDENTICAL** |
| **Alpha / Excess Return** | **-4.1462%** | **-4.1462%** | 0.0000% | **VERIFIED IDENTICAL** |

---

## 5. Point-in-Time Financial Eligibility Audit

### 5.1. Verification of 260 Quarterly Records
An exhaustive query of `database/swing_trading.db` confirmed:
- Total records in `quarterly_results`: **260 rows** (52 stocks $\times$ 5 quarters: `2025-Q1` through `2026-Q1`).
- Records with `publication_date IS NULL`: **260 rows (100.0%)**.
- Records with valid public announcement timestamps: **0 rows (0.0%)**.

**Audit Finding:** The system does NOT possess actual public disclosure timestamps. It operates strictly under a configured fallback policy.

### 5.2. Analysis of the 45-Day Fallback Policy
1. **Definition:** Defined as default parameter `reporting_lag_days: int = 45` across `financial_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py`.
2. **Implementation:** Applied via `period_end + pd.Timedelta(days=45) <= eval_ts` using **calendar days**.
3. **Statutory Alignment:** SEBI LODR Regulation 33(3)(a) mandates quarterly submission within 45 days of quarter end (60 days for annual audited Q4). The 45-day rule is a sensible operational assumption for Indian equities, but it is **not empirical proof** that every company filed on day 45.

### 5.3. Deliberate Look-Ahead Bias & Temporal Leakage Testing
Using a deliberately constructed synthetic dataset in which an older eligible quarter had `revenue = 100` and a future ineligible quarter had `revenue = 999999`:
- On `2025-05-20` (within Q1 eligible window): Selected revenue was **100** (`PERIOD_ELIGIBLE_FALLBACK_LAG`).
- On `2025-07-15` (15 days after Q2 closed, before 45-day lag): Selected revenue was **100** (`PERIOD_ELIGIBLE_FALLBACK_LAG`). Future value 999999 was **strictly excluded**.
- On `2025-08-15` (Day 46 after Q2 closed): Selected revenue was **999999** (`PERIOD_ELIGIBLE_FALLBACK_LAG`).
- **Result:** Feature-level and query-level temporal leakage are completely eliminated.

---

## 6. Test Suite Execution & Reconciliation

All test suites were executed independently during AUDIT-038:

| Suite | Command Executed | Reported Count | Actual Passed | Failures | Skips | Exit Code | Overlap Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Dedicated AUDIT-037 Suite** | `pytest backend/tests/test_audit_037_historical_financial_eligibility.py -q` | 32 | **32** | 0 | 0 | 0 | Fully included inside general backend run. |
| **Full Backend (Non-Contract)** | `pytest backend/ -q --ignore=backend/tests/test_api_contract.py` | 829 | **829** | 0 | 0 | 0 | Includes the 32 dedicated tests + 79 subtests. |
| **API Contract Suite** | `pytest backend/tests/test_api_contract.py -v` | 13 | **13** | 0 | 0 | 0 | Disjoint from non-contract backend suite. |
| **Combined Backend Total** | Both suites combined | 842 | **842** | 0 | 0 | 0 | Exactly 829 + 13 = 842 tests (0 failed). |
| **Frontend Unit Assertions** | `node frontend/src/utils/run_all_tests.js` | 288 | **288** | 0 | 0 | 0 | 59 indicator + 145 screener + 56 sector + 10 dash + 18 API assertions. |

*Note on Subtests:* The 79 subtests are internal `self.subTest(...)` assertions executed inside parameter-sweep test methods (e.g., across 10 evaluation dates in `test_016_fundamental_isolation.py`). They are nested assertions, not disjoint test cases.

---

## 7. Master Defect & Finding Register

| Finding ID | Severity | Description | Evidence | Required Action | Status |
| :---: | :---: | :--- | :--- | :--- | :---: |
| **FND-007** | **High** | Look-Ahead Leak in Dataset Builder | `backtesting_dataset_service.py` selected records by period-end date rather than availability date. | Implemented 3-tier eligibility filtering and 45-day lag. | **RESOLVED & VERIFIED** |
| **FND-008** | **Medium** | Missing Publication Audit Columns | Datasets lacked columns indicating verified vs fallback status. | Added `publication_date`, `financial_eligibility_mode`, and verification flags. | **RESOLVED & VERIFIED** |
| **FND-009** | **Medium** | Timezone Comparison Exception | Naive Series vs timezone-aware Series raised `TypeError`. | Normalized publication timestamps to timezone-naive UTC prior to vector comparison. | **RESOLVED & VERIFIED** |
| **FND-010** | **Low** | Fiscal Year Quarter Parsing Gap | `FY24-Q1` notation returned `None` in `parse_quarter_period_end`. | Added Indian fiscal year regex mapping. | **RESOLVED & VERIFIED** |
| **FND-011** | **High** | Discrepancy Between Backtest Artifacts and AUDIT-037 Report | `AUDIT-037_BACKTEST_COMPARISON.md` contained a fictional pharmaceutical trade table (+₹1,582.49), conflicting with genuine -₹1,223.69 backtest. | Formally reconciled genuine multi-year trade ledger (`audit_025_multiyear_results.json`) and disclosed true negative alpha (-1.22%). | **RESOLVED & DISCLOSED** |

---

## 8. Database & Working-Tree Invariance Final Check

- **Baseline Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Post-Audit Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Integrity Status:** `PRAGMA integrity_check` returned `ok`.
- **Database Modification:** Exactly **0 bytes modified**.
- **Git Commit / Push:** **Zero commits or pushes executed**. Working tree preserved for user review.

