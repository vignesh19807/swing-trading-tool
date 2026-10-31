# AUDIT-018: Baseline Environment & Database Fingerprint

**Audit Execution Date:** 2026-10-29  
**Branch:** `main`  
**Commit Hash:** `77d8aff28c7966033581cea0add2c603c352b22a`  
**Auditor:** Independent Verification Engineer  

---

## 1. Git Repository State

- **Branch:** `main`
- **Head Commit:** `77d8aff28c7966033581cea0add2c603c352b22a`
- **Working Tree Cleanliness:** Dirty (Uncommitted changes present from preceding audits and user workspace modifications).
- **Preservation Policy:** All pre-existing modifications and untracked audit artifacts are strictly preserved without resetting or discarding.

### Tracked Modified Files (31 files)
- `backend/app.py`
- `backend/data_pipeline/backtest_result_service.py`
- `backend/data_pipeline/financial_service.py`
- `backend/data_pipeline/test_backup_recovery.py`
- `backend/data_pipeline/test_financial_score_persistence.py`
- `backend/data_pipeline/test_opportunity_score_persistence.py`
- `backend/data_pipeline/test_stock_snapshot_service.py`
- `backend/engines/financial_engine.py`
- `backend/engines/test_decision_engine.py`
- `backend/engines/test_financial_engine.py`
- `backend/engines/test_universe_orchestrator.py`
- `backend/engines/universe_orchestrator.py`
- `backend/logic/backtest_engine.py`
- `backend/logic/backtest_metrics.py`
- `backend/logic/backtest_specification.py`
- `backend/logic/debt_equity_analyzer.py`
- `backend/logic/growth_analyzer.py`
- `backend/logic/profit_margin_analyzer.py`
- `backend/logic/roce_analyzer.py`
- `backend/logic/roe_analyzer.py`
- `backend/logic/stock_context_analyzer.py`
- `backend/logic/test_end_to_end_integration.py`
- `backend/logic/test_growth_analyzer.py`
- `backend/logic/test_stock_intelligence.py`
- `backend/logic/test_tradingview_validation.py`
- `backend/logic/test_valuation_analyzer.py`
- `backend/logic/test_volatility_analyzer.py`
- `backend/logic/trade_simulator.py`
- `backend/logic/valuation_analyzer.py`
- `backend/tests/test_api_contract.py`
- `frontend/src/pages/StockExplorer.jsx`

---

## 2. Production Database Fingerprint

- **Path:** `c:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool\database\swing_trading.db`
- **SHA-256 Checksum (pre-audit):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Backup Created & Verified:** `database/swing_trading.db.bak_audit_018`
  - Backup SHA-256: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Exact Match)

### Database Table Inventory & Row Counts
| Table Name | Row Count | Purpose |
| :--- | :--- | :--- |
| `companies` | 52 | Active stock universe master |
| `daily_prices` | 25,746 | Historical daily OHLCV bars |
| `technical_indicators` | 25,746 | Pre-calculated technical indicators |
| `quarterly_results` | 260 | Quarterly financial statements (5 quarters x 52 stocks) |
| `sectors` | 17 | Macro sector classifications |
| `industries` | 45 | Granular industry classifications |
| `backtest_runs` | 2 | Historical backtest run metadata |
| `backtest_trades` | 1 | Historical backtest executed trade ledger |
| `backtest_equity_curve` | 125 | Daily portfolio equity mark-to-market snapshots |
| `backtest_results` | 2 | Legacy backtest score results |
| `financial_scores` | 0 | Dynamic cache table |
| `opportunity_scores` | 0 | Dynamic cache table |
| `signals` | 0 | Dynamic cache table |
| `sqlite_sequence` | 11 | Internal SQLite autoincrement sequence |

- **Stock Universe Count:** 52 companies
- **Daily Price History Span:** `2024-10-23` to `2026-10-23` (25,746 rows across 500 trading days)
- **Financial Publication Date Status:** 260 / 260 rows have `publication_date IS NULL` (100.0% missing regulatory filing dates, requiring the documented 45-day post-quarter empirical lag fallback).

---

## 3. Audit Artifact & Database Isolation Tracking

- **AUDIT-017 Temporary Database:**
  - Path: `docs/audit_artifacts/temp_pilot_audit_017.db`
  - SHA-256: `BFEB78DAAB516DBED9E7F2A2C5547CAF889D32531CC6A4C4D63EC9075A4F9A52`
  - Preserved intact; not modified or overwritten.
- **AUDIT-018 Isolated Temporary Database:**
  - Path: `docs/audit_artifacts/temp_pilot_audit_018.db`
  - Initial SHA-256: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
  - All reproduction simulations and database writes for AUDIT-018 will target this isolated copy exclusively.

