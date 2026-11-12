# PHASE 5.3 — ZERO-COST DEPLOYMENT MIGRATION AUDIT
## SQLite to Serverless PostgreSQL Architecture Impact Assessment

**Project:** Swing Trading Intelligence Platform — Indian Equities
**Target Environment:** ₹0/Month Production & Staging Architecture
**Target Stack:**
- **Frontend:** Vercel Hobby (React 19 + Vite 8 + TypeScript 5.7)
- **Backend:** Render Free Web Service (FastAPI + Uvicorn)
- **Database:** Neon Free Serverless PostgreSQL (PostgreSQL 16)

**Audit Status:** AUDIT ONLY (No code modifications or database mutations applied)
**Production Database Hash Verified:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
**Protected Logic Engines Verified:** Unmodified (0 database dependencies)

---

## 1. Executive Summary

### 1.1 Objective & Background
The existing cloud deployment blueprint (Phases 5.0–5.2) utilizes SQLite hosted on a persistent disk attached to a Render web service. While functionally validated, Render persistent disks require paid instance tiers ($7/month minimum for web service + $0.25/GB/month for persistent disk storage), making the deployment incompatible with the strict **₹0/month ($0.00)** operational budget.

To achieve a perpetual zero-cost operational model for staging and production, the platform architecture must transition from file-based SQLite to a modern serverless relational database:
- **Neon Free PostgreSQL**: Provides 0.5 GiB (500 MB) persistent relational storage, automated branching, and connection pooling at **₹0/month**.
- **Render Free Web Service**: Provides 512 MB RAM, 0.1 vCPU FastAPI hosting with automated GitHub deployments at **₹0/month**.
- **Vercel Hobby**: Provides global edge CDN, automated TLS, and React SPA hosting at **₹0/month**.

### 1.2 Core Audit Findings
1. **Trading Logic Agnosticism (Zero Risk):** The protected core strategy engines ([`signal_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/signal_engine.py), [`trade_quality_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/trade_quality_engine.py), and [`portfolio_simulator.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/portfolio_simulator.py)) possess **0 SQL queries and 0 database imports**. They operate exclusively on in-memory Pandas DataFrames and Python dictionaries. Core trading logic is 100% insulated from database migration risks.
2. **Data Sizing Suitability:** The production dataset is **8.65 MB (9,068,544 bytes)** across 13 domain tables (51,939 total records). Neon's 500 MB free allocation represents **57x the current production storage footprint**, giving immense headroom (~1.7% utilized) for universe expansion.
3. **Architectural Decoupling Requirement:** The codebase currently lacks an Object-Relational Mapping (ORM) layer or a centralized database gateway. Across the backend, **83 distinct calls directly invoke `sqlite3.connect(DATABASE_PATH)`** with SQLite-specific parameter markers (`?`), conflict handlers (`INSERT OR IGNORE`), and PRAGMAs. A centralized Database Access Layer (DAL) / Connection Pool is required.
4. **Cold-Start Compounding:** Both Render Free (spins down after 15 minutes of inactivity; ~50–90s wake-up) and Neon Free (suspends compute after 5 minutes of inactivity; ~1–2.5s wake-up) feature scale-to-zero semantics. An initial request to an idle deployment will experience **50–95 seconds** of cold-start latency, requiring explicit frontend UX handling and uptime keep-alive strategies.

---

## 2. Existing Database Architecture

### 2.1 Database Files and Footprint
The platform maintains two SQLite database instances:

| Metric | Production Database (`swing_trading.db`) | Staging Expansion Database (`staging_financial_expansion.db`) |
| :--- | :--- | :--- |
| **Path** | `database/swing_trading.db` | `database/staging_financial_expansion.db` |
| **File Size** | 9,068,544 bytes (8.65 MB) | 9,105,408 bytes (8.68 MB) |
| **SHA-256 Hash** | `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` | `FE23A865CFBAE48D...` |
| **Domain Tables** | 13 tables (+ `sqlite_sequence`) | 14 tables (+ `sqlite_sequence`) |
| **Total Rows** | 51,939 rows | 51,967 rows |
| **Triggers** | 0 triggers | 3 immutability / lineage triggers |
| **Indexes** | 13 custom B-tree indexes | 5 custom B-tree indexes |

### 2.2 Table-by-Table Inventory & Data Distribution
Detailed breakdown of tables, record counts, and schema widths:

| Table Name | Production Rows | Staging Rows | Columns | Primary Purpose / Governance Role |
| :--- | :---: | :---: | :---: | :--- |
| `companies` | 52 | 52 | 8 | Core stock master (symbol, sector, industry, exchange) |
| `daily_prices` | 25,746 | 25,746 | 9 | Daily OHLCV price history (2-year lookback) |
| `technical_indicators` | 25,746 | 25,746 | 12 | Precomputed RSI, MACD, EMA, ATR, Technical Scores |
| `quarterly_results` | 260 | 260 | 12 | Historical quarterly financials with `publication_date` |
| `quarterly_financial_vintages` | *N/A* | 28 | 56 | Multi-dimensional PIT financial vintages & audit lineage |
| `sectors` | 17 | 17 | 2 | Sector taxonomic classification |
| `industries` | 45 | 45 | 3 | Industry taxonomic classification |
| `signals` | 0 | 0 | 8 | Generated trading signals (ephemeral / on-demand) |
| `financial_scores` | 0 | 0 | 7 | Calculated fundamental health scores |
| `opportunity_scores` | 0 | 0 | 7 | Composite rank scores |
| `backtest_runs` | 2 | 0 | 10 | Backtest execution metadata and run configurations |
| `backtest_results` | 2 | 0 | 6 | Per-symbol backtest evaluation metrics |
| `backtest_trades` | 1 | 0 | 23 | Granular trade logs (P&L, execution timestamps, slippage) |
| `backtest_equity_curve` | 125 | 0 | 8 | Portfolio valuation time-series and drawdowns |

### 2.3 Connection & Concurrency Patterns
- **No ORM:** All SQL is raw SQL strings executed via standard `cursor.execute()` or `pandas.read_sql_query(sql, conn)`.
- **Per-Request / Per-Call Connection:** Modules open and close dedicated SQLite connections via `sqlite3.connect(DATABASE_PATH)` rather than retaining long-lived connection handles.
- **Locking Model:** Relies on SQLite file-level locking. Write transactions acquire an exclusive filesystem lock (`PRAGMA journal_mode = WAL` is used in ingestion pipelines, but default delete journal mode exists in base connections).
- **Configuration Proxy:** `backend/config.py` provides `DATABASE_PATH` as a dynamic `os.PathLike` proxy, allowing dynamic redirection via the `DATABASE_PATH` environment variable.

---

## 3. SQLite Dependency Inventory

An exhaustive code inspection was conducted across all 223 Python modules in the `backend/` directory (excluding virtual environments and temporary scratch scripts).

### 3.1 Inventory Summary
- **Total Python files scanned:** 223
- **Files importing `sqlite3`:** 93
- **Files executing `sqlite3.connect()`:** 84
- **Files referencing `PRAGMA`:** 29
- **Files querying SQLite system catalogs (`sqlite_master`, `sqlite_sequence`):** 14
- **Files using SQLite conflict clauses (`INSERT OR IGNORE / REPLACE`):** 6
- **Files relying on `cursor.lastrowid`:** 5
- **Files setting `conn.row_factory = sqlite3.Row`:** 12
- **Files using `pandas.read_sql_query`:** 10

### 3.2 Granular Breakdown by Component

#### A. Core API & Configuration
- [`backend/config.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/config.py): Defines `_DatabasePath` proxy and `get_database_path()`. Needs extension to support `DATABASE_URL` (PostgreSQL URI).
- [`backend/app.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/app.py):
  - Defines `_get_db()`: opens `sqlite3.connect(DATABASE_PATH)` with `conn.row_factory = sqlite3.Row`.
  - Queries `sqlite_master` in `/api/readiness` and `/api/backtest/results` endpoints.
  - Direct calls to `_get_db()` in 7 route handlers.

#### B. Data Pipeline & Services (41 Files)
The data pipeline contains the highest density of SQLite-specific operations:
1. **Ingestion & Data Services:**
   - [`backend/data_pipeline/data_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/data_service.py): 5 `sqlite3.connect()` calls, parameterized queries with `?`, `read_sql_query()`.
   - [`backend/data_pipeline/historical_pit_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/historical_pit_service.py): Own `_get_connection()` method, point-in-time date filtering using `date(?)`.
   - [`backend/data_pipeline/financial_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/financial_service.py): 4 `sqlite3.connect()` calls, manual commit/rollback handling.
   - [`backend/data_pipeline/stock_universe_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/stock_universe_service.py): Universe table querying, dynamic company additions.
   - [`backend/data_pipeline/stock_onboarding_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/stock_onboarding_service.py): Uses `cursor.lastrowid` to capture newly created company IDs.
   - [`backend/data_pipeline/staging_financial_vintage_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/staging_financial_vintage_service.py): Uses `cursor.lastrowid` for vintage lineage tracking.
2. **Conflict Resolution & Bulk Insertion:**
   - [`backend/data_pipeline/load_stock_data.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/load_stock_data.py): Uses `INSERT OR IGNORE INTO daily_prices` and `cursor.lastrowid`.
   - [`backend/data_pipeline/insert_financial_data.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/insert_financial_data.py): Uses `INSERT OR REPLACE INTO quarterly_results`.
   - [`backend/data_pipeline/backtest_result_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/backtest_result_service.py): Uses `INSERT OR REPLACE INTO backtest_results`.
3. **Backup & Recovery Utilities:**
   - [`backend/data_pipeline/backup_database.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/backup_database.py): Relies on `sqlite3.Connection.backup()` API.
   - [`backend/data_pipeline/restore_database.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/restore_database.py): Copies raw SQLite `.db` binary files and runs `PRAGMA integrity_check`.

#### C. Database Schema & Migration Scripts (12 Files)
- [`backend/database/create_database.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/database/create_database.py): DDL definitions containing `AUTOINCREMENT`, `REAL`, `TEXT`, `PRAGMA foreign_keys = ON`.
- [`backend/database/first_boot_validation.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/database/first_boot_validation.py): Inspects `sqlite_master` and executes `PRAGMA table_info`.
- [`backend/database/migrate_staging_financial_vintages.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/database/migrate_staging_financial_vintages.py): Contains SQLite triggers using `RAISE(ABORT, ...)` and generated virtual columns `GENERATED ALWAYS AS (...) VIRTUAL`.
- Migration history files (`migrate_week2.py`, `migrate_week3.py`, `migrate_week7.py`, `migrate_week8.py`): SQLite DDL scripts.

#### D. Protected Logic Engines (Zero Dependencies)
- [`backend/logic/signal_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/signal_engine.py): **0 SQL / 0 SQLite imports**
- [`backend/logic/trade_quality_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/trade_quality_engine.py): **0 SQL / 0 SQLite imports**
- [`backend/logic/portfolio_simulator.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/portfolio_simulator.py): **0 SQL / 0 SQLite imports**
- [`backend/logic/strategy_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/strategy_engine.py): Non-existent / deleted in earlier refactoring.

#### E. Test Suite (23 Test Files)
- 23 test files directly import `sqlite3` to set up isolated test fixtures via `tempfile.NamedTemporaryFile(suffix='.db')` or in-memory databases.
- 13 test files (API contracts, pure logic verification, data readiness) are completely database-agnostic.

---

## 4. PostgreSQL Compatibility Matrix

A granular mapping between current SQLite constructs and PostgreSQL 16 equivalents:

| Feature / Pattern | Current SQLite Implementation | PostgreSQL 16 Equivalent | Migration Complexity | Risk Level |
| :--- | :--- | :--- | :--- | :--- |
| **Parameter Markers** | Positional `?` (e.g. `WHERE symbol = ?`) | Positional `%s` (psycopg) or `$1, $2` (asyncpg) | Moderate (Across ~120 queries) | Low |
| **Auto-Increment PK** | `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` or `INT GENERATED ALWAYS AS IDENTITY` | Low (Schema DDL only) | Low |
| **Conflict Resolution** | `INSERT OR IGNORE INTO ...` | `INSERT INTO ... ON CONFLICT (...) DO NOTHING` | Low (6 files affected) | Low |
| **Replace / Upsert** | `INSERT OR REPLACE INTO ...` | `INSERT INTO ... ON CONFLICT (...) DO UPDATE SET ...` | Low (3 files affected) | Low |
| **Last Inserted ID** | `cursor.lastrowid` | `INSERT INTO ... RETURNING id` followed by `cursor.fetchone()[0]` | Moderate (5 files affected) | Medium |
| **Row Factory** | `conn.row_factory = sqlite3.Row` | `psycopg.rows.dict_row` (psycopg 3) or `RealDictCursor` (psycopg 2) | Low (Handled at connection pool) | Low |
| **Foreign Key Enforcement** | Per-connection `PRAGMA foreign_keys = ON;` | Always enabled natively by PostgreSQL engine | Low (Eliminate PRAGMA call) | None |
| **Schema Introspection** | `PRAGMA table_info(table_name)` | `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s` | Low (2 files affected) | Low |
| **Catalog Check** | `SELECT name FROM sqlite_master WHERE type='table'` | `SELECT table_name FROM information_schema.tables WHERE table_schema='public'` | Low (14 files affected) | Low |
| **Integrity Checks** | `PRAGMA integrity_check` | `SELECT count(*) ...` or native PostgreSQL constraints / `pg_amcheck` | Low (Replace with health query) | Low |
| **Generated Virtual Columns** | `GENERATED ALWAYS AS (...) VIRTUAL` | `GENERATED ALWAYS AS (...) STORED` (Postgres requires `STORED`) | Moderate (DDL adjustment) | Low |
| **Immutability Triggers** | `CREATE TRIGGER ... BEGIN SELECT RAISE(ABORT, '...'); END;` | PL/pgSQL function returning `TRIGGER` with `RAISE EXCEPTION '...'` | High (Requires PL/pgSQL syntax) | Medium |
| **Floating Point Types** | `REAL` (IEEE 754 float) | `DOUBLE PRECISION` (for prices) or `NUMERIC(14, 4)` (for ratios) | Moderate (Type mapping) | Low |
| **Date & Timestamps** | `TEXT` ISO-8601 strings (`'YYYY-MM-DD'`) | Native `DATE` and `TIMESTAMPTZ` | Moderate (Driver auto-parses dates) | Low |
| **Boolean Values** | `INTEGER` (`0` or `1`) | Native `BOOLEAN` (`TRUE` or `FALSE`) | Moderate (Handle in ORM / DAL) | Low |
| **Database Backup** | `conn.backup(target_conn)` API | `pg_dump` CLI or logical table export (CSV / JSON) | Moderate (Tooling replacement) | Low |
| **Concurrency & Pooling** | Single file handle per thread, file locks | Client connection pool (`psycopg_pool.ConnectionPool`) | Moderate (New pool module) | Low |

---

## 5. Financial Data Integrity Risk Assessment

### 5.1 Point-in-Time (PIT) Governance Protection
- **Current Guarantee:** Financial queries filter by `filing_date <= :as_of_date` or `published_at <= :as_of_date` to prevent lookahead bias.
- **PostgreSQL Impact:** PostgreSQL provides strict, type-safe `DATE` and `TIMESTAMPTZ` comparisons. Unlike SQLite's text-based string collation, PostgreSQL natively indexes dates with standard B-tree indexes, ensuring identical historical point-in-time isolation with superior execution performance.

### 5.2 Vintage Immutability & Constraint Triggers
In `staging_financial_expansion.db`, three critical triggers enforce governance:
1. `prevent_vintage_deletion`: Blocks any `DELETE` on financial vintages.
2. `prevent_vintage_financial_mutation`: Blocks `UPDATE` on core figures (`revenue`, `net_profit`, `eps`, `published_at`).
3. `prevent_extraction_restatement_conflation`: Blocks conflicting classification attributes.

**PostgreSQL Implementation Requirement:**
In PostgreSQL, triggers cannot execute inline `RAISE(ABORT, ...)` expressions within SQL statements. They must be defined as standalone PL/pgSQL trigger functions:
```sql
CREATE OR REPLACE FUNCTION trg_enforce_vintage_immutability()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Illegal deletion: Historical financial vintages are immutable and cannot be deleted.';
    ELSIF TG_OP = 'UPDATE' THEN
        IF (NEW.company_id <> OLD.company_id) OR
           (NEW.quarter <> OLD.quarter) OR
           (NEW.revenue <> OLD.revenue) OR
           (NEW.net_profit <> OLD.net_profit) OR
           (NEW.eps <> OLD.eps) OR
           (NEW.published_at <> OLD.published_at) THEN
            RAISE EXCEPTION 'Illegal mutation: Financial figures and publication timestamps are immutable. Insert a new vintage instead.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vintage_immutability
BEFORE UPDATE OR DELETE ON quarterly_financial_vintages
FOR EACH ROW EXECUTE FUNCTION trg_enforce_vintage_immutability();
```
This guarantees identical financial safeguards with database-enforced integrity.

### 5.3 Audit Trails & Checksum Parity Verification
- **SQLite Hash Invariant:** The production database hash (`1A2036...`) is an operating-system file hash. Because PostgreSQL stores data in pages with transaction identifiers (`xmin`, `xmax`) and write-ahead logs, a single file hash cannot be used.
- **Canonical Deterministic Hashing:** Data equivalence between SQLite and PostgreSQL must be validated using deterministic table content hashing:
  ```sql
  SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY id)) FROM quarterly_results t;
  ```
- **Zero Data Loss Guarantee:** Migration verification requires 100% match on:
  1. Exact row counts for all 13 production tables and 1 staging table.
  2. Exact sums of key financial metrics (`SUM(revenue)`, `SUM(net_profit)`, `SUM(close)`).
  3. Pre- and post-migration backtest result equivalence against identical test runs.

---

## 6. Data Migration Strategy

A 4-stage deterministic migration pipeline from SQLite to Neon PostgreSQL:

```mermaid
flowchart LR
    A["SQLite Source<br/>(swing_trading.db)"] -->|"1. Extract & Serialize<br/>(Deterministic ETL)"| B["Canonical JSON / CSV<br/>Intermediate Files"]
    B -->|"2. Schema DDL<br/>(PostgreSQL 16 Dialect)"| C["Neon Free PostgreSQL<br/>(DDL Applied)"]
    C -->|"3. Bulk Ingest<br/>(COPY / Batch Insert)"| D["Loaded Tables<br/>(Neon Cloud DB)"]
    D -->|"4. Checksum & Row Verification"| E["Verification Report<br/>(100% Match Verified)"]
```

### 6.1 Phase 1 — Schema Provisioning (`schema_pg.sql`)
1. Generate PostgreSQL-compliant DDL with:
   - Primary keys as `BIGSERIAL PRIMARY KEY`.
   - Data types mapped: `TEXT` -> `VARCHAR` / `TEXT`, `REAL` -> `DOUBLE PRECISION`, `INTEGER` booleans -> `BOOLEAN`.
   - Virtual generated columns defined as `STORED`.
   - Foreign key constraints with `ON DELETE RESTRICT`.
2. Apply PL/pgSQL immutability trigger functions.

### 6.2 Phase 2 — Extraction & Transformation (`export_sqlite.py`)
1. Open read-only connection to SQLite source.
2. Read each table in topological order (dependency hierarchy):
   `sectors` -> `industries` -> `companies` -> `daily_prices` -> `technical_indicators` -> `quarterly_results` -> `quarterly_financial_vintages` -> `backtest_*`.
3. Normalize date formats and boolean integers (`0/1` -> `False/True`).
4. Handle `NaN` / `None` values to ensure valid SQL `NULL` representations.

### 6.3 Phase 3 — Ingestion & Sequence Realignment (`load_pg.py`)
1. Disable triggers temporarily during initial seed loading.
2. Ingest records using batch parameterized inserts (`psycopg.Cursor.executemany()`) or PostgreSQL `COPY`.
3. Re-enable all immutability triggers.
4. **Sequence Realignment:** Explicitly advance PostgreSQL auto-increment sequences to match max imported IDs:
   ```sql
   SELECT setval(pg_get_serial_sequence('companies', 'id'), coalesce(max(id), 1)) FROM companies;
   SELECT setval(pg_get_serial_sequence('daily_prices', 'id'), coalesce(max(id), 1)) FROM daily_prices;
   SELECT setval(pg_get_serial_sequence('technical_indicators', 'id'), coalesce(max(id), 1)) FROM technical_indicators;
   SELECT setval(pg_get_serial_sequence('quarterly_results', 'id'), coalesce(max(id), 1)) FROM quarterly_results;
   ```

### 6.4 Phase 4 — Data Equivalence Audit & Rollback Plan
- **Verification Script:** Computes record count, min/max ID, and column hashes across both databases.
- **Rollback Procedure:** The SQLite database files remain completely untouched on disk. If Neon connectivity fails or data mismatches occur, the application reverts instantly via `DATABASE_URL=""` falling back to local SQLite.

---

## 7. Cloud Deployment Architecture (₹0/Month)

### 7.1 Target Cloud Topology

```mermaid
flowchart TD
    subgraph Client Tier ["Client Browser"]
        User["User Browser"]
    end

    subgraph Vercel ["Vercel Hobby Tier (₹0/mo)"]
        Frontend["React 19 + Vite 8 SPA<br/>Global Edge CDN<br/>100 GB Bandwidth"]
    end

    subgraph Render ["Render Free Tier (₹0/mo)"]
        Backend["FastAPI Backend<br/>512 MB RAM / 0.1 vCPU<br/>Auto-sleep after 15m idle"]
        KeepAlive["Cron Ping (Optional)<br/>Keeps warm during market hours"]
    end

    subgraph Neon ["Neon Free Tier (₹0/mo)"]
        PgBouncer["Neon Connection Pooler<br/>Port 6543 (Pooled)"]
        Postgres["PostgreSQL 16 Engine<br/>0.5 GiB (500 MB) Storage<br/>Auto-suspend after 5m idle"]
    end

    User -->|"HTTPS (Static Assets)"| Frontend
    Frontend -->|"REST API Calls (CORS)"| Backend
    Backend -->|"psycopg_pool (SSL required)"| PgBouncer
    PgBouncer --> Postgres
    KeepAlive -.->|"GET /api/health"| Backend
```

### 7.2 Component Specifications & Constraints

| Resource | Service / Tier | Free Quota / Limits | Platform Constraints | Platform Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | Vercel Hobby | Unlimited deployments, 100 GB/mo bandwidth | Non-commercial hobby use | Fits platform staging / demo usage |
| **Backend** | Render Free Web Service | 512 MB RAM, 0.1 vCPU, 750 free instance hrs/mo | Spins down after 15 mins of inactivity; 50–90s cold start | Extended client HTTP timeout (120s) + loading screen |
| **Database** | Neon Free Serverless | 0.5 GiB (500 MB) storage, 0.25 vCPU compute | Auto-suspends after 5 mins of inactivity; 1–2.5s wake-up | Current data is 8.65 MB (~1.7% limit); pooled endpoint |
| **Networking** | TLS / Outbound | Unlimited inbound / outbound | Render Free allows outbound connections over standard ports | Connects to Neon via TLS `sslmode=require` |

### 7.3 Monthly Cost Breakdown

| Component | Provider | Tier | Monthly Cost (INR) | Monthly Cost (USD) |
| :--- | :--- | :--- | :---: | :---: |
| Frontend Hosting | Vercel | Hobby | ₹0.00 | $0.00 |
| Backend Hosting | Render | Free Web Service | ₹0.00 | $0.00 |
| Relational Database | Neon | Free Serverless | ₹0.00 | $0.00 |
| SSL / TLS Certificates | Vercel / Render / Let's Encrypt | Automated | ₹0.00 | $0.00 |
| CI / CD Automation | GitHub Actions | Public Repo (Free) | ₹0.00 | $0.00 |
| **Total Monthly Spend** | | | **₹0.00** | **$0.00** |

### 7.4 Cold-Start Analysis & Mitigation Plan
When both Render Free and Neon Free are inactive:
1. **Cold Start Latency Breakdown:**
   - Render container spin-up & Python startup: ~50–90 seconds.
   - Neon serverless compute resume: ~1–2.5 seconds.
   - **Combined Cold-Start Latency:** **~51–92.5 seconds** on the very first incoming request.
2. **Mitigations for ₹0/mo Architecture:**
   - **Client-Side Timeout Expansion:** Frontend Axios/Fetch client timeout must be increased from default 10s to **120 seconds**.
   - **Intelligent Wake-Up UX:** React frontend intercepts slow initial health-check responses and displays:
     *"Cloud servers are waking up from free standby (~45s). Please hold on..."* with a live progress indicator.
   - **Optional External Uptime Ping:** A free ping service (e.g., cron-job.org or GitHub Actions scheduled curl) hitting `/api/health` every 14 minutes during Indian Market Hours (9:00 AM – 3:30 PM IST) prevents sleep during active usage windows without incurring costs.

---

## 8. Testing Strategy

### 8.1 Dual-Backend Database Access Layer (DAL)
To preserve test speed and developer velocity, the application should implement a **dual-engine Database Gateway**:
- **Local Testing & Fast CI:** Default to SQLite in-memory (`:memory:`) or temporary `.db` files when `DATABASE_URL` is omitted.
- **Staging, Production & CI Integration:** Use PostgreSQL when `DATABASE_URL` (starts with `postgresql://` or `postgres://`) is provided.

```python
# Conceptual DAL Factory (backend/database/connection.py)
import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_cursor():
    if DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")):
        with pg_pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                yield cur
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

### 8.2 GitHub Actions CI Integration
GitHub Actions workflows ([`.github/workflows/ci.yml`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/.github/workflows/ci.yml)) can run full PostgreSQL integration tests without external cloud dependencies by attaching an ephemeral PostgreSQL service container:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_DB: swing_trading_test
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - 5432:5432
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```
This enables 100% portable CI execution of all financial governance tests against actual PostgreSQL engines on every push.

---

## 9. Estimated Implementation Complexity

### 9.1 Component Complexity Breakdown

| Architectural Component | Files to Modify / Create | Complexity Level | Estimated Effort |
| :--- | :--- | :---: | :---: |
| **Database Gateway / Connection Pool** | Create `connection_pool.py`, update `config.py` | Low | 3 hours |
| **PostgreSQL DDL & Trigger Functions** | Create `schema_pg.sql`, `triggers_pg.sql` | Medium | 4 hours |
| **ETL & Data Migration Utilities** | Create `export_sqlite.py`, `load_pg.py`, `verify_pg.py` | Medium | 4 hours |
| **Data Pipeline Query Refactoring** | Modify `data_service.py`, `financial_service.py`, `historical_pit_service.py`, `stock_universe_service.py` | Medium | 6 hours |
| **API Endpoints & Health Checks** | Modify `app.py` (`_get_db()`, `readiness`, system catalog checks) | Low | 2 hours |
| **CI / CD Pipeline Updates** | Update `.github/workflows/ci.yml` (add Postgres service) | Low | 2 hours |
| **Frontend Cold-Start Handling** | Update API client timeout and add wake-up banner in React UI | Low | 2 hours |
| **Total Estimated Implementation Effort** | **~23 Engineering Hours** | | |

### 9.2 Risk Matrix

| Risk Factor | Probability | Severity | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **Cold-start UX degradation** | High | Medium | Add loading state in React UI; configure 120s timeout; optional daytime keep-alive ping. |
| **Query syntax regressions (`?` vs `%s`)** | Medium | Medium | Implement DAL query adapter or helper function; comprehensive unit test suite execution. |
| **Trigger syntax mismatch** | Low | High | Develop and test PL/pgSQL triggers against ephemeral PostgreSQL container before production deploy. |
| **Financial data loss or truncation** | Low | Critical | Automated checksum verification script matching exact pre- and post-migration record hashes and sums. |

---

## 10. Recommended Migration Sequence

A phased, low-risk execution plan for subsequent phases:

```mermaid
flowchart TD
    P1["Phase 5.3.1: Connection & Abstraction Layer<br/>Create centralized database adapter supporting dual SQLite/Postgres"]
    P2["Phase 5.3.2: DDL & Trigger Translation<br/>Define PostgreSQL 16 schema, constraints, and PL/pgSQL triggers"]
    P3["Phase 5.3.3: Ingestion & Verification Tooling<br/>Write automated SQLite-to-Neon migration and checksum verification script"]
    P4["Phase 5.3.4: Data Pipeline & Query Adaptation<br/>Refactor raw SQL across services to use parameterized connection gateway"]
    P5["Phase 5.3.5: CI/CD Service Container Integration<br/>Add ephemeral postgres:16 service container to GitHub Actions workflow"]
    P6["Phase 5.3.6: Staging Deployment on Neon & Render<br/>Deploy staging backend to Render Free connected to Neon Free database"]

    P1 --> P2 --> P3 --> P4 --> P5 --> P6
```

1. **Step 1 — Connection Abstraction:** Build `backend/database/connection.py` implementing connection pooling (`psycopg_pool`) with transparent fallback to SQLite when `DATABASE_URL` is unset.
2. **Step 2 — Schema Translation:** Finalize `backend/database/schema_pg.sql` with PostgreSQL types, `STORED` virtual columns, and PL/pgSQL immutability functions.
3. **Step 3 — Migration Scripting:** Develop `backend/database/migrate_sqlite_to_neon.py` with comprehensive row-by-row checksum validation.
4. **Step 4 — Service Decoupling:** Refactor backend services to replace direct `sqlite3.connect()` calls with the centralized gateway.
5. **Step 5 — CI Validation:** Enable `postgres:16-alpine` in GitHub Actions and run all 351 backend tests against PostgreSQL.
6. **Step 6 — Remote Staging Deployment:** Provision free Neon PostgreSQL database, populate data, deploy Render backend with `DATABASE_URL`, and deploy Vercel frontend.

---

## 11. Unresolved Blockers & Operational Limitations

1. **Compounded Cold-Start Delay (50–95s):**
   *Limitation:* On Render Free, an inactive backend container requires ~50–90 seconds to boot. Paired with Neon's 1–2.5s compute resume, the first request after 15 minutes of idle time will pause.
   *Resolution:* Acceptable for a ₹0/month personal/staging project; mitigated by client-side progress notifications and daytime pinging.
2. **Absence of Unified ORM:**
   *Limitation:* Because the application uses raw SQL strings across 83 connect sites, query adaptation requires manual refactoring of parameter markers (`?` -> `%s`) and conflict syntax.
   *Resolution:* The centralized DAL connection adapter will standardize cursor generation and query execution.
3. **Neon Free Storage Cap (500 MB):**
   *Limitation:* Free storage is capped at 0.5 GiB.
   *Resolution:* Current production database is 8.65 MB (~1.7% of cap). Storage capacity is sufficient for several years of 52-stock data or expanding to ~500 stocks.

---

## 12. Final Readiness Verdict

### **VERDICT: READY WITH LIMITATIONS**

### Detailed Justification
- **Why "READY":**
  1. The core trading algorithms ([`signal_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/signal_engine.py), [`trade_quality_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/trade_quality_engine.py), [`portfolio_simulator.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/portfolio_simulator.py)) are **100% database-agnostic** with zero database imports or queries.
  2. The production data size (8.65 MB, ~52,000 rows) fits comfortably within Neon Free's 500 MB limit with a 57x safety margin.
  3. The zero-cost hosting stack (Vercel Hobby + Render Free + Neon Free) achieves **₹0.00/month ($0.00/month)** perpetually with zero infrastructure expense.
- **Why "WITH LIMITATIONS":**
  1. **Dialect Incompatibilities:** 83 raw `sqlite3.connect` invocations, PRAGMA dependencies, SQLite conflict clauses, and SQLite trigger syntax (`RAISE(ABORT)`) cannot run on PostgreSQL without an abstraction gateway and query standardization.
  2. **Cold-Start Latency:** Free-tier spin-down requires frontend UX enhancements (120s timeout and a wake-up progress banner) to avoid premature timeout errors on idle cold boots.
  3. **Verification Invariant Transition:** File-level SHA-256 validation must be translated to deterministic row/column content hashing to guarantee zero data loss.
