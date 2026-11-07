# PHASE 4 — INITIAL ARCHITECTURE AUDIT: DYNAMIC STOCK UNIVERSE MANAGEMENT
**Swing Trading Intelligence Platform**  
**Audit Date:** March 2026 / Turn Baseline  
**Auditor:** Senior DevOps Engineer, Cloud Architect, Backend Engineer & Database Infrastructure Specialist  
**Classification:** Phase 4 Pre-Implementation Architecture Audit  

---

## EXECUTIVE SUMMARY

Phase 4 transforms the Swing Trading Intelligence Platform from a partially hardcoded, static stock-universe architecture into a database-driven, scalable, and reliable universe management architecture.

Currently, the stock universe definition is fractured:
1. **Static Python Code**: `backend/data_pipeline/stock_universe.py` defines a hardcoded 100-stock list (`STOCK_UNIVERSE`), which is directly imported by 11 ingestion and reporting scripts.
2. **Local Production Database**: `database/swing_trading.db` (`companies` table) contains exactly 52 active companies (Nifty 50 constituents + `TMPV` and `ETERNAL`).
3. **Frontend Presentation**: `Dashboard.jsx` hardcodes fallback counts (`52`) and displays static labels (`NIFTY 50 Universe`), while `api.getStocks()` requests `/api/stocks` without pagination parameters, defaulting to a 50-item limit.

This audit establishes the empirical baseline, identifies every location where static universe dependencies exist, documents architectural limitations across the backend, database, and frontend, assesses operational risks, and proposes a phased implementation architecture.

**Baseline Production Database Checksum (Verified):**
`1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`

---

## 1. CURRENT STOCK-UNIVERSE ARCHITECTURE

The stock universe is currently accessed through two divergent architectural pathways:

```
+-----------------------------------------------------------------------------------------------+
|                             CURRENT DIVERGENT UNIVERSE PATHWAYS                               |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|   PATHWAY A: Ingestion & Maintenance Pipelines (HARDCODED)                                    |
|   --------------------------------------------------------                                    |
|   backend/data_pipeline/stock_universe.py                                                     |
|         │                                                                                     |
|         ├─► load_stock_data.py          (Imports STOCK_UNIVERSE; loops 100 stocks)            |
|         ├─► load_financial_data.py      (Imports STOCK_UNIVERSE; loops 100 stocks)            |
|         ├─► run_daily_update.py         (Imports STOCK_UNIVERSE; daily orchestrator)          |
|         ├─► run_technical_pipeline.py   (Imports STOCK_UNIVERSE; indicator calculation)       |
|         └─► Quality & Audit Scripts     (verify_financial_data, sector_industry_audit, etc.)  |
|                                                                                               |
|   PATHWAY B: Analytics, Decision Engine & API Serving (DATABASE-DRIVEN)                       |
|   ---------------------------------------------------------------------                       |
|   database/swing_trading.db (companies table: 52 stocks)                                      |
|         │                                                                                     |
|         ├─► classification_service.py (get_all_classifications() -> SELECT * FROM companies)  |
|         ├─► universe_orchestrator.py  (rank_universe() -> calls get_all_classifications())    |
|         ├─► app.py                    (GET /api/stocks -> calls get_all_classifications())    |
|         └─► app.py                    (GET /api/data-health -> SELECT COUNT(*) FROM companies)|
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
```

### Architectural Conflict
- Ingestion pipelines operate on the 100-stock `STOCK_UNIVERSE` Python array.
- The serving APIs, decision engine, and opportunities ranking operate on the 52 companies present in the SQLite database.
- Adding a stock currently requires:
  1. Manually adding the stock dictionary to `backend/data_pipeline/stock_universe.py`.
  2. Running `load_stock_data.py` to insert the company row into the database and download market data.
  3. Running `run_technical_pipeline.py` to compute indicators.
  4. Updating frontend static references if hardcoded counts are used.

---

## 2. EXISTING DATABASE SCHEMA AUDIT

Inspection of `database/swing_trading.db` revealed the following table definitions and constraints:

### A. Table: `companies` (Primary Universe Registry)
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    company_name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    exchange TEXT,
    sector_id INTEGER,
    industry_id INTEGER,
    FOREIGN KEY (sector_id) REFERENCES sectors(id),
    FOREIGN KEY (industry_id) REFERENCES industries(id)
);
```
- **Strengths**: Symbol uniqueness is enforced (`symbol TEXT UNIQUE NOT NULL`). Relational links to `sectors` and `industries` exist.
- **Architectural Gaps for Dynamic Management**:
  - No `is_active` flag (cannot deactivate or delist a stock without deleting rows).
  - No `status` lifecycle indicator (`PENDING`, `ACTIVE`, `INACTIVE`, `QUARANTINED`).
  - No `created_at` or `updated_at` audit timestamps.
  - No `source` or `provenance` metadata recording who or what registered the symbol.
  - No `listing_date` or security classification metadata.

### B. Table: `daily_prices` (Market Data Store)
```sql
CREATE TABLE daily_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    adjusted_close REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, date)
);
```
- **Strengths**: Strict composite unique constraint `UNIQUE(company_id, date)` prevents duplicate market bars.

### C. Table: `technical_indicators` (Indicator Store)
```sql
CREATE TABLE technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    rsi REAL,
    macd REAL,
    macd_signal REAL,
    ema_20 REAL,
    ema_50 REAL,
    ema_200 REAL,
    macd_histogram REAL,
    atr_14 REAL,
    technical_score REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, date)
);
```
- **Strengths**: Precomputed indicator store linked by foreign key.

### D. Table: `quarterly_results` (Financial Fundamentals)
```sql
CREATE TABLE quarterly_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    quarter TEXT NOT NULL,
    revenue REAL,
    net_profit REAL,
    eps REAL,
    roe REAL,
    roce REAL,
    debt_equity REAL,
    operating_margin REAL,
    net_margin REAL,
    publication_date TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);
```

### E. Existing Indexes
- `idx_daily_prices_company_date` on `daily_prices(company_id, date)`
- `idx_technical_indicators_company_date` on `technical_indicators(company_id, date)`
- `idx_quarterly_results_company_quarter` on `quarterly_results(company_id, quarter)`

---

## 3. HARDCODED STOCK REFERENCES INVENTORY

The audit scanned the complete codebase for hardcoded universe definitions and static counts:

| Location / File | Hardcoded Component | Architectural Impact |
| :--- | :--- | :--- |
| `backend/data_pipeline/stock_universe.py` | `STOCK_UNIVERSE = [...]` (100 stock dicts) | Static central list. Requires code edit to add/remove stocks. |
| `backend/data_pipeline/load_stock_data.py` | Imports `STOCK_UNIVERSE`; loops over list | Market data ingestion cannot onboard stocks dynamically. |
| `backend/data_pipeline/load_financial_data.py`| Imports `STOCK_UNIVERSE` | Financial ingestion tied to static list. |
| `backend/data_pipeline/run_daily_update.py` | Imports `STOCK_UNIVERSE` | Daily refresh runner loops over static array. |
| `backend/data_pipeline/run_technical_pipeline.py`| Imports `STOCK_UNIVERSE` | Indicator recalculation loops over static array. |
| `backend/data_pipeline/sector_industry_audit.py`| Imports `STOCK_UNIVERSE` | Sector validation checks against static list. |
| `backend/data_pipeline/sector_industry_quality_report.py`| Imports `STOCK_UNIVERSE` | Quality report metrics bound to static list. |
| `backend/data_pipeline/financial_quality_report.py`| Imports `STOCK_UNIVERSE` | Fundamental report metrics bound to static list. |
| `backend/data_pipeline/validate_all.py` | Imports `STOCK_UNIVERSE` | Validation script asserts static list completeness. |
| `backend/data_pipeline/verify_financial_data.py`| Imports `STOCK_UNIVERSE` | Verification checks against static list. |
| `backend/tests/test_audit_041_historical_data_readiness.py` | Asserts exactly 52 companies and 5 quarters | Historical governance assertion (protected test). |
| `backend/tests/test_database_configuration.py` | `assert len(df) == 52`, `companies_count >= 50` | Unit test assertions on existing dataset. |
| `frontend/src/pages/Dashboard.jsx` | `universeCount = ... || 52`, `NIFTY 50 Universe` | Hardcoded UI labels and fallback count. |
| `frontend/src/data/mockStocks.js` | 10 static mock stocks | Mock mode fixtures. |

---

## 4. EXISTING INGESTION ARCHITECTURE & DEFICIENCIES

1. **Synchronous, Sequential Processing**:
   - `load_stock_data.py` runs a single synchronous `for stock in STOCK_UNIVERSE` loop.
   - For 52 stocks, ingestion requires ~45 seconds.
   - For 300 stocks, sequential execution without batching or connection pooling risks hitting provider timeouts or Yahoo Finance rate limits (HTTP 429).
2. **Missing Ingestion State Tracking**:
   - There is no table or mechanism recording whether a stock's market data is `PENDING`, `COLLECTING`, `MARKET_DATA_READY`, or `FAILED`.
   - Ingestion success is only inferred by checking whether rows exist in `daily_prices`.
3. **Absence of Onboarding Isolation**:
   - There is no dedicated single-stock onboarding entry point. To onboard a single new stock, operators currently have to invoke the full-universe ingestion script.

---

## 5. EXISTING API LIMITATIONS

1. **In-Memory Filtering & Pagination in `/api/stocks`**:
   - `get_stocks` in `backend/app.py` reads the entire `companies` table into a Pandas DataFrame in Python, applies Python list comprehensions for search and sector filtering, and slices in memory.
   - While adequate for 52 stocks, for 300+ stocks this creates unnecessary CPU and memory allocation on every HTTP request.
2. **Missing Universe Management Endpoints**:
   - No REST endpoint exists to:
     - Add a company (`POST /api/universe/stocks`).
     - Activate or deactivate a company (`PATCH /api/universe/stocks/{symbol}`).
     - Inspect granular data coverage (`GET /api/universe/coverage`).
     - Check per-stock ingestion status (`GET /api/universe/status`).

---

## 6. FRONTEND LIMITATIONS

1. **Client-Side Slicing vs Server-Side Pagination**:
   - `frontend/src/services/api.js` defines `getStocks()` as `request("/api/stocks")` with no query parameters.
   - `backend/app.py` has default `limit=50`.
   - Consequently, when the database expands beyond 50 stocks, the frontend currently misses stocks beyond index 50 unless explicit pagination parameters are passed.
2. **Hardcoded Fallbacks**:
   - `Dashboard.jsx` falls back to `52` if `dataHealth` is loading or unavailable.
   - Label says "NIFTY 50 Universe", which becomes inaccurate as the universe expands to broader Indian equities (Nifty Next 50, Midcap 150).
3. **No Coverage Distinction in UI**:
   - The UI does not distinguish between a stock that is merely active in the universe vs one whose market data is ready vs one whose financial fundamentals are verified.

---

## 7. DATA-QUALITY AND GOVERNANCE LIMITATIONS

1. **The Market-Data vs Financial-Data Divide**:
   - Market data (OHLCV) can be fetched in minutes via Yahoo Finance.
   - Authentic financial data under P1/P2 governance requires quarterly filing verification, statutory 45-day lag enforcement, and OCR/exchange validation.
   - Newly added stocks will initially possess market data but **zero verified quarterly filings**.
2. **Decision Engine Invariance**:
   - The scoring engine (`backend/engines/financial_engine.py`) requires at least 2 valid fundamental sub-scores to generate an `overall_score`. If fewer than 2 exist, it returns `overall_score = None`.
   - The platform must maintain strict governance: a newly onboarded stock must NOT generate synthetic fundamentals, must NOT fabricate publication dates, and must NOT generate speculative BUY signals without verified data.

---

## 8. RISK ASSESSMENT & MITIGATION MATRIX

| Risk Factor | Severity | Probability | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **Production DB Mutation / Corruption** | **CRITICAL** | Medium | STRICT PROHIBITION: Never run migrations directly on `database/swing_trading.db`. All schema evolutions and batch expansions must execute in isolated test databases with pre- and post-checksum validation. |
| **Provider Rate Limiting (Yahoo Finance)** | **HIGH** | High | Implement controlled batch onboarding (e.g. 5 stocks, then 10 stocks), configurable inter-request rate limiting (0.5s–1.0s delay), and exponential backoff retry. |
| **Strategy & Signal Engine Drift** | **CRITICAL** | Low | Absolute freeze on protected logic files (`strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`). 0 modifications permitted. |
| **Regression in Historical Test Suites** | **HIGH** | Medium | Preserve the 52 original companies and their IDs. Use `@pytest.mark.requires_preseeded_db` for historical suites; ensure all 185 portable tests and 144 historical tests continue passing 100%. |
| **Spurious Signals for Newly Added Stocks** | **HIGH** | Medium | Cold-start gating: Newly onboarded stocks without verified technical history (>= 200 bars) and verified financials are classified as `INCOMPLETE_DATA` and excluded from trading signals. |

---

## 9. PROPOSED PHASE 4 IMPLEMENTATION ARCHITECTURE

Phase 4 will be implemented across seven structured, auditable subphases:

```
+-----------------------------------------------------------------------------------------------+
|                             PHASE 4 SUBPHASE ROADMAP                                          |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|   Phase 4.0: Architecture Audit (COMPLETE — This Document)                                    |
|              Audit existing codebase, database, schemas, and hardcoded dependencies.          |
|                                                                                               |
|   Phase 4.1: Database-Driven Stock Universe Service                                           |
|              - Safe backward-compatible migration for 'companies' (is_active, status, etc.)  |
|              - Create backend/data_pipeline/stock_universe_service.py                         |
|              - Refactor consumers to query DB-driven universe service.                        |
|                                                                                               |
|   Phase 4.2: Dynamic Stock Onboarding & Symbol Validation                                     |
|              - Implement symbol validator (NSE syntax, exchange verification).                |
|              - Implement add_stock(), activate_stock(), deactivate_stock().                   |
|              - Maintain audit logging for universe membership changes.                        |
|                                                                                               |
|   Phase 4.3: Market Data Onboarding Pipeline                                                  |
|              - Implement single-stock & batch market data backfiller.                         |
|              - Incorporate P0 anomaly detection and holiday filtering.                        |
|              - Calculate technical indicators upon successful historical ingest.              |
|                                                                                               |
|   Phase 4.4: Financial Data Coverage Integration                                              |
|              - Decouple market data readiness from financial eligibility.                     |
|              - Implement universe coverage tracking (Market Ready vs Financial Eligible).     |
|                                                                                               |
|   Phase 4.5: API & Frontend Integration                                                       |
|              - Implement REST endpoints: GET /api/universe/stocks, POST, PATCH, coverage.     |
|              - Update frontend to support dynamic universe sizing and coverage dashboards.    |
|                                                                                               |
|   Phase 4.6: Controlled Universe Expansion Pilot                                              |
|              - Onboard Batch 1 (5 high-quality, verified NSE stocks in isolated test DB).     |
|              - Validate market data coverage, indicators, and cold-start financial safety.    |
|                                                                                               |
|   Phase 4.7: Regression, Governance & Reliability Validation                                  |
|              - Run full 329 backend tests + 143 frontend tests + clean checkout CI simulation. |
|              - Confirm production DB SHA-256 invariance.                                      |
|              - Deliver docs/phase4/PHASE_4_IMPLEMENTATION_REPORT.md.                          |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
```

---

## 10. AUDIT SIGN-OFF & VERDICT

- **Architecture Audit Status**: COMPLETE
- **Production Database Invariant**: VERIFIED (`1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`)
- **Protected Logic Files**: VERIFIED (0 modifications)
- **Ready for Implementation**: YES, starting with Phase 4.1 Database-Driven Stock Universe Service.

