# AUDIT-016: Baseline Verification

**Audit Phase:** Phase 1 — Baseline Verification & Environment Preservation  
**Execution Timestamp:** 2026-10-29T21:05:30+05:30  
**Environment:** Windows PowerShell, Python 3.12.9 (.venv), Node.js v20.18.0  

---

## 1. Version Control Baseline

* **Current Branch:** `main`
* **Current Revision (HEAD):** `77d8aff28c7966033581cea0add2c603c352b22a`
* **Working Tree State:** All existing tracked and untracked modifications from previous audits (AUDIT-009 through AUDIT-015) are strictly preserved.
* **Modified Tracked Files (24 files):**
  - `backend/app.py`
  - `backend/data_pipeline/backtest_result_service.py`
  - `backend/data_pipeline/financial_service.py`
  - `backend/data_pipeline/test_backup_recovery.py`
  - `backend/data_pipeline/test_financial_score_persistence.py`
  - `backend/data_pipeline/test_opportunity_score_persistence.py`
  - `backend/data_pipeline/test_stock_snapshot_service.py`
  - `backend/engines/test_decision_engine.py`
  - `backend/engines/test_financial_engine.py`
  - `backend/engines/test_universe_orchestrator.py`
  - `backend/engines/universe_orchestrator.py`
  - `backend/logic/backtest_engine.py`
  - `backend/logic/backtest_metrics.py`
  - `backend/logic/backtest_specification.py`
  - `backend/logic/stock_context_analyzer.py`
  - `backend/logic/test_end_to_end_integration.py`
  - `backend/logic/test_growth_analyzer.py`
  - `backend/logic/test_stock_intelligence.py`
  - `backend/logic/test_tradingview_validation.py`
  - `backend/logic/test_valuation_analyzer.py`
  - `backend/logic/test_volatility_analyzer.py`
  - `backend/logic/trade_simulator.py`
  - `backend/tests/test_api_contract.py`
  - `frontend/src/pages/StockExplorer.jsx`
* **AUDIT-015 Artifacts Preserved:**
  - `docs/audit_artifacts/AUDIT_015_BASELINE.md`
  - `docs/audit_artifacts/AUDIT_015_POINT_IN_TIME_REVIEW.md`
  - `docs/audit_artifacts/AUDIT_015_PILOT_SPECIFICATION.md`
  - `docs/audit_artifacts/AUDIT_015_PILOT_EXECUTION.md`
  - `docs/audit_artifacts/AUDIT_015_PILOT_RESULTS.md`
  - `docs/audit_artifacts/AUDIT_015_REGRESSION_RESULTS.md`
  - `docs/audit_artifacts/AUDIT_015_FINAL_ACCEPTANCE.md`
  - `docs/audit_artifacts/temp_pilot_audit_015.db`

---

## 2. Production Database Baseline

* **Database File Path:** `database/swing_trading.db`
* **File Size:** 9,068,544 bytes
* **SHA256 Checksum:** `10F40129FC710F7E49AB82D285A45F94591D19EF2ED05A74F071FB86EFE92AD2`
* **Backup Created:** `database/swing_trading.db.bak_audit_016`
* **Backup SHA256 Checksum:** `10F40129FC710F7E49AB82D285A45F94591D19EF2ED05A74F071FB86EFE92AD2` (Verified 100% identical)

### Database Table Inventory
| Table Name | Row Count | Purpose |
| :--- | :--- | :--- |
| `companies` | 52 | Active Nifty company master records |
| `daily_prices` | 25,746 | Historical EOD daily prices (OHLCV) |
| `quarterly_results` | 260 | Quarterly financial statements (5 quarters $\times$ 52 stocks) |
| `technical_indicators` | 25,746 | Computed indicators (ATR, EMA, RSI, Support/Resistance) |
| `sectors` | 17 | Sector taxonomy |
| `industries` | 45 | Industry classification |
| `backtest_runs` | 2 | Historical test runs (baseline) |
| `backtest_results` | 2 | Per-run benchmark results |
| `backtest_trades` | 1 | Baseline recorded trade |
| `backtest_equity_curve` | 125 | Baseline equity curve records |
| `financial_scores` | 0 | Cache table |
| `opportunity_scores` | 0 | Cache table |
| `signals` | 0 | Active signal storage |
| `sqlite_sequence` | 11 | Autoincrement metadata |

---

## 3. Operational Guarantees

1. The production database is marked read-only for this audit and will be protected by SHA256 integrity verifications.
2. All experimental runs, test suite additions, and pilot executions must utilize isolated temporary databases.
3. Pre-existing code modifications and audit artifacts will not be reverted or discarded.

