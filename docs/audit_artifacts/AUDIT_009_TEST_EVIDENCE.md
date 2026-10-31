# AUDIT-009: Test Evidence & Independent Execution Log

## 1. Backend Test Suite Verification

* **Command:** `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/data_pipeline backend/engines backend/logic backend/tests -q`
* **Exit Code:** `0` (Success)
* **Duration:** 89.28 seconds
* **Result:** **478 passed, 32 warnings** (100% pass rate)

### Breakdown by Subsystem & Directory:
1. `backend/tests/`: **67 unique tests**
   - `test_api_contract.py`: 10 passed
   - `test_audit_001_financial_lookahead.py`: 9 passed
   - `test_audit_002_backtest_metrics.py`: 11 passed
   - `test_audit_003_004_performance.py`: 7 passed
   - `test_audit_005_sequential_backtest.py`: 19 passed
   - `test_audit_006_independent_verification.py`: 5 passed
   - `test_historical_financial_safety.py`: 6 passed
2. `backend/data_pipeline/`: **193 unique tests** (ingestion, historical service, snapshot service, failure isolation, retry logic, persistence)
3. `backend/engines/`: **112 unique tests** (technical engine, indicators, financial scoring, sector RS, ranking, universe orchestrator)
4. `backend/logic/`: **106 unique tests** (valuation, growth, profitability, trade simulator, cost model, portfolio simulator, metrics)

*Total Unique Backend Tests:* **478 passed.**

---

## 2. Frontend Test Suite Verification

* **Command:** `node src/utils/run_all_tests.js`
* **Exit Code:** `0` (Success)
* **Duration:** 2.1 seconds
* **Result:** **288 assertions / tests passed across 7 suites** (100% pass rate)

### Breakdown by Frontend Suite:
1. `technicalIndicators.test.js`: 59 passed (EMA, RSI, MACD, ATR, edge case short history)
2. `screenerFilters.test.js`: 53 passed (strategy filters, price bounds, sorting, chip removal)
3. `watchlistStorage.test.js`: 49 passed (localStorage operations, error resilience)
4. `performanceHelpers.test.js`: 46 passed (equity curves, win rates, drawdown, profit factor)
5. `sectorHelpers.test.js`: 56 passed (relative strength, ranking, sector cards)
6. `dashboardRegressions.test.js`: 10 passed (issues A–G regression guards)
7. `api.test.js`: 18 passed (mock fixtures vs live guard validations)

*Total Unique Frontend Tests/Assertions:* **288 passed.**

---

## 3. Production Frontend Build Verification

* **Command:** `cd frontend; npm run build`
* **Exit Code:** `0` (Success)
* **Duration:** 2.08 seconds
* **Output:** Bundled 1,932 modules cleanly into `dist/` with valid code chunks.

---

## 4. Re-running Safeguards (AUDIT-005 & AUDIT-006)

* **Command:** `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/test_audit_005_sequential_backtest.py backend/tests/test_audit_006_independent_verification.py -v`
* **Exit Code:** `0` (Success)
* **Duration:** 17.65 seconds
* **Verified Test Cases:**
  - `test_01_whole_share_position_sizing`: PASSED
  - `test_02_indian_equity_cost_model_breakdown`: PASSED
  - `test_03_gross_vs_net_pnl_reconciliation`: PASSED
  - `test_04_single_open_position_per_symbol_no_overlap`: PASSED
  - `test_05_max_open_positions_cap_enforced`: PASSED
  - `test_06_insufficient_cash_prevents_entry`: PASSED
  - `test_07_opening_gap_down_and_gap_up_executions`: PASSED
  - `test_08_same_bar_collision_stop_loss_priority`: PASSED
  - `test_09_end_of_backtest_policy_mark_to_market_vs_force_close`: PASSED
  - `test_10_portfolio_cash_and_equity_reconciliation`: PASSED
  - `test_11_persistence_and_idempotent_duplicate_prevention`: PASSED
  - `test_12_legacy_score_only_records_excluded_and_preserved`: PASSED
  - `test_13_deterministic_sorting_on_opportunity_score`: PASSED
  - `test_14_exits_processed_before_entries_releases_cash`: PASSED
  - `test_15_api_post_backtest_portfolio_schema`: PASSED
  - `test_16_api_get_backtest_runs_includes_portfolio`: PASSED
  - `test_17_api_get_backtest_equity_curve`: PASSED
  - `test_18_audit_001_through_004_safeguards_preserved`: PASSED
  - `test_19_end_to_end_sequential_portfolio_simulation`: PASSED
  - `test_01_same_day_stop_loss_exit`: PASSED
  - `test_02_same_day_target_reached_exit`: PASSED
  - `test_03_multi_run_persistence_isolation`: PASSED
  - `test_04_cost_model_hand_calculations`: PASSED
  - `test_05_phase_5_controlled_synthetic_portfolio_simulation`: PASSED

