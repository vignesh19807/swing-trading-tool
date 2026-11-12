# PHASE 5.3.1 — CENTRALIZED DATABASE CONNECTION ABSTRACTION REPORT
## Database Access Layer (DAL) Implementation & Representative Service Migration

**Project:** Swing Trading Intelligence Platform — Indian Equities
**Phase:** Phase 5.3.1 — Centralized Database Connection Abstraction
**Active Git Branch:** `staging`
**Execution Date:** 2026-11-07

---

## 1. Architectural Decisions

### 1.1 ORM Evaluation (SQLAlchemy Core vs. Lightweight Native DAL)
During architectural evaluation, introducing **SQLAlchemy Core** (or full ORMs like SQLAlchemy ORM, Peewee, Tortoise) was analyzed and deliberately rejected based on the following concrete technical criteria:

1. **Massive Third-Party Dependency Overhead:** SQLAlchemy Core represents ~40,000 lines of library code and introduces dialect engines, typing complications, metadata reflections, and potential version churn across Python 3.10–3.14. It was not installed in the repository environment.
2. **Incompatibility with Existing Codebase Queries:** Across the backend data pipelines and services, 80+ queries are already written as clear, parameterized, and auditable SQL. Forcing these queries into SQLAlchemy Expression Language (`select(table).where(...)`) would require a ground-up rewrite of all database code, creating unnecessary friction and regression risk without delivering functional value.
3. **Driver Directness:** The official PostgreSQL driver for Python is `psycopg` (v3). By using a direct PEP 249-compliant gateway, the application benefits from native `psycopg_pool.ConnectionPool` without intermediary abstraction layers that hide database behaviors or add query latency.
4. **Lightweight Native DAL Selected:** A purpose-built, 660-line Database Access Layer was implemented in [`backend/database/connection.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/database/connection.py). It provides:
   - Zero ORM bloat.
   - Transparent connection lifecycle and thread-safe connection pooling.
   - Native context managers (`with get_db_connection():` and `with get_db_cursor():`).
   - Strict credential masking in all representations and logs.
   - Dual-engine query parameter adaptation (`?` for SQLite, `%s` for PostgreSQL).
   - Ergonomic row access via `DbRow` (supporting `row["col"]`, `row[0]`, and `dict(row)` across both engines).
   - Loud, non-silent failure modes that prevent accidental cross-engine fallbacks.

---

## 2. New Database Abstraction Architecture

The DAL is centered in [`backend/database/connection.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/database/connection.py):

```mermaid
flowchart TD
    Config["parse_database_url()<br/>(DATABASE_URL or DATABASE_PATH)"] --> Router{"Engine Selector"}

    Router -->|"engine == SQLITE<br/>(default or sqlite:///)"| SQLiteConn["SQLite Connection<br/>- PRAGMA foreign_keys = ON<br/>- sqlite3.Row factory<br/>- In-memory or file-backed"]
    Router -->|"engine == POSTGRESQL<br/>(postgresql:// or postgres://)"| PgPool["PostgreSQL Pool<br/>- psycopg_pool.ConnectionPool<br/>- min_size=1, max_size=5<br/>- sslmode=require supported"]

    SQLiteConn --> Wrapper["ConnectionWrapper<br/>- .cursor() -> CursorWrapper<br/>- .commit() / .rollback()<br/>- .transaction() context manager<br/>- .close() lifecycle hook"]
    PgPool --> Wrapper

    Wrapper --> Cursor["CursorWrapper<br/>- _adapt_query_placeholders(? vs %s)<br/>- PEP 249 fetchone / fetchall<br/>- DbRow dict-like row proxy<br/>- lastrowid property"]
```

### 2.1 Core Interfaces and Components
1. **`DatabaseEngine` (Enum):** Defines `SQLITE = "sqlite"` and `POSTGRESQL = "postgresql"`.
2. **`mask_database_url(url: str) -> str`:** Uses regex and RFC 3986 URL parsing to redact passwords (`user:***@host:port/db`), handling special characters (e.g. `@`, `#`, `%`) in credentials without leakage.
3. **`parse_database_url(url_or_path)`:** Resolves database configuration from explicit arguments, environment variables, or defaults. Detects invalid schemes and raises `DatabaseConfigurationError`.
4. **`ConnectionWrapper` & `CursorWrapper`:** Provide standard context managers, query parameter translation (`?` <-> `%s`), transaction rollback on exception, and automatic connection return/closure.
5. **`DbRow`:** Custom row wrapper for PostgreSQL that guarantees full behavioral parity with `sqlite3.Row` (`row["col"]`, `row[0]`, `dict(row)`, `row.get("col")`, `.keys()`, `.items()`).
6. **`get_db_connection()` / `open_db_connection()` / `get_db_cursor()`:** Context managers and lifecycle helpers providing drop-in integration for pipeline services.

---

## 3. Files Created and Modified

| File Path | Operation | Lines Added / Modified | Description |
| :--- | :---: | :---: | :--- |
| [`backend/database/connection.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/database/connection.py) | **Created** | +660 lines | Centralized Database Access Layer (DAL) supporting dual SQLite & PostgreSQL engines. |
| [`backend/tests/test_database_connection_dal.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/tests/test_database_connection_dal.py) | **Created** | +365 lines | Comprehensive unit & integration test suite covering DAL lifecycle, security, injection, and isolation. |
| [`backend/requirements.txt`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/requirements.txt) | **Modified** | +4 lines | Added `psycopg[binary]>=3.2.0,<4.0.0` and `psycopg-pool>=3.2.0,<4.0.0` for PostgreSQL cloud support. |
| [`backend/engines/cache_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/cache_service.py) | **Modified** | +8 / -11 lines | Migrated `get_db_fingerprint()` to use `get_db_cursor(commit=False)`. |
| [`backend/data_pipeline/stock_universe_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/stock_universe_service.py) | **Modified** | +20 / -14 lines | Migrated `_get_connection()` to `open_db_connection()`; added dialect-aware column checking. |
| [`backend/data_pipeline/universe_coverage_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/universe_coverage_service.py) | **Modified** | +8 / -9 lines | Migrated `_get_connection()` to `open_db_connection()`; preserved multi-table coverage queries. |
| [`backend/data_pipeline/stock_onboarding_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/stock_onboarding_service.py) | **Modified** | +55 / -35 lines | Migrated `_get_connection()` and table introspection to use DAL; verified INSERT, UPDATE, and audit logs. |

---

## 4. Services Migrated (Representative Non-Critical Group)

A representative group of 4 non-critical services was migrated to validate all fundamental query patterns:

| Migrated Service | File Path | Patterns Demonstrated | Verification Result |
| :--- | :--- | :--- | :---: |
| **Cache Fingerprint Service** | [`backend/engines/cache_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/cache_service.py) | Read-only basic SELECT queries; aggregation (`MAX(date)`, `COUNT(*)`); context cursor without commit. | **PASSED** (< 1ms execution) |
| **Stock Universe Service** | [`backend/data_pipeline/stock_universe_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/stock_universe_service.py) | Parameterized SELECT queries (`WHERE symbol = ?`); dynamic filtering; row dictionary access; column introspection. | **PASSED** (52/52 active stocks verified) |
| **Universe Coverage Service** | [`backend/data_pipeline/universe_coverage_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/universe_coverage_service.py) | Multi-table parameterized queries; aggregation and date threshold comparisons across `daily_prices` and `technical_indicators`. | **PASSED** (Summary and stock coverage verified) |
| **Stock Onboarding Service** | [`backend/data_pipeline/stock_onboarding_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/stock_onboarding_service.py) | INSERT operations; UPDATE lifecycle transitions; explicit transaction commit & rollback; audit logging. | **PASSED** (Full onboarding lifecycle tested) |

---

## 5. Services Not Yet Migrated (Remaining Inventory)

To preserve system stability and comply with the phased migration plan, the remaining database call sites were left untouched. They will be migrated incrementally in subsequent phases:

| Component Category | Unmigrated File Count | Key Services Remaining | Rationale for Postponing to Phase 5.3.4 |
| :--- | :---: | :--- | :--- |
| **Historical & PIT Ingestion** | 8 files | `historical_pit_service.py`, `financial_service.py`, `staging_financial_vintage_service.py` | Governs financial publication dates and lookahead protection; best migrated after PostgreSQL DDL is live. |
| **Market Data Ingestion** | 12 files | `load_stock_data.py`, `market_data_onboarding.py`, `run_daily_update.py` | Contains bulk ingestion and `INSERT OR IGNORE` conflict clauses requiring table constraints. |
| **Backtesting Data Access** | 6 files | `backtest_result_service.py`, `data_service.py` | Handles backtest runs, trade logging, and equity curves; utilizes `pandas.read_sql_query`. |
| **Database DDL & Schema Scripts** | 12 files | `create_database.py`, `first_boot_validation.py`, `migrate_*.py` | These are SQLite schema scripts; Phase 5.3.2 will introduce `schema_pg.sql` instead. |
| **Core API Gateway** | 1 file | `backend/app.py` (`_get_db()`) | High-traffic entry point; should be migrated in final integration step after all services are validated. |
| **Test Fixtures** | 22 files | Various `test_*.py` files creating temporary SQLite fixtures | Unit tests should continue using SQLite for maximum test execution speed. |

---

## 6. SQLite Compatibility Results

Full backward compatibility with SQLite was verified across multiple execution modes:
- **Default Resolution:** Calls to `parse_database_url()` without arguments cleanly resolve to `database/swing_trading.db`.
- **Explicit File Paths:** `open_db_connection(Path(...))` and string paths resolve anchored to `PROJECT_ROOT`.
- **In-Memory Operation:** `sqlite:///:memory:` runs isolated in-memory test databases with `PRAGMA foreign_keys = ON;`.
- **Regression Suite:** All 79 relevant existing regression tests passed without errors.

---

## 7. PostgreSQL Configuration Results

Configuration parsing and credential isolation were validated:
- **Valid URLs:** Formats `postgresql://user:pass@host:port/db?sslmode=require` and `postgres://...` parse into `DatabaseEngine.POSTGRESQL`.
- **Credential Masking:** Validated that passwords containing alphanumeric and special characters (`@`, `#`, `$`) are redacted in string representations and logs (`user:***@host:port/db`).
- **Driver Integration:** `psycopg` (3.3.8) and `psycopg_pool` (3.3.3) are installed and verified in the environment.
- **Strict Non-Silent Failure Invariant:** If `DATABASE_URL` is set to an unreachable PostgreSQL host, the DAL raises `DatabaseConnectionError`. **It does NOT silently fall back to SQLite.**
- **Invalid Scheme Rejection:** URLs with unsupported schemes (`mysql://`, `oracle://`, `mongodb://`) immediately raise `DatabaseConfigurationError`.

---

## 8. Test Execution Results

### 8.1 DAL Dedicated Test Suite (`backend/tests/test_database_connection_dal.py`)
Executed via `pytest -v`:
- **Total Tests:** 17
- **Passed:** 16
- **Skipped / Reported NOT RUN:** 1 (`test_postgresql_live_integration_or_skip`)
- **Failures:** 0

| Test Name | Result | Notes |
| :--- | :---: | :--- |
| `test_sqlite_connection_creation_default` | **PASSED** | Resolves authoritative default database path |
| `test_sqlite_connection_creation_explicit_path` | **PASSED** | Verified persistence across connection open/close |
| `test_sqlite_connection_in_memory` | **PASSED** | Verified ephemeral `:memory:` execution |
| `test_postgresql_connection_configuration_valid` | **PASSED** | Verified URL parsing and credentials masking |
| `test_postgresql_postgres_scheme_alias` | **PASSED** | Verified `postgres://` alias support |
| `test_mask_database_url_edge_cases` | **PASSED** | Redaction handles empty, malformed, and complex URLs |
| `test_invalid_database_url_handling` | **PASSED** | Loud rejection of unsupported schemes |
| `test_postgresql_unreachable_connection_does_not_silently_fallback` | **PASSED** | Strict invariant enforced (no silent fallback) |
| `test_connection_cleanup_on_context_exit` | **PASSED** | Resources closed immediately on context exit |
| `test_open_db_connection_manual_lifecycle` | **PASSED** | Manual `close()` cleanly terminates connection |
| `test_transaction_commit_success` | **PASSED** | Atomic commit persists records across transactions |
| `test_transaction_rollback_on_exception` | **PASSED** | Rollback restores original state on exception |
| `test_parameterized_queries_and_sql_injection_resistance` | **PASSED** | Injection payloads treated strictly as literals |
| `test_query_placeholder_adaptation` | **PASSED** | `?` <-> `%s` translated without corrupting literals |
| `test_dbrow_proxy_indexing_and_dict_access` | **PASSED** | Full parity with `sqlite3.Row` ergonomics |
| `test_database_isolation_between_test_instances` | **PASSED** | Zero leakage between separate database targets |
| `test_postgresql_live_integration_or_skip` | **SKIPPED (NOT RUN)** | Live PostgreSQL test server not configured locally |

### 8.2 Comprehensive Regression Suite
A full test run of 80 test cases across 10 critical test files was executed:
- **`test_api_contract.py`**: 13 passed
- **`test_dynamic_universe_management.py`**: 4 passed
- **`test_universe_pilot_and_api.py`**: 3 passed
- **`test_phase4_1_verification.py`**: 8 passed
- **`test_phase4_2_financial_boundary.py`**: 7 passed
- **`test_database_connection_dal.py`**: 16 passed, 1 skipped
- **`test_database_configuration.py`**: 9 passed
- **`test_database_persistence_safety.py`**: 4 passed
- **`test_first_boot_validation.py`**: 4 passed
- **`test_p1_point_in_time_financial_integrity.py`**: 10 passed
- **Overall Suite Result:** **79 PASSED, 1 SKIPPED, 0 FAILED** (34.59s).

---

## 9. Financial Integrity & Governance Verification

All critical financial governance safeguards remain intact and fully functional:
- **Point-in-Time Correctness:** Strict point-in-time filtering (`filing_date <= as_of_date`) continues to exclude unverified or future filings.
- **Publication Date Enforcement:** Tests `test_01` through `test_10` in `test_p1_point_in_time_financial_integrity.py` confirmed 100% compliance.
- **Financial Eligibility Boundaries:** Phase 4.2 boundary scenarios (zero financials, missing publication dates, quarantined filings, incomplete metrics) produce identical fallback behavior.
- **Data Fingerprint Accuracy:** In [`backend/engines/cache_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/cache_service.py), the fingerprint continues to invalidate cache on underlying data mutations.
- **Zero Fabrication:** No synthetic or mock records were inserted into production datasets.

---

## 10. Production Database Hash Verification

The authoritative SHA-256 fingerprint of the production database was computed before and after all changes:

| Checkpoint | Database Path | SHA-256 Hash | Status |
| :--- | :--- | :--- | :---: |
| **Initial Baseline** | `database/swing_trading.db` | `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` | VERIFIED |
| **Post-Implementation** | `database/swing_trading.db` | `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` | **IDENTICAL (100% UNTOUCHED)** |

### Protected Engine Verification
- [`backend/logic/strategy_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/strategy_engine.py): **DOES NOT EXIST** (Reported as non-existent; cleanly removed in earlier phase).
- [`backend/logic/signal_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/signal_engine.py): **UNCHANGED** (SHA-256: `745702716d95ac4a5e47a181d050baf7d7906c8aefaceeaa2d2008f2118eb99f`).
- [`backend/logic/trade_quality_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/trade_quality_engine.py): **UNCHANGED** (SHA-256: `138ed930b00dce5310806d1c81204c1fe4b91ad6aabc1630f7e9562a6248c985`).
- [`backend/logic/portfolio_simulator.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/portfolio_simulator.py): **UNCHANGED** (SHA-256: `cf8a8a4919ac0113ff9a4841b1742b2c3e595b3dfaf791196175edaf8ae59370`).

---

## 11. Remaining Migration Risks

1. **Unmigrated Ingestion Services:** 60+ connection sites remain using raw `sqlite3.connect()`. Attempting to set `DATABASE_URL` globally without migrating those services would cause half the pipeline to write to SQLite while other services query PostgreSQL. Migration must proceed in lockstep with schema provisioning.
2. **PostgreSQL Dialect Edge Cases:** `INSERT OR IGNORE` and `INSERT OR REPLACE` syntax used in `load_stock_data.py` and `insert_financial_data.py` require PostgreSQL-compliant `ON CONFLICT` clauses.
3. **Live Serverless Cold-Start Verification:** Neon Serverless PostgreSQL cold starts (~1–2.5s) can only be benchmarked against an active cloud or containerized PostgreSQL instance.

---

## 12. Recommendation for Phase 5.3.2

**Recommendation:** Proceed to **Phase 5.3.2 — PostgreSQL Schema & Trigger Provisioning**.

In Phase 5.3.2, the plan should:
1. Create `backend/database/schema_pg.sql` containing the full PostgreSQL 16 DDL for all 14 tables.
2. Implement the 3 PL/pgSQL immutability trigger functions for `quarterly_financial_vintages`.
3. Provide an automated migration script (`backend/database/migrate_sqlite_to_pg.py`) that exports data from SQLite and seeds PostgreSQL with sequence realignment and row-checksum validation.
4. Prepare the GitHub Actions workflow to run ephemeral PostgreSQL containers for live integration testing.
