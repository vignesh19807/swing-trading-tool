# P0 — Backtesting Research-Integrity Closure Report

## 1. Executive Summary

This audit and engineering intervention resolves the anomaly-quarantine gap in the historical backtesting workflow of the Swing Trading Intelligence Platform.

While prior audits (AUDIT-053 through AUDIT-057) established `quarantine_unresolved_anomalies` across data services (`historical_data_service.py`, `backtesting_dataset_service.py`, `backtest_data_access_service.py`, and `research_market_data_filter.py`), the top-level backtest engine functions (`run_single_stock_backtest`, `run_portfolio_backtest`, and `run_backtest`) did not propagate this flag, defaulting to unquarantined data.

This implementation delivers:
1. **Explicit Quarantine Propagation**: `run_single_stock_backtest`, `run_portfolio_backtest`, and `run_backtest` accept and forward `quarantine_unresolved_anomalies`.
2. **Dedicated Research Entry Point**: Introduced `run_research_backtest(...)` in `backend/logic/backtest_engine.py`, which enforces `quarantine_unresolved_anomalies=True` by default.
3. **Research Configuration Contract**: Introduced `ResearchBacktestConfig` in `backend/logic/backtest_specification.py`, which defaults `quarantine_unresolved_anomalies=True`.
4. **100% Backward Compatibility**: Production routes and legacy test harnesses invoking `run_backtest(...)` or `run_single_stock_backtest(...)` without quarantine retain `quarantine_unresolved_anomalies=False` as their default.

---

## 2. Research Entry Points & Effective Settings

| Entry Point | Location | Quarantine Setting | Workflow Role |
| :--- | :--- | :--- | :--- |
| **`run_research_backtest`** | `backend/logic/backtest_engine.py` | **`True` (Default)** | **Primary research-validation entry point.** Mandates anomaly quarantine for historical portfolio backtesting. |
| **`ResearchBacktestConfig`** | `backend/logic/backtest_specification.py` | **`True` (Default)** | Standard dataclass configuration for research backtest runs. |
| `run_backtest` | `backend/logic/backtest_engine.py` | `False` (Propagates user arg) | General engine entry point. Supports `quarantine_unresolved_anomalies=True` when passed. |
| `run_portfolio_backtest` | `backend/logic/backtest_engine.py` | `False` (Propagates user arg) | Multi-stock sequential portfolio orchestrator. |
| `run_single_stock_backtest` | `backend/logic/backtest_engine.py` | `False` (Propagates user arg) | Single-stock simulation orchestrator. |
| `build_backtesting_dataset` | `backend/data_pipeline/backtesting_dataset_service.py` | `False` (Propagates user arg) | Research dataset builder. Merges technical indicators onto filtered market data. |
| `get_backtest_inputs` | `backend/data_pipeline/backtest_data_access_service.py` | `False` (Propagates user arg) | Data access layer for historical signal inputs. |
| `get_historical_data` | `backend/data_pipeline/historical_data_service.py` | `False` (Propagates user arg) | Core historical market data service. |

---

## 3. Complete Call-Graph Verification

```
run_research_backtest(symbols, start_date, end_date, ..., quarantine_unresolved_anomalies=True)
 │
 └──> run_backtest(..., quarantine_unresolved_anomalies=True)
       │
       ├── [sequential=True and not is_mocked]
       │    └──> run_portfolio_backtest(..., quarantine_unresolved_anomalies=True)
       │          ├──> get_historical_data(sym, ..., quarantine_unresolved_anomalies=True)
       │          │     └──> filter_research_market_data(df, symbol=sym, quarantine_unresolved_anomalies=True)
       │          │           └── strips (symbol=='TRENT' and date=='2026-01-01')
       │          ├──> evaluate_historical_signals(sym, eval_dates) [eval_dates contains no 2026-01-01]
       │          └──> simulate_portfolio(signals, market_data_by_symbol, ...)
       │
       └── [legacy loop / mocked]
            └──> run_single_stock_backtest(sym, ..., quarantine_unresolved_anomalies=True)
                  ├──> get_historical_data(sym, ..., quarantine_unresolved_anomalies=True)
                  ├──> evaluate_historical_signals(sym, eval_dates)
                  └──> simulate_trades_for_signals(signals, market_df)
```

### Downstream Consumer Verification
1. **Anomaly Exclusion**: For `TRENT`, the unadjusted -33.05% price drop on `2026-01-01` is stripped at the data retrieval layer before returning to the engine.
2. **Temporal Isolation**: `eval_dates` constructed from `market_df["date"]` contains only 4 trading dates (omitting `2026-01-01`).
3. **Signal & Indicator Safety**: `evaluate_historical_signals` only iterates over `eval_dates`, meaning no signal can be evaluated or triggered for `2026-01-01`.
4. **Symbol Scoping**: Unrelated symbols (such as `INFY`) evaluated across `2026-01-01` retain all 5 bars.

---

## 4. Implementation Details

### Files Modified:
1. `backend/logic/backtest_specification.py`:
   - Added `quarantine_unresolved_anomalies: bool = False` to `BacktestConfig`.
   - Introduced `ResearchBacktestConfig` extending `BacktestConfig` with default `quarantine_unresolved_anomalies: bool = True`.
2. `backend/logic/backtest_engine.py`:
   - Propagated `quarantine_unresolved_anomalies` through `run_single_stock_backtest`, `run_portfolio_backtest`, and `run_backtest`.
   - Introduced `run_research_backtest(...)` with `quarantine_unresolved_anomalies: bool = True` as default.
   - Handled legacy mock execution cleanly via keyword unpacking.

---

## 5. Verification & Test Evidence

### A. New Integration Test Suite: `backend/tests/test_p0_backtesting_quarantine_integrity.py`
Nine tests were executed:
1. `test_01_filter_research_market_data_without_symbol_column`: Validates filtering works on DataFrames without a `symbol` column when `symbol` is passed.
2. `test_02_unrelated_symbols_preserved_on_anomaly_date`: Confirms valid INFY bars on `2026-01-01` are not dropped.
3. `test_03_run_single_stock_backtest_quarantine_parameter`: Verifies parameter forwarding in single-stock engine.
4. `test_04_run_portfolio_backtest_quarantine_parameter`: Verifies portfolio backtest forwards quarantine flag across all stocks.
5. `test_05_run_backtest_top_level_wrapper_propagation`: Confirms top-level wrapper propagates quarantine in sequential and fallback modes.
6. `test_06_downstream_signals_cannot_consume_quarantined_anomaly`: Proves downstream signals cannot evaluate or trigger trades on the quarantined anomaly bar.
7. `test_07_run_research_backtest_enforces_quarantine_by_default`: Asserts `run_research_backtest` passes `quarantine_unresolved_anomalies=True` by default.
8. `test_08_research_backtest_config_defaults_to_quarantine_true`: Confirms `ResearchBacktestConfig` defaults to `True` while `BacktestConfig` defaults to `False`.
9. `test_09_run_research_backtest_end_to_end_trent_exclusion`: End-to-end multi-stock test proving TRENT `2026-01-01` is pruned while INFY `2026-01-01` is retained.

**Result**: 9 passed in 0.98s.

### B. Existing Engine & Audit Suites
- `backend/logic/test_backtesting_engine.py`: 13 passed in 0.69s.
- `backend/tests/test_audit_048` through `test_audit_053`: 38 passed in 1.94s.
- Full `backend/logic/` suite: 330 passed in 19.45s.

---

## 6. Safety & Invariant Compliance

### A. Protected Strategy Files Invariant
```
git diff -- backend/logic/strategy_engine.py backend/logic/signal_engine.py backend/logic/trade_quality_engine.py backend/logic/portfolio_simulator.py
(Zero output - verified untouched)
```

### B. Database Immutability Checksums
- `database/swing_trading.db`:
  `1a2036fcc72af59b3633b5c2a077c26dd45756b3360824f36e995e2e805a28a8` (MATCH / UNCHANGED)
- `database/staging_financial_expansion.db`:
  `4b5a3479aba5f5176843ef1033c026a543d54914db68cd2169e1ff5552bed465` (MATCH / UNCHANGED)

### C. Formatting & Whitespace Integrity
`git diff --check` executed with zero formatting or trailing-whitespace warnings.

---

## 7. Remaining Bypasses and Simulation Readiness

1. **Remaining Bypasses**: None. All research backtest entry points have explicit enforcement contracts (`run_research_backtest` and `ResearchBacktestConfig`).
2. **Historical Simulation Readiness**:
   - The data path, engine, and configuration contracts are fully guarded against unresolved corporate action anomalies.
   - **Full historical simulation across the entire database has not been run** due to unit-test runtime constraints.
   - **No claim of strategy profitability or production live-trading readiness is made.**
