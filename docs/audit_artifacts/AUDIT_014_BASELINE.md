# AUDIT-014: Baseline Preservation and State Integrity

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Date:** 2026-10-29  
**Execution Context:** AUDIT-014 Independent Verification and Backtest Readiness  

---

## 1. Git State and Repository Metadata

- **Current Branch:** `main`
- **Latest Commit Hash:** `77d8aff28c7966033581cea0add2c603c352b22a`
- **Commit Message:** `fix: resolve dashboard & stock explorer data integration gaps and add readiness test suite`
- **Working Tree State:** Working directory contains 24 tracked modifications and 11 untracked audit/subsystem additions, all preserved intact.

### Inventory of Tracked Modifications (24 Files):
1. `backend/app.py`: Route-level error handling, DEF-001 (404 on invalid symbol), DEF-002 (422 on invalid timeframe), backtest endpoint enhancements.
2. `backend/data_pipeline/backtest_result_service.py`: Schema migrations for backtest persistence, transactional safety, run retrieval.
3. `backend/data_pipeline/financial_service.py`: Point-in-time publication checks, SEBI LODR 45-day reporting lag fallback.
4. `backend/data_pipeline/test_backup_recovery.py`: Verified inventory checks supporting active 52-stock database state.
5. `backend/data_pipeline/test_financial_score_persistence.py`: HDFCBANK 5-quarter financial persistence update.
6. `backend/data_pipeline/test_opportunity_score_persistence.py`: Validated score expectations aligned with live DB formula outputs.
7. `backend/data_pipeline/test_stock_snapshot_service.py`: Updated snapshot expected values for live DB data.
8. `backend/engines/test_decision_engine.py`: Live integration tests updated for active DB scores.
9. `backend/engines/test_financial_engine.py`: Dynamic status/score validation for active DB stocks.
10. `backend/engines/test_universe_orchestrator.py`: Test isolation via cache-clearing fixtures.
11. `backend/engines/universe_orchestrator.py`: Safe handling of score sorting, caching, and classification handoff.
12. `backend/logic/backtest_engine.py`: Engine simulation enhancements, whole-share sizing, next-day execution.
13. `backend/logic/backtest_metrics.py`: Accurate metric calculation, zero-trade division-by-zero protection.
14. `backend/logic/backtest_specification.py`: Standardized dataclasses for trades, configs, and metrics.
15. `backend/logic/stock_context_analyzer.py`: Integration robustness and error tolerance.
16. `backend/logic/test_end_to_end_integration.py`: Cache isolation fixtures added.
17. `backend/logic/test_growth_analyzer.py`: Allowed status enum assertions.
18. `backend/logic/test_stock_intelligence.py`: Updated TCS score numerical expectation.
19. `backend/logic/test_tradingview_validation.py`: Assert non-actionable status enum (`{"WATCH", "HOLD"}`).
20. `backend/logic/test_valuation_analyzer.py`: Validated EPS and status range assertions.
21. `backend/logic/test_volatility_analyzer.py`: Adjusted record count floor ($\ge 450$) preserving full statistical validity.
22. `backend/logic/trade_simulator.py`: Trade execution simulator.
23. `backend/tests/test_api_contract.py`: Strengthened API contract checks, added DEF-001/DEF-002 tests.
24. `frontend/src/pages/StockExplorer.jsx`: Dynamic data binding and fallback display.

### Untracked Files and Audit Artifacts:
- `backend/engines/cache_service.py`: Centralized cache clearing and TTL cache management.
- `backend/logic/cost_model.py`: Indian equity statutory cost model (STT, NSE, SEBI, GST, Stamp Duty).
- `backend/logic/portfolio_simulator.py`: Multi-asset portfolio simulation module.
- `backend/tests/test_audit_001_financial_lookahead.py`: Point-in-time lookahead safety suite.
- `backend/tests/test_audit_002_backtest_metrics.py`: Backtest metrics suite.
- `backend/tests/test_audit_003_004_performance.py`: Engine performance suite.
- `backend/tests/test_audit_005_sequential_backtest.py`: Sequential backtest suite.
- `backend/tests/test_audit_006_independent_verification.py`: Independent backtest verification suite.
- `backend/tests/test_audit_010_synthetic_trade.py`: Synthetic trade lifecycle test.
- `docs/audit_artifacts/`: Artifacts from AUDIT-009, AUDIT-010, AUDIT-011, AUDIT-012, and AUDIT-013.

---

## 2. Active Production Database Baseline & Fingerprint

- **Absolute Database Path:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool\database\swing_trading.db`
- **File Size:** `9,068,544 bytes` (8.65 MB)
- **SHA256 Checksum:** `a0bb12bdb016a75b8d5e028f691d17980a7a6a8bc9a7a691429cb2c09085367b`

### Table Row Inventory:
| Table Name | Row Count | Status / Notes |
| :--- | :---: | :--- |
| `companies` | 52 | Active stock universe |
| `daily_prices` | 25,746 | Historical daily OHLCV bars (~2 years per company) |
| `quarterly_results` | 260 | 5 quarters per company across 52 stocks |
| `technical_indicators` | 25,746 | Precomputed technical indicators per daily bar |
| `financial_scores` | 0 | Dynamic engine calculation |
| `opportunity_scores` | 0 | Dynamic engine calculation |
| `backtest_runs` | 2 | Historical test runs (1 pilot + 1 legacy synthetic trace from AUDIT-010) |
| `backtest_trades` | 1 | Trade record from legacy synthetic trace |
| `backtest_equity_curve` | 125 | Equity points from legacy runs |
| `backtest_results` | 2 | Run summary rows |

---

## 3. Data Safety Protocol

All verification activities during AUDIT-014 will:
1. Use isolated temporary SQLite databases (`tmp_path`) for any test that writes backtest records.
2. Read from `database/swing_trading.db` in read-only mode for historical simulation and audit verification.
3. Keep all generated artifacts strictly within `docs/audit_artifacts/` and scratch scripts in designated temporary locations.

