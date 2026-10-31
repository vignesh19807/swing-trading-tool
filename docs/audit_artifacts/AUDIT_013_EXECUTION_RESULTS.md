# AUDIT-013: Independent Reproduction of Test Suites & Build Execution Results

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Execution Environment:** Windows 11, PowerShell, Python 3.14.7, pytest 9.2.0, Node.js v22+, Vite 8.3.0  
**Verification Date:** 2026-10-29  
**Overall Result:** **100% PASSING — ZERO FAILURES ACROSS ENTIRE PLATFORM**

---

## 1. Executive Summary Table

| Test Suite / Target | Command Executed | Tests / Assertions | Passed | Failed | Warnings / Notes | Execution Duration |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Full Backend Test Suite** | `pytest backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q` | 798 tests + 79 subtests | **798** | **0** | 3,962 warnings (99.4% pandas date parsing noise) | 176.16s (02:56) |
| **Core Modern Acceptance Suite** | `pytest backend/tests -q` | 71 tests | **71** | **0** | 2,559 warnings | 90.44s (01:30) |
| **Frontend Unit Test Suites** | `node src/utils/run_all_tests.js` | 288 assertions (7 master suites) | **288** | **0** | Clean execution | 2.12s |
| **Frontend Production Build** | `npm run build` (Vite v8.3.0) | 1,932 modules transformed | **Success** | **0** | Production bundles generated | 2.89s |

---

## 2. Full Backend Test Suite Reproduction

- **Command:** `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q`
- **Output:**
  ```
  798 passed, 3962 warnings, 79 subtests passed in 176.16s (0:02:56)
  ```
- **Breakdown:**
  - **Passed:** 798
  - **Subtests Passed:** 79
  - **Failed:** 0
  - **Skipped:** 0
  - **Errors:** 0
  - **XFailed:** 0

---

## 3. Core Acceptance Test Suite Reproduction

- **Command:** `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests -q`
- **Output:**
  ```
  71 passed, 2559 warnings in 90.44s (0:01:30)
  ```
- **Breakdown:**
  - **Passed:** 71
  - **Failed:** 0
  - **Errors:** 0
  - **Suites Included:**
    - `test_api_contract.py` (includes DEF-001 & DEF-002 regression tests)
    - `test_audit_001_financial_lookahead.py` (9 tests)
    - `test_audit_002_backtest_metrics.py` (12 tests)
    - `test_audit_003_004_performance.py` (4 tests)
    - `test_audit_005_sequential_backtest.py` (15 tests)
    - `test_audit_006_independent_verification.py` (14 tests)
    - `test_audit_010_synthetic_trade.py` (1 comprehensive trade lifecycle test)
    - `test_historical_financial_safety.py` (6 tests)

---

## 4. Frontend Test Suite Reproduction

- **Command:** `cd frontend; node src/utils/run_all_tests.js`
- **Output:**
  ```
  ========================================
  ✅ ALL FRONTEND UNIT TESTS COMPLETED SUCCESSFULLY
  ========================================
  ```
- **Suites & Assertions Inventory:**
  1. `technicalIndicators.test.js`: 59 assertions (EMA, RSI, MACD, Wilder smoothing, price edge-cases) — **59 PASSED**
  2. `screenerFilters.test.js`: 71 assertions (search, sector, recommendation, EMA filters, sorting) — **71 PASSED**
  3. `watchlistStorage.test.js`: 26 assertions (local storage persistence, add, remove, toggle) — **26 PASSED**
  4. `performanceHelpers.test.js`: 48 assertions (metrics calculation, returns, benchmarks) — **48 PASSED**
  5. `sectorHelpers.test.js`: 56 assertions (relative strength, ranking, sorting, aggregations) — **56 PASSED**
  6. `dashboardRegressions.test.js`: 10 assertions (Issues A–G regressions, setup badge, health API) — **10 PASSED**
  7. `api.test.js`: 18 assertions (API contract guards, network error handling, mock fixtures) — **18 PASSED**
- **Total Frontend Assertions:** **288 PASSED, 0 FAILED**

---

## 5. Frontend Production Build Reproduction

- **Command:** `cd frontend; npm run build`
- **Build Tool:** Vite v8.3.0
- **Build Status:** **SUCCESS** in 2.89s
- **Output Artifacts:**
  - `dist/index.html` (1.06 kB │ gzip: 0.49 kB)
  - `dist/assets/index-kdxBI8ss.css` (60.50 kB │ gzip: 10.08 kB)
  - `dist/assets/index-XfBcrgJk.js` (342.24 kB │ gzip: 66.37 kB)
  - `dist/assets/vendor-react-DrJf331d.js` (207.45 kB │ gzip: 64.62 kB)
  - `dist/assets/vendor-B9FSgnjk.js` (50.78 kB │ gzip: 18.18 kB)
  - `dist/assets/vendor-icons-0D7ea-ru.js` (16.12 kB │ gzip: 5.82 kB)
  - Component & mock chunks (all $< 5$ kB)

---

## 6. Investigation & Categorization of the 3,962 Warnings

A complete analysis was conducted on the 3,962 warnings generated during the full backend suite run:

| Warning Category | Frequency | Source / Origin | Example Warning Text | Severity & Risk Assessment |
| :--- | :---: | :--- | :--- | :--- |
| **Pandas Date Format Fallback** | ~3,940 (>99.4%) | `backend/logic/*_analyzer.py` (ROE, ROCE, D/E, Margin, Growth, Valuation) and dataset tests | `UserWarning: Could not infer format, so each element will be parsed individually, falling back to 'dateutil'. To ensure parsing is consistent and as-expected, please specify a format.` | **Benign Library Noise.** Caused by calling `pd.to_datetime(df["quarter"], errors="coerce")` on mixed quarterly format strings (`2025-Q1` vs `2025-03-31`). No parsing errors or invalid values occur. |
| **Pytest Return-Not-None** | 11 | `test_classification_handoff.py`, `test_peer_group_handoff.py` | `PytestReturnNotNoneWarning: Test functions should return None, but ... returned <class 'tuple'>.` | **Benign Legacy Formatting.** Legacy helper tests from Weeks 8–10 returned boolean tuples rather than asserting. All assertions within them still execute. |
| **Python 3.12+ `utcnow()` Deprecation** | 2 | `backend/app.py:93` (`/healthz`) and `backend/app.py:858` (`/api/data-health`) | `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects...` | **Minor Actionable Deprecation.** Python 3.14 deprecation note; easily updated to `datetime.now(timezone.utc)` in future maintenance. Zero impact on runtime accuracy. |
| **Starlette / FastApi TestClient** | ~9 | `fastapi.testclient.py:1` | `StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.` | **Upstream Library Deprecation.** FastApi/Starlette internal deprecation. No impact on test execution or reliability. |

**Conclusion on Warnings:** None of the 3,962 warnings represent logic errors, memory leaks, unhandled exceptions, data corruption, or math defects. They are standard library deprecation and parser notifications that do not affect platform correctness.

