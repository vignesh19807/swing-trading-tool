# AUDIT-037: Historical Financial Eligibility Remediation Report

**Audit Sequence:** AUDIT-037  
**Execution Timestamp:** 2026-11-01T12:15:00+05:30  
**Role:** Senior Python Data-Engineering and Quantitative-Research Engineer  
**Repository Working Directory:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Path:** `database/swing_trading.db`  
**Baseline Database SHA-256:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`  
**Post-Audit Database SHA-256:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (100% Invariant)  

---

## 1. Initial Finding & Investigation Outcome

### Initial Hypothesis
The prompt requested verification of whether the historical backtesting dataset builder (`backend/data_pipeline/backtesting_dataset_service.py`) could select a quarterly financial record before its estimated or verified availability date, bypassing the established eligibility rules in `backend/data_pipeline/financial_service.py`.

### Audit Result: CONFIRMED (High Severity Data-Integrity Defect)
The investigation **100% confirmed** the defect in `backend/data_pipeline/backtesting_dataset_service.py`:
1. `build_backtesting_dataset(symbol, ...)` invoked `get_financial_data(symbol)` with `evaluation_date=None`, retrieving an unfiltered snapshot of all quarters.
2. `get_financial_data(symbol)` dropped the `publication_date` column from its output DataFrame because it was not listed in `FINANCIAL_COLUMNS`.
3. In `_prepare_financial_data(financial, evaluation_date)`:
   The selection logic filtered records purely by:
   ```python
   eligible = data[data["_quarter_date"] <= evaluation_timestamp].copy()
   ```
   where `_quarter_date` was the quarter period-end timestamp (e.g. `2025-03-31 23:59:59.999999` for `2025-Q1`).
4. **Immediate Consequence:** On evaluation date `2025-04-01` (1 day after quarter end), the condition `2025-03-31 <= 2025-04-01` evaluated to `True`. The service attached `2025-Q1` financial fundamentals to April 1st—**44 days before the statutory 45-day reporting lag** (`2025-05-15`) and **weeks before actual corporate earnings announcement dates**.
5. Even if a quarterly record contained an actual `publication_date` (e.g. `2025-04-20`), evaluating on `2025-04-10` still selected `2025-Q1`, causing a direct lookahead leak.
6. The service's internal `leakage_check` column only verified `reporting_period <= evaluation_date`. Because `_quarter_date <= evaluation_timestamp` was satisfied, `leakage_check` silently recorded `"PASS"`, masking premature data leakage.

---

## 2. Affected Files & Functions

| File Path | Function / Component | Defect Description |
| :--- | :--- | :--- |
| `backend/data_pipeline/financial_service.py` | `get_financial_data` | Dropped `publication_date` column from `result_df` when returning `data[FINANCIAL_COLUMNS]`, preventing downstream callers from accessing publication timestamps. |
| `backend/data_pipeline/backtesting_dataset_service.py` | `_prepare_financial_data` | Filtered exclusively by `period_end <= evaluation_date`. Completely ignored `publication_date` and the 45-day statutory fallback lag. |
| `backend/data_pipeline/backtesting_dataset_service.py` | `build_backtesting_dataset` | Did not pass `reporting_lag_days` parameter; labeled unverified fallback records with ambiguous status; leakage check only validated reporting period end date. |
| `backend/data_pipeline/backtest_data_access_service.py` | `get_backtest_input`, `get_backtest_inputs` | Relied on `build_backtesting_dataset` without exposing or configuring `reporting_lag_days`. |
| `backend/tests/test_historical_financial_safety.py` | `test_02_dates_at_quarter_end`, `test_03_publication_lag_limitation_documentation` | Asserted legacy defective behavior (asserting `2025-Q2` was eligible on `2025-07-01` and `2025-07-05`, 1 and 5 days after quarter end). |

---

## 3. Root Cause Analysis

1. **Architectural Disconnect between Weeks 11 and 13:**
   - In Week 11 (AUDIT-016), `backend/data_pipeline/financial_service.py` was enhanced to support `evaluation_date` and `reporting_lag_days=45` for fundamental scoring analyzers (`analyze_roe`, `analyze_growth`, etc.).
   - However, the tabular dataset builder in `backend/data_pipeline/backtesting_dataset_service.py` (authored in Week 13) was implemented independently. To optimize execution speed over hundreds of evaluation dates, it fetched the entire financial table once via `get_financial_data(symbol)` and implemented its own local `_prepare_financial_data` helper.
2. **Conflation of "Period-End" with "Public Availability":**
   - The developer of `_prepare_financial_data` assumed that checking `period_end <= evaluation_date` prevented lookahead bias ("never select a reporting period after evaluation date").
   - This prevented *future-quarter* leakage (e.g., selecting Q3 in Q1), but failed to prevent *pre-availability* leakage (selecting Q1 during the 45-day statutory lag between quarter end and public disclosure).
3. **Misleading `leakage_check`:**
   - `leakage_check` compared `reporting_period > evaluation_date`. Because the code pre-filtered by `reporting_period <= evaluation_date`, `leakage_check` was guaranteed to be `"PASS"`, providing a false positive assurance of zero lookahead bias.

---

## 4. Synthetic Reproduction: Before vs. After

### Minimal Synthetic Scenario
- **Quarter 1 (`2024-Q4`):** Period ends `2024-12-31`. Verified publication timestamp: `2025-01-25`.
- **Quarter 2 (`2025-Q1`):** Period ends `2025-03-31`. Verified publication timestamp: `2025-04-20`.
- **Evaluation Date:** `2025-04-10` (10 days after Q1 ends, but 10 days **before** Q1 is published).

### Execution Traces

#### BEFORE FIX:
```python
fin_df = pd.DataFrame([
    {"quarter": "2024-Q4", "revenue": 100, "publication_date": "2025-01-25"},
    {"quarter": "2025-Q1", "revenue": 120, "publication_date": "2025-04-20"},
])

rec, status = _prepare_financial_data(fin_df, "2025-04-10")
# OUTPUT:
# Selected quarter: 2025-Q1  <-- DEFECT: Leaked 10 days before publication!
# Status: PERIOD_ELIGIBLE_AVAILABILITY_UNVERIFIED
```

#### AFTER FIX:
```python
rec, status = _prepare_financial_data(fin_df, "2025-04-10")
# OUTPUT:
# Selected quarter: 2024-Q4  <-- CORRECT: 2025-Q1 excluded; latest published quarter selected
# Status: VERIFIED_POINT_IN_TIME
```

#### Fallback Lag Scenario (Missing Publication Timestamps):
- **Quarter 1 (`2025-Q1`):** Period ends `2025-03-31`. `publication_date`: `None`. Fallback 45-day availability: `2025-05-15`.
- **Evaluation Date 1:** `2025-04-10` -> Excluded (`rec = None`, `status = "NO_ELIGIBLE_RECORDS"`).
- **Evaluation Date 2:** `2025-05-20` -> Eligible (`rec["quarter"] = "2025-Q1"`, `status = "PERIOD_ELIGIBLE_FALLBACK_LAG"`).

---

## 5. Implementation Changes

### 1. `backend/data_pipeline/financial_service.py`
Preserved `publication_date` in output DataFrame of `get_financial_data`:
```python
result_df_cols = list(FINANCIAL_COLUMNS)
if "publication_date" in data.columns and "publication_date" not in result_df_cols:
    result_df_cols.append("publication_date")

result_df = data[result_df_cols].copy()
```

### 2. `backend/data_pipeline/backtesting_dataset_service.py`
- Imported canonical timestamp normalization utilities: `parse_quarter_period_end`, `_normalize_eval_timestamp`, `_normalize_pub_timestamp`.
- Re-architected `_prepare_financial_data` to strictly enforce:
  1. **Future Period Elimination:** `if period_end > eval_ts: continue`.
  2. **Verified Publication Date:** If `pub_ts` is not None and `pub_ts <= eval_ts`: record is eligible (`VERIFIED_POINT_IN_TIME`).
  3. **Estimated Fallback Lag:** If `pub_ts` is None: `avail_ts = period_end + pd.Timedelta(days=reporting_lag_days)`. Eligible if `avail_ts <= eval_ts` (`PERIOD_ELIGIBLE_FALLBACK_LAG`).
  4. **Multi-Quarter Selection:** Sorts eligible records chronologically by `(period_end, avail_ts)` and selects the latest eligible quarter.
- Added parameter `reporting_lag_days: int = 45` to `build_backtesting_dataset`.
- Added explicit, unambiguous audit fields to the constructed dataset:
  - `publication_date`: The verified publication date string, or `None`.
  - `financial_eligibility_mode`: `"VERIFIED_PUBLICATION"` | `"ESTIMATED_REPORTING_LAG"` | `"NO_ELIGIBLE_RECORDS"` | `"MISSING"`.
  - `is_financial_publication_verified`: `True` | `False` | `None`.
  - `financial_availability_status`: `"VERIFIED"` if verified publication date was used; `"UNVERIFIED"` if estimated fallback lag was used; `"MISSING"` if missing.
- Upgraded `leakage_check` to detect:
  1. Future reporting periods (`FAIL_FUTURE_FINANCIAL_PERIOD`).
  2. Premature publication leaks (`FAIL_PRE_PUBLICATION_LEAK`).
  3. Premature fallback leaks (`FAIL_PRE_AVAILABILITY_LEAK`).

### 3. `backend/data_pipeline/backtest_data_access_service.py`
Added `reporting_lag_days: int = 45` to `get_backtest_input` and `get_backtest_inputs`, forwarding it to `build_backtesting_dataset`.

### 4. `backend/tests/test_historical_financial_safety.py`
Updated `test_02_dates_at_quarter_end` and `test_03_publication_lag_limitation_documentation` to assert the corrected eligibility rules:
- Proves that without publication date and with 45-day lag, Q2 is NOT eligible on July 1 or July 5 (Q1 is selected).
- Proves that when zero reporting lag is explicitly passed (`reporting_lag_days=0`), Q2 is immediately eligible on July 1.
- Proves that after 45 days (August 15), Q2 is eligible under default fallback lag.
- Proves that when a verified publication date is present, Q2 is eligible on its publication date.

---

## 6. Comprehensive Test Cases & Results

### Dedicated Regression Test Suite: `test_audit_037_historical_financial_eligibility.py`
Created 12 rigorous synthetic regression tests in `backend/tests/test_audit_037_historical_financial_eligibility.py`:

| Test Name | Scenario Tested | Result |
| :--- | :--- | :--- |
| `test_01_publication_before_evaluation_date` | Record published prior to cutoff is eligible (`VERIFIED_POINT_IN_TIME`). | **PASSED** |
| `test_02_publication_after_evaluation_date` | Record published after cutoff is excluded (returns `NO_ELIGIBLE_RECORDS`). | **PASSED** |
| `test_03_period_ended_before_eval_date_but_published_afterward` | Period ended before cutoff but published afterward excludes current quarter and selects previous quarter (`2024-Q4`). | **PASSED** |
| `test_04_missing_pub_timestamp_fallback_before_cutoff` | Missing publication timestamp with cutoff > (period_end + 45d) is eligible (`PERIOD_ELIGIBLE_FALLBACK_LAG`). | **PASSED** |
| `test_05_missing_pub_timestamp_fallback_after_cutoff` | Missing publication timestamp with cutoff within 45d window excludes current quarter and selects previous quarter. | **PASSED** |
| `test_06_invalid_publication_timestamp_falls_back_safely` | Corrupted publication string falls back to 45d lag; never silently verified. | **PASSED** |
| `test_07_future_reporting_period_strictly_excluded` | Quarter whose period ends after cutoff is never selected, even if synthetic pub date was premature. | **PASSED** |
| `test_08_no_eligible_records_returns_none_and_explicit_status` | Returns `(None, 'NO_ELIGIBLE_RECORDS')` when all quarters are post-cutoff. | **PASSED** |
| `test_09_multiple_quarters_selects_latest_eligible_older_quarter` | Among 4 quarters, selects the latest eligible older quarter (`2024-Q4`). | **PASSED** |
| `test_10_date_only_evaluation_cutoff_applies_eod_semantics` | Date-only `YYYY-MM-DD` cutoff applies `23:59:59.999999` end-of-day cutoff. | **PASSED** |
| `test_11_timestamp_evaluation_cutoff_exact_hour` | Exact timestamp cutoff (e.g. 10:00 vs 15:00) precisely respects publication hour. | **PASSED** |
| `test_12_consistent_eligibility_between_services` | 100% agreement between `get_financial_data(..., eval_date)` and `_prepare_financial_data(..., eval_date)` across 10 evaluation dates in isolated DB. | **PASSED (10 subtests)** |

### Full Test Suite Execution Summary
- **Focused Dataset & Financial Service Suite:**
  - `backend/data_pipeline/test_backtesting_dataset_service.py` (19 tests) -> **19 PASSED**
  - `backend/data_pipeline/test_backtest_data_access_service.py` (15 tests) -> **15 PASSED**
  - `backend/tests/test_historical_financial_safety.py` (6 tests) -> **6 PASSED**
  - `backend/tests/test_audit_016_fundamental_isolation.py` (12 tests) -> **12 PASSED**
  - `backend/tests/test_audit_037_historical_financial_eligibility.py` (12 tests) -> **12 PASSED (10 subtests)**
  - `backend/data_pipeline/test_financial_handoff.py` (1 test) -> **1 PASSED**
  - Total Focused: **65 tests, 10 subtests PASSED (100%)**
- **Full Backend Regression Suite:**
  - Non-contract suite: **809 passed, 89 subtests passed, 0 failed** in 124.64s (Exit code: 0)
  - API contract suite: **13 passed, 0 failed** in 13.80s (Exit code: 0)
  - **Combined Backend Total: 822 passed, 89 subtests passed, 0 failed, 0 skipped (Exit code: 0)**
- **Frontend Test Suite:**
  - `node frontend/src/utils/run_all_tests.js`: **288 assertions passed, 0 failed**.

---

## 7. Production Database Checksum Comparison

- **Database File:** `database/swing_trading.db`
- **File Size:** 9,068,544 bytes
- **Pre-Audit SHA-256:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Post-Audit SHA-256:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Integrity Status:** **100% BYTE-FOR-BYTE INVARIANT**. Zero database writes or schema modifications occurred on the production database.

---

## 8. Explicit Distinction: Verified vs. Estimated Financial Availability

To ensure institutional clarity and prevent misleading audit claims, the platform now maintains three distinct availability tiers:

1. **Verified Point-in-Time Availability (`VERIFIED_POINT_IN_TIME` / `VERIFIED_PUBLICATION`):**
   - **Criterion:** An empirical corporate filing timestamp (`publication_date`) exists from official exchange feeds (NSE/BSE corporate announcements) and is $\le$ `evaluation_cutoff`.
   - **Audit Field:** `is_financial_publication_verified = True`, `financial_availability_status = "VERIFIED"`.
2. **Estimated Statutory Fallback Availability (`PERIOD_ELIGIBLE_FALLBACK_LAG` / `ESTIMATED_REPORTING_LAG`):**
   - **Criterion:** `publication_date` is `NULL` or missing. Availability is conservatively approximated as $T_{\text{avail}} = \text{period\_end} + 45\text{ calendar days}$ (derived from SEBI LODR Regulation 33(3)(a)).
   - **Audit Field:** `is_financial_publication_verified = False`, `financial_availability_status = "UNVERIFIED"`.
   - **Limitation:** In reality, companies may report earlier (e.g. IT majors report 15–20 days post quarter-end) or face statutory extensions. This fallback is an **eligibility assumption**, not empirical proof of disclosure timing.
3. **Unavailable / Ineligible (`NO_ELIGIBLE_RECORDS` / `MISSING`):**
   - **Criterion:** No quarterly record meets either the verified publication or 45-day fallback cutoff as of the evaluation date.
   - **Audit Field:** `is_financial_publication_verified = None`, `financial_availability_status = "MISSING"`.

---

## 9. Remaining Limitations

1. **Production Database Publication Timestamps:**
   - 100% (260/260) of quarterly results records in `database/swing_trading.db` currently have `publication_date IS NULL`.
   - Therefore, when running backtests against the current production database, all financial records operate under the **45-day statutory fallback model** (`financial_availability_status = "UNVERIFIED"`).
   - Complete lookahead-bias immunity cannot be mathematically guaranteed until official NSE/BSE corporate announcement feeds are integrated to populate `quarterly_results.publication_date`.
2. **Annual Financials:**
   - Audited annual financial statements are governed by SEBI LODR Regulation 33(3)(d), which grants listed companies 60 days following financial year-end (March 31) to submit audited annual accounts. The annual financial analyzer utilizes its own standalone logic.

---

## 10. Audit Verdict

### **VERDICT: PASS (REMEDIATION FULLY VERIFIED)**

- **Defect Resolution:** Confirmed that `backend/data_pipeline/backtesting_dataset_service.py` no longer selects financial records prematurely. A reporting period ending before evaluation date $D$ is **never** automatically treated as available by $D$.
- **Consistency:** 100% mathematical and logical consistency established between `financial_service.py` and `backtesting_dataset_service.py`.
- **Test Integrity:** 822 backend tests passing with zero failures. Zero weakened assertions. Zero skipped tests.
- **Database Safety:** Production database `database/swing_trading.db` preserved in an identical, immutable state (SHA-256 verified invariant).
- **No Strategy Modifications:** Zero changes to trading rules, indicator formulas, scoring weights, stop-loss/target parameters, or position sizing.

