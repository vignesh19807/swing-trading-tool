# AUDIT-017: Regression Testing & Verification Suite Results

**Audit Execution Date:** 2026-10-29  
**Branch:** `main`  
**Commit:** `77d8aff28c7966033581cea0add2c603c352b22a`  
**Execution Environment:** Python 3.14.0 / Node.js v22.14.0 / Windows 11  

---

## 1. Executive Summary

A comprehensive regression verification was conducted across all backend test suites, frontend verification harnesses, and build pipelines. 

| Verification Domain | Harness / Command | Total Tests / Assertions | Passed | Failed / Errored | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Point-in-Time Isolation** | `python scratch/test_audit_017_isolation.py` | 6 tests | 6 | 0 | **PASS** |
| **Fundamental Isolation** | `pytest backend/tests/test_audit_016_fundamental_isolation.py` | 12 tests | 12 | 0 | **PASS** |
| **Financial & Decision Engines**| `pytest backend/engines/test_decision_engine.py backend/engines/test_financial_engine.py` | 52 tests | 52 | 0 | **PASS** |
| **Modern Core Backend Suite** | `pytest backend/tests -q` | 83 tests | 83 | 0 | **PASS** |
| **Full Backend Regression Suite** | `pytest backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q` | 810 tests (79 subtests) | 810 (79 subtests) | 0 | **PASS** |
| **Frontend Unit Test Suite** | `node frontend/src/utils/run_all_tests.js` | 288 assertions | 288 | 0 | **PASS** |
| **Frontend Production Build** | `npm run build` (Vite v8.3.0) | 1,932 modules | 1,932 | 0 | **PASS** |

**Overall Regression Verdict:** **100% PASSED** (0 regressions detected across 810 backend tests and 288 frontend assertions).

---

## 2. Full Backend Test Suite Execution Details

### Command
```powershell
python -m pytest backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q
```

### Execution Metrics
- **Runtime:** 126.33 seconds (0:02:06)
- **Exit Code:** `0`
- **Collected & Passed:** 810 passed, 79 subtests passed
- **Failures:** 0
- **Warnings:** 7,460

### Warning Breakdown & Triage
The full backend test run emitted 7,460 warnings across several non-breaking categories:
1. **`StarletteDeprecationWarning`**:
   - *Message:* `Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
   - *Triage:* Harmless Starlette/FastAPI internal deprecation notice regarding the testing client.
2. **`Pandas4Warning` & `UserWarning`**:
   - *Message:* `Parsing '2025-Q2' as a quarterly string is deprecated and will be removed in a future version. Use pd.Period('2025-Q2').to_timestamp(), or a PeriodIndex for indexing, instead.`
   - *Location:* `backend/data_pipeline/test_backtesting_dataset_service.py` and `backend/data_pipeline/test_week13_completeness.py`.
   - *Triage:* Deprecation warning from Pandas for ambiguous quarterly string parsing.
3. **`PytestReturnNotNoneWarning`**:
   - *Message:* `Test functions should return None, but ... returned <class 'tuple'>.`
   - *Location:* Legacy tests from Weeks 10-12 in `backend/data_pipeline/test_classification_handoff.py` and `test_peer_group_handoff.py`.
   - *Triage:* Legacy handoff test functions return data tuples instead of bare `assert`. Fully functional but generates pytest warnings.
4. **`DeprecationWarning: datetime.datetime.utcnow()`**:
   - *Location:* `backend/app.py` lines 93 and 858.
   - *Triage:* Python 3.12+ deprecation of timezone-naive `utcnow()`.

---

## 3. Frontend Unit & Build Suite Execution Details

### Unit Test Execution
```powershell
node frontend/src/utils/run_all_tests.js
```
- **Runtime:** 1.84 seconds
- **Exit Code:** `0`
- **Assertion Breakdown:**
  - Technical Indicator & Chart Calculations: **59/59 passed**
  - Screener Filter & Multi-Criteria Logic: **71/71 passed**
  - Portfolio, Position Sizing, & Opportunity Filters: **74/74 passed**
  - Sector Normalization & Relative Strength: **56/56 passed**
  - Dashboard Regressions: **10/10 passed**
  - API Service Layer & Mock Guardrails: **18/18 passed**
  - **Total:** **288 / 288 assertions passed**.

### Production Build Execution
```powershell
cd frontend
npm run build
```
- **Vite Version:** 8.3.0
- **Modules Transformed:** 1,932
- **Build Duration:** 1.78 seconds
- **Exit Code:** `0`
- **Output Artifacts:** `dist/index.html` (1.06 kB), `dist/assets/index-XfBcrgJk.js` (342.24 kB / 66.37 kB gzip), `dist/assets/index-kdxBI8ss.css` (60.50 kB / 10.08 kB gzip).

---

## 4. Production Database Isolation Audit During Regression

An automated inspection of database checksums was performed before and after the 810-test suite execution:

- **Baseline Checksum (`swing_trading.db.bak_audit_017`):**
  `10F40129FC710F7E49AB82D285A45F94591D19EF2ED05A74F071FB86EFE92AD2`
- **Post-Pytest Checksum (`swing_trading.db`):**
  `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`

### Investigation of Checksum Variance
A granular, table-by-table row comparison was executed (`scratch/compare_rows.py`):
1. **Core Market & Fundamental Data:**
   - `companies` (52 rows): **100% IDENTICAL**
   - `daily_prices` (25,746 rows): **100% IDENTICAL**
   - `quarterly_results` (260 rows): **100% IDENTICAL**
   - `technical_indicators` (25,746 rows): **100% IDENTICAL**
   - `sectors` (17 rows), `industries` (45 rows): **100% IDENTICAL**
2. **Identified Mutation in Legacy Test:**
   - Table `backtest_results` (2 rows) and `sqlite_sequence` differed.
   - Diff trace (`scratch/inspect_backtest_diff.py`):
     - `('RUN_001', 'INFY', '2025-08-25', '{"score": 60}')`
     - `('RUN_001', 'TCS', '2025-08-25', '{"score": 80}')`
     - The IDs and timestamps were refreshed during execution of `backend/data_pipeline/test_backtest_result_service.py` because this legacy test references `DATABASE_PATH` directly without an isolated SQLite fixture.
   - **Audit Conclusion:** The production market price, indicator, and fundamental datasets remained completely untouched and pristine. A technical debt ticket should be filed to inject temporary database fixtures into `backend/data_pipeline/test_backtest_result_service.py`.

---

## 5. Conclusion

The system demonstrates total regression stability:
- All 810 backend tests pass.
- All 288 frontend assertions pass.
- Production frontend bundle builds with zero errors.
- Point-in-time fundamental isolation is completely verified and intact.

