# Production Deployment Roadmap: Swing Trading Intelligence Platform

> **Core Safety Principle**: Because this platform delivers actionable swing-trading intelligence and risk-managed decision support, **data freshness, historical alignment, and mathematical correctness are critical safety requirements**. A responsive UI that displays stale prices, misaligned evaluation dates, or silent mock fallbacks is treated as an operational outage.

---

## 1. Architectural Guardrails & Deployment Decisions

### 1.1 Standardized Database Path & Single-Node SQLite Operating Model
* **Database Path Standard**:
  * Unified via environment variable: `DATABASE_PATH` (defaults to `/data/swing_trading.db` in Docker, and `<PROJECT_ROOT>/database/swing_trading.db` in local dev).
  * All scripts, pipelines, and services must read `DATABASE_PATH` from a central configuration module (`backend/config.py`), eliminating hardcoded paths.
* **Single-Node SQLite Concurrency Model**:
  * **Engine**: SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), synchronous normal (`PRAGMA synchronous=NORMAL;`), and busy timeout set to 15,000ms (`PRAGMA busy_timeout=15000;`).
  * **Access Pattern**: Read-heavy web serving (FastAPI) and write-isolated scheduled ingestion. FastAPI opens connections in read-only URI mode (`file:/data/swing_trading.db?mode=ro`) or queries against pre-computed materialized tables.
  * **Volume Persistence**: Persistent Docker volume mounted to `/data` with directory permissions (`uid/gid: 10001:10001`).
* **Migration & Pre-Start Verification**:
  * Database migrations (`backend/database/migrate_*.py`) execute in the container entrypoint hook *before* the API server accepts traffic.
  * Schema integrity verification: Executes `PRAGMA integrity_check;` and index validation (`add_indexes.py`, `add_financial_indexes.py`) during container initialization.

### 1.2 Idempotent Ingestion & Atomic Staging
* **Decoupled Ingestion Runner**:
  * Scheduled job runs independently of FastAPI at **15:45 IST** (post-NSE market close) via dedicated worker container executing `backend/data_pipeline/run_daily_update.py`.
* **Atomic Pipeline Execution (No Partial Updates Exposed)**:
  * Ingestion writes price, indicator, and scoring updates into staging tables or inside an explicit, single transaction block.
  * Pre-computed tables (`opportunity_scores`, `stock_snapshots`, `sector_rankings`) are only swapped/updated after the entire 50-stock universe and quality checks pass.
  * If the pipeline fails midway (e.g., Yahoo Finance rate-limiting or Kite token expiration), the entire update rolls back. The database remains on the previous verified trading session with a status of `UPDATE_FAILED`.
  * **Exclusive Lock**: Controlled by an OS-level file lock (`/data/ingestion.lock`) to prevent concurrent pipeline runs.

### 1.3 Trading-Calendar Freshness & Decomposed Health Status
* **NSE Trading Calendar Awareness**:
  * Freshness is evaluated against the **NSE Indian Equities Trading Calendar** (accounting for trading holidays, weekends, and truncated sessions), not naive wall-clock time.
* **Component-Level Decomposed Status (`/api/data-health`)**:
  Rather than a single opaque boolean, the health endpoint reports three distinct dimensions:
  1. `price_data_status`: `CURRENT` (EOD data matches last closed NSE session), `STALE`, or `MISSING`.
  2. `indicator_status`: `SYNCHRONIZED` (1:1 date match with price series across RSI, EMA, MACD, ATR), or `UNSYNCHRONIZED`.
  3. `pipeline_status`: `IDLE`, `RUNNING`, `SUCCESS`, or `FAILED` (with timestamp, execution duration, and error diagnostics).
  * Exposes explicit metadata: `latest_trade_date`, `next_expected_trade_date`, `universe_coverage_ratio`, and `anomalous_symbols`.

### 1.4 Formalized Historical `evaluation_date` API Behavior
* **Strict Point-in-Time Semantics**:
  * Endpoints (`/api/opportunities`, `/api/stocks/:symbol`, `/api/sectors`) support `?evaluation_date=YYYY-MM-DD`.
  * If omitted, defaults to the **latest verified EOD trade date** present in the database (never server current date).
  * Invariant: Data served for `evaluation_date=T` strictly excludes any price, volume, indicator, or corporate action data timestamped after `T` (`reporting_period <= T` and `date <= T`).
  * Responses must include top-level metadata:
    ```json
    {
      "evaluation_date": "2026-10-23",
      "data_as_of": "2026-10-23T15:30:00+05:30",
      "is_historical": false
    }
    ```

### 1.5 Strict Zero-Silent-Fallback & React Error Handling
* **Zero Mock Fallback**:
  * `frontend/src/services/api.js` must strictly prohibit fallback to mock data when `VITE_USE_MOCK_DATA !== "true"`.
  * Network errors, 4xx, and 5xx responses throw strongly-typed errors (`ApiError`, `NetworkError`) with HTTP status codes and error payloads.
* **Real React Error-Handling Model**:
  * Pages (`Dashboard.jsx`, `Opportunities.jsx`, `StockDetail.jsx`, `Watchlist.jsx`) manage component-level state:
    `{ data: null, loading: false, error: "Network Error: Unable to fetch live opportunities" }`.
  * When `error` is present:
    * Render `ErrorState` from `frontend/src/components/StateComponents.jsx` displaying the error message and an interactive `onRetry` button.
    * Do not crash React tree; top-level navigation, sidebar, and theme toggle remain fully functional.
  * If `/api/data-health` reports `price_data_status !== 'CURRENT'`, a persistent amber warning banner renders at the top of the viewport indicating the date of the stale data.

### 1.6 Backup, Restore & Disaster Recovery
* **Automated Pre-Update Snapshots**:
  * Before each 15:45 IST ingestion run, SQLite `VACUUM INTO '/data/backups/swing_trading_YYYYMMDD_HHMM.db'` executes.
  * Retain 7 daily snapshots on the persistent volume.
* **Verified Restoration Procedure**:
  * Operationalize `backend/data_pipeline/restore_database.py` with an automated post-restore verification test:
    1. Restores backup into isolated directory.
    2. Runs `PRAGMA integrity_check;`.
    3. Verifies universe row counts (50 symbols, complete historical tables).
    4. Swaps restored database into active service.

### 1.7 Production Security & Hardening
* **Non-Root Execution**: Backend and frontend containers run as dedicated non-root users (`uid: 10001`).
* **CORS Restrictions**: Strict origin matching via `CORS_ORIGINS` (no wildcards `*` in production).
* **Header Hardening**: Nginx frontend enforces `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`, and `Referrer-Policy: strict-origin-when-cross-origin`.
* **API Rate Limiting**: SlowAPI / Nginx limit zone on API endpoints (e.g., 60 req/min per IP).

---

## 2. Verified Repository Asset Inventory

Before assigning implementation tasks, every required component has been verified in the local workspace:

| Layer | Repo File | Verified Status & Role |
| :--- | :--- | :--- |
| **REST API Entry** | [`backend/app.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/app.py) | **To Be Implemented** (currently 0 bytes). |
| **API Contract** | [`docs/frontend-api-contract.md`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/frontend-api-contract.md) | **Verified Contract** (8 endpoints, complete request/response schemas). |
| **Opportunity Engine** | [`backend/engines/decision_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/decision_engine.py) | **Verified** (Opportunity Score 0-100, recommendation logic). |
| **Ranking Engine** | [`backend/engines/ranking_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/ranking_engine.py) | **Verified** (Top 10 universe sweep). |
| **Stock Intelligence** | [`backend/logic/stock_intelligence.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/stock_intelligence.py) | **Verified** (Complete composite payload per symbol). |
| **Historical OHLCV** | [`backend/data_pipeline/historical_data_service.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/historical_data_service.py) | **Verified** (Retrieves sanitized daily candlestick data). |
| **Quality Monitor** | [`backend/data_pipeline/week15_quality_monitor.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/week15_quality_monitor.py) | **Verified** (Audits universe coverage, orphans, duplicates, sync). |
| **Backup / Recovery** | [`backend/data_pipeline/restore_database.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/data_pipeline/restore_database.py) | **Verified** (Non-destructive backup restoration & integrity check). |
| **Frontend Client** | [`frontend/src/services/api.js`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/frontend/src/services/api.js) | **Verified Structure** (Needs mock toggle removed, real fetch wired). |
| **UI Error Handling** | [`frontend/src/components/StateComponents.jsx`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/frontend/src/components/StateComponents.jsx) | **Verified** (`ErrorState` with retry button, `LoadingState`, `EmptyState`). |

---

## 3. Work Breakdown Structure & Phase Execution

```mermaid
flowchart TD
    subgraph Phase 1: API & Contract Testing
        P1A[Centralize backend/config.py] --> P1B[Implement backend/app.py with FastAPI]
        P1B --> P1C[Automated Contract Tests with pytest]
    end

    subgraph Phase 2: Ingestion & Freshness
        P2A[Atomic Staging & File Lock in run_daily_update.py] --> P2B[Trading Calendar Aware Health Endpoint]
        P2B --> P2C[Pre-update Backup Hook & restore_database.py Automation]
    end

    subgraph Phase 3: Frontend Zero-Mock Integration
        P3A[Remove Mock Fallback in api.js] --> P3B[Wire Real API Calls]
        P3B --> P3C[Stale-Data Warning Banner & Error Boundaries]
    end

    subgraph Phase 4: Containerization & Security
        P4A[Backend Dockerfile with non-root user] --> P4B[Frontend Multi-stage Nginx Dockerfile]
        P4B --> P4C[docker-compose.yml with persistent volume]
    end

    subgraph Phase 5: Production Validation Gate
        P5A[Rehearse Backup Restoration] --> P5B[Validate Point-in-Time Historical Invariants]
        P5B --> P5C[Cross-verify 10 Stocks vs TradingView / NSE EOD]
    end

    Phase 1 --> Phase 2 --> Phase 3 --> Phase 4 --> Phase 5
```

---

### Detailed Implementation Phases

#### Phase 1: REST API Implementation & Contract Testing
1. **Centralize Config ([`backend/config.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/config.py))**:
   * Export `DATABASE_PATH = Path(os.getenv("DATABASE_PATH", PROJECT_ROOT / "database" / "swing_trading.db"))`.
   * Export `CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")`.
2. **Build Route Controllers in [`backend/api/`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/api)**:
   * `market_routes.py`: `GET /api/market/indices`
   * `opportunity_routes.py`: `GET /api/opportunities` (invokes `ranking_engine` + `signal_engine` with rank, entry zone, stop, target, R:R).
   * `stock_routes.py`: `GET /api/stocks`, `GET /api/stocks/{symbol}`, `GET /api/stocks/{symbol}/history`.
   * `sector_routes.py`: `GET /api/sectors`.
   * `backtest_routes.py`: `GET /api/backtests/latest`.
   * `health_routes.py`: `GET /api/data-health`, `GET /healthz/live`, `GET /healthz/ready`.
3. **Automate Contract Verification Tests**:
   * Write `backend/tests/test_api_contract.py` validating every response against [`docs/frontend-api-contract.md`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/frontend-api-contract.md) using FastAPI's `TestClient`.

#### Phase 2: Ingestion Decoupling & Freshness Engine
1. **Atomic Ingestion Updates**:
   * Modify `backend/data_pipeline/run_daily_update.py` to acquire `/data/ingestion.lock`.
   * Write intermediate results to transaction staging; commit once all checks pass.
2. **Trading Calendar Integration**:
   * Implement `is_market_holiday()` and `get_last_nse_trading_session()` based on the NSE holiday list.
   * `GET /api/data-health` computes freshness by comparing database's max date with the last completed session.
3. **Automated Backup Pre-Flight**:
   * Before ingestion, create timestamped snapshot in `/data/backups/`.
   * Add a scheduled CLI task to test restoration using `restore_database.py`.

#### Phase 3: Frontend Zero-Mock Wiring & Hardening
1. **Strict Production Client**:
   * In `frontend/src/services/api.js`: remove fallback mock branches when `VITE_USE_MOCK_DATA !== 'true'`.
   * Throw clear errors on network timeouts or 5xx responses.
2. **Component Error Verification**:
   * Verify `OpportunityTable.jsx`, `SectorList.jsx`, and `PriceChart.jsx` cleanly display `ErrorState` with retry buttons when the backend is unreachable.
3. **Data Freshness Banner**:
   * In `frontend/src/layouts/MainLayout.jsx` or `TopBar.jsx`, query `/api/data-health`. If `price_data_status === 'STALE'`, show:
     `"Notice: Displaying data as of [latest_trade_date]. NSE market data has not updated yet."`

#### Phase 4: Containerization & Security Orchestration
1. **`backend/Dockerfile`**:
   * Base: `python:3.11-slim`.
   * User: non-root `appuser (uid 10001)`.
   * Web server: Uvicorn with 4 worker processes.
2. **`frontend/Dockerfile`**:
   * Stage 1: `node:20-alpine` runs `npm ci && npm run build`.
   * Stage 2: `nginx:1.25-alpine` serving assets with reverse proxy `/api` routing to backend.
3. **`docker-compose.yml`**:
   * `frontend`: port 80/443.
   * `backend`: port 8000 (internal network).
   * `cron-worker`: runs Python scheduler executing `run_daily_update.py` at 15:45 IST on weekdays.
   * Named persistent volume `market_data` mounted to `/data` across backend and worker.

#### Phase 5: Final Production Validation Gates
1. **Disaster Recovery Rehearsal**: Trigger `restore_database.py`, execute integrity check, verify zero data loss.
2. **Point-in-Time Regression**: Request historical evaluation dates (e.g., `?evaluation_date=2026-08-14`) and confirm no data after that date appears.
3. **Production Acceptance Audit**:
   * Cross-verify 10 stocks across diverse sectors against official NSE closing sheets.
   * Confirm RSI, MACD, and EMA match TradingView within a 0.5% tolerance.
   * Verify production build (`npm run build`) generates zero lint/type errors and runs with `VITE_USE_MOCK_DATA=false`.
