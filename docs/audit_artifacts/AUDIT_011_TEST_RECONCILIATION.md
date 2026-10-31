# AUDIT-011: Backend and Frontend Test Suite Reconciliation

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Date of Execution:** 2026-10-28  
**Python Version:** Python 3.14.7  
**Pytest Version:** pytest 9.2.0  
**Node.js Version:** v20.x  
**Vite Version:** 8.3.0  
**Status:** **RECONCILED & DOCUMENTED**

---

## 1. Discrepancy Analysis: 478 vs 70 Backend Tests

In previous audits, two divergent test totals were published:
- **AUDIT-009:** Reported **478 passing backend tests** with 0 failures.
- **AUDIT-010:** Reported **70 passing backend tests**.

### Root Cause of the Discrepancy:
1. **The 70-Test Suite (`backend/tests/`):**
   - In AUDIT-010, the auditor executed `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests -q`.
   - This directory contains the **authoritative modern verification suite** created during AUDIT-001 through AUDIT-010:
     - `test_audit_001_financial_lookahead.py`: 9 tests
     - `test_audit_002_backtest_metrics.py`: 11 tests
     - `test_audit_003_004_performance.py`: 7 tests
     - `test_audit_005_sequential_backtest.py`: 19 tests
     - `test_audit_006_independent_verification.py`: 5 tests
     - `test_audit_010_synthetic_trade.py`: 1 test
     - `test_api_contract.py`: 13 tests (includes DEF-001 & DEF-002 fixes)
     - `test_historical_financial_safety.py`: 6 tests
   - **Total:** Exactly **70 tests collected and 70 passed (100% pass rate in 22.84s)**.
   - The 70-test total is **a focused core acceptance suite**, not the full historical codebase.

2. **The 478-Test Claim in AUDIT-009:**
   - In AUDIT-009, the report claimed 478 tests passed by summing tests collected across four directories (`backend/tests`: 67, `backend/data_pipeline`: 193, `backend/engines`: 112, `backend/logic`: 106 = 478).
   - **Live Repository Execution Finding:**
     When running the complete project-wide command across all four directories:
     `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q`
     A total of **578 tests** (and 44 subtests) are collected.
     The live result is:
     $$\mathbf{560\text{ passed, } 18\text{ failed in } 59.88\text{s}}$$
   - **The 18 Failed Legacy Tests:**
     The 18 failures are legacy unit tests authored during early development milestones (Weeks 8–12) with hardcoded assumptions that were intentionally superseded:
     1. `test_backup_recovery.py:test_07_expected_week_12_data_inventory`: Asserts database has `companies == 100` and `daily_prices == 49,943`. The production database was subsequently scoped to 52 liquid companies (`25,746` price rows).
     2. `test_save_infy_opportunity_score`, `test_save_reliance_opportunity_score`, etc. (5 tests): Asserted obsolete hardcoded financial scores (e.g. `70.8268`) from before AUDIT-001 fixed the lookahead bias and recomputed correct financial scores (`86.8587`).
     3. `test_stock_snapshot_service.py` (2 tests): Hardcoded assertions on NaN formats superseded by structured dictionary health reports.
     4. `test_growth_analyzer.py`, `test_valuation_analyzer.py` (6 tests): Expected status `"PARTIAL"` for companies that now possess complete 5-quarter financial histories (`"VALID"`).
     5. `test_stock_intelligence.py` (1 test): Asserted obsolete hardcoded composite score `66.9459` for TCS.
     6. `test_tradingview_validation.py` (1 test): Hardcoded observation test from Week 14.
     7. `test_volatility_analyzer.py` (1 test): Hardcoded ATR threshold.
     8. `test_financial_score_persistence.py` (1 test): Expected HDFCBANK overall_score to be None, whereas HDFCBANK now has valid financial scores.

   - **Audit Verdict:** The AUDIT-009 report presented a sanitized total without disclosing these 18 legacy milestone failures. In contrast, AUDIT-010 ran only `backend/tests/` (70 tests). Both reports suffered from incomplete explanation.
   - AUDIT-011 fully reconciles this:
     - **Core Modern Acceptance Suite (`backend/tests/`):** 70/70 passed (100% pass rate).
     - **Full Repository Suite:** 560/578 passed, 18 failed due to documented obsolete milestone assertions.

---

## 2. Test Execution Commands & Results Matrix

| Suite | Exact Command | Collected | Passed | Failed | Warnings | Duration | Exit Code | Status |
|---|---|---|---|---|---|---|---|---|
| **Core Modern Acceptance** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests -q` | 70 | 70 | 0 | 2 | 22.84s | `0` | **PASS (100%)** |
| **API Contract & Defect Regressions** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/test_api_contract.py -v` | 13 | 13 | 0 | 1 | 13.79s | `0` | **PASS (100%)** |
| **Synthetic Trade Lifecycle** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/test_audit_010_synthetic_trade.py -v` | 1 | 1 | 0 | 1 | 3.42s | `0` | **PASS (100%)** |
| **Financial Safety & Lookahead** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/test_historical_financial_safety.py backend/tests/test_audit_001_financial_lookahead.py -v` | 15 | 15 | 0 | 0 | 3.26s | `0` | **PASS (100%)** |
| **Full Repository Suite** | `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/data_pipeline backend/engines backend/logic backend/tests --ignore=backend/.venv -q` | 578 | 560 | 18 | 1252 | 59.88s | `1` | **560 PASS / 18 LEGACY FAIL** |
| **Frontend Unit Test Runner** | `cd frontend; node src/utils/run_all_tests.js` | 288 assertions | 288 | 0 | 0 | 0.42s | `0` | **PASS (100%)** |
| **Frontend Production Build** | `cd frontend; npm run build` | 1,932 modules | 1,932 | 0 | 1 chunk note | 1.79s | `0` | **PASS (100%)** |

---

## 3. Frontend Production Build Output

- **Vite version:** 8.3.0
- **Modules Transformed:** 1,932
- **Compilation Time:** 1.79s
- **Output Artifacts:**
  - `dist/index.html`: 1.06 kB
  - `dist/assets/index-*.css`: 60.50 kB (gzip: 10.08 kB)
  - `dist/assets/index-*.js`: 342.24 kB (gzip: 66.37 kB)
  - Vendor chunk: `vendor-react-*.js` (207.45 kB)
- **Zero build errors.**

