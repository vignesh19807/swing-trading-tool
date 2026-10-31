# AUDIT-014: Full Suite Regression Verification & Warning Analysis

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Execution Environment:** Windows 11, PowerShell, Python 3.14.7, pytest 9.2.0, Node.js v22+, Vite 8.3.0  
**Verification Date:** 2026-10-29  
**Result:** **100% PASSING (ZERO TEST FAILURES, CLEAN PRODUCTION BUILD)**

---

## 1. Master Test Execution Inventory

| Target Test Suite | Exact Command Line Executed | Exit Code | Tests / Assertions | Passed | Failed | Warnings / Notes | Execution Duration |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full Backend Suite** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q` | **0** | 798 tests (+ 79 subtests) | **798** | **0** | 3,962 warnings (99.4% benign pandas date inference notices) | 125.86s (02:05) |
| **Core Modern Acceptance Suite** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests -q` | **0** | 71 tests | **71** | **0** | 2,559 warnings | 68.21s (01:08) |
| **Frontend Unit Suites** | `cd frontend; node src/utils/run_all_tests.js` | **0** | 288 assertions (7 master suites) | **288** | **0** | Zero errors | 2.15s |
| **Frontend Production Build** | `cd frontend; npm run build` (Vite v8.3.0) | **0** | 1,932 modules transformed | **Success** | **0** | Clean bundle generation | 1.63s |

---

## 2. In-Depth Warning Analysis (3,962 Warnings)

An itemized audit of the warning stream was conducted to assess code quality and check for indicators of hidden bugs:

### Warning Taxonomy Breakdown:
1. **Pandas Date Format Fallback Warnings (~3,940 warnings, >99.4% of total):**
   - **Trigger Line:** `df["quarter_dt"] = pd.to_datetime(df["quarter"], errors="coerce")` in `roe_analyzer.py:94`, `roce_analyzer.py:96`, `debt_equity_analyzer.py:104`, `profit_margin_analyzer.py:130`, `growth_analyzer.py:218`, `valuation_analyzer.py:102`, and dataset tests.
   - **Root Cause:** Pandas 2.0+ deprecates ambiguous format parsing and emits a `UserWarning` suggesting an explicit format string (`format='%Y-%m-%d'` or `format='ISO8601'`). Because quarterly financial statements contain mixed notations (`2025-Q1` alongside `2025-03-31`), pandas falls back to `dateutil`, generating a warning per call.
   - **Risk Assessment:** **Benign Library Noise.** All valid strings parse correctly, invalid ones coerce to NaT as expected, and zero numerical errors occur.
2. **Pytest Return-Not-None Warnings (11 warnings):**
   - **Trigger Files:** Legacy handoff tests (`test_classification_handoff.py`, `test_peer_group_handoff.py`).
   - **Root Cause:** Early helper functions return `(True, "message")` tuples rather than bare `None`.
   - **Risk Assessment:** **Benign Legacy Formatting.** All assertions within the test functions execute and pass.
3. **Python 3.12+ `datetime.utcnow()` Deprecations (2 warnings):**
   - **Trigger Files:** `backend/app.py:93` (`/healthz`) and `backend/app.py:858` (`/api/data-health`).
   - **Root Cause:** Python 3.12+ prefers timezone-aware `datetime.now(timezone.utc)`.
   - **Risk Assessment:** **Minor Technical Debt.** Fully functional under current Python 3.14 runtime; clean upgrade path available.
4. **Starlette TestClient Deprecation (~9 warnings):**
   - **Trigger:** Starlette test client importing HTTPX internal client.
   - **Risk Assessment:** **Upstream Library Noise.**

**Conclusion on Warnings:** No warnings indicate arithmetic overflow, memory leaks, unhandled exceptions, division by zero, or NaN contamination.

---

## 3. Frontend Production Build Artifacts

- **Vite Version:** 8.3.0
- **Transformation Status:** 1,932 modules transformed in 1.63s
- **Output Files:**
  - `dist/index.html` (1.06 kB │ gzip: 0.49 kB)
  - `dist/assets/index-kdxBI8ss.css` (60.50 kB │ gzip: 10.08 kB)
  - `dist/assets/index-XfBcrgJk.js` (342.24 kB │ gzip: 66.37 kB)
  - `dist/assets/vendor-react-DrJf331d.js` (207.45 kB │ gzip: 64.62 kB)
  - `dist/assets/vendor-B9FSgnjk.js` (50.78 kB │ gzip: 18.18 kB)
  - `dist/assets/vendor-icons-0D7ea-ru.js` (16.12 kB │ gzip: 5.82 kB)
  - `dist/assets/logo-CeVyrf2i.png` (646.30 kB)
- **Exit Code:** `0`

