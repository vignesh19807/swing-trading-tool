# Test Coverage Matrix: Swing Trading Intelligence Platform

## 1. Frontend Pages & Routes

| Route / Page | File | Test Type | Coverage Details | Result |
|---|---|---|---|---|
| `/` (Dashboard) | `src/pages/Dashboard.jsx` | Unit / Regressions / API | Tested via `dashboardRegressions.test.js`, API service contracts, and live probe | **PASS** |
| `/opportunities` | `src/pages/Opportunities.jsx` | Unit / API | Tested via `api.test.js`, `screenerFilters.test.js`, and live `/api/opportunities` | **PASS** |
| `/stocks` (Explorer) | `src/pages/StockExplorer.jsx` | Unit / Build / Probe | Tested via screener filter tests, build checks, and `/api/stocks` verification | **PASS** |
| `/stocks/:symbol` | `src/pages/StockDetail.jsx` | Unit / Technical | Tested via `technicalIndicators.test.js`, chart tests, and `/api/stocks/{symbol}` probe | **PASS** |
| `/sectors` | `src/pages/SectorExplorer.jsx` | Unit / Helpers | Tested via `sectorHelpers.test.js` (56/56 passing) and `/api/sectors` endpoint | **PASS** |
| `/performance` | `src/pages/Performance.jsx` | Unit / Performance | Tested via `performanceHelpers.test.js` (54/54 passing) and `/api/backtests/latest` | **PASS** |
| `/watchlist` | `src/pages/Watchlist.jsx` | Unit / LocalStorage | Tested via `watchlistStorage.test.js` (18/18 passing) | **PASS** |
| `*` (NotFound) | `src/pages/NotFound.jsx` | Static / Build | Tested via production build & route table | **PASS** |

---

## 2. Backend REST API Endpoints

| Endpoint | Method | Expected Status | Measured Latency | Validation & Edge Case Check | Result |
|---|---|---|---|---|---|
| `/healthz/live` | GET | 200 | ~255 ms | Liveness probe immediate response | **PASS** |
| `/healthz/ready` | GET | 200 | ~21 ms | Verifies database pool and company universe count (52) | **PASS** |
| `/api/data-health` | GET | 200 | ~55 ms | Returns decomposed health factor statuses | **PASS** |
| `/api/market/indices` | GET | 200 | ~99 ms | Returns broad market benchmark levels | **PASS** |
| `/api/sectors` | GET | 200 | ~988 ms | Computes dynamic sector rankings across universe | **PASS** |
| `/api/stocks` | GET | 200 | ~171 ms | Returns all 52 supported stock symbols & metadata | **PASS** |
| `/api/stocks/{symbol}` | GET | 200 / 404 | ~187 ms | Returns comprehensive stock intelligence payload | **PASS WITH LIMITATIONS** (DEF-001: returns INSUFFICIENT dict on unknown symbol) |
| `/api/stocks/{symbol}/history` | GET | 200 | ~16 ms | Returns OHLCV candles (supports 1M, 3M, 6M, 1Y, ALL) | **PASS WITH LIMITATIONS** (DEF-002: unvalidated timeframe parameter) |
| `/api/opportunities` | GET | 200 | ~717 ms | Ranks top swing trading candidates | **PASS** |
| `/api/backtests/latest` | GET | 200 | ~8 ms | Returns latest persisted portfolio backtest run & equity curve | **PASS** |

---

## 3. Core Business & Trading Engines

| Component / Subsystem | Directory | Automated Test Suite | Test Count | Result |
|---|---|---|---|---|
| **Technical Analysis Engine** | `backend/engines/` | `test_technical_engine.py`, `test_rsi_integration.py`, `test_macd_integration.py`, `test_ema_integration.py`, `test_atr_integration.py` | 58 | **PASS** |
| **Financial Health Engine** | `backend/engines/` | `test_financial_engine.py`, `test_annual_financial_engine_integration.py` | 24 | **PASS** |
| **Sector & Industry Engine** | `backend/engines/` | `test_sector_industry_engine_integration.py` | 18 | **PASS** |
| **Ranking & Decision Engine** | `backend/engines/` | `test_decision_engine.py`, `test_ranking_engine.py`, `test_universe_orchestrator.py` | 42 | **PASS** |
| **Signal Engine & Risk Gate** | `backend/logic/` | `test_signal_engine.py`, `test_signal_integration.py`, `test_trade_quality_engine.py` | 64 | **PASS** |
| **Trade Simulator & Costs** | `backend/logic/` | `test_trade_simulator.py`, `test_audit_005_sequential_backtest.py`, `test_audit_006_independent_verification.py` | 38 | **PASS** |
| **Portfolio Simulator & Accounting** | `backend/logic/` | `test_audit_005_sequential_backtest.py`, `test_audit_006_independent_verification.py` | 24 | **PASS** |
| **Historical Data Pipelines** | `backend/data_pipeline/` | `test_historical_data_service.py`, `test_data_handoff.py`, `test_backtesting_dataset_service.py` | 92 | **PASS** |
| **Backtest Result Persistence** | `backend/data_pipeline/` | `test_backtest_result_service.py`, `test_backtest_data_access_service.py` | 46 | **PASS** |
| **Explanations & Context** | `backend/logic/explanation/` | `test_financial_explanation.py`, `test_opportunity_explanation.py`, `test_technical_explanation.py` | 36 | **PASS** |
| **Audit Test Suites (001–006)** | `backend/tests/` | `test_audit_001` through `test_audit_006` | 51 | **PASS** |

