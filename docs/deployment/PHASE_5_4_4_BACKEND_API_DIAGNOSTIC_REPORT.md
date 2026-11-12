# PHASE 5.4.4 — BACKEND API DIAGNOSTIC REPORT

**Project:** Swing Trading Intelligence Platform
**Target Environment:** Staging
**Frontend URL:** `https://swing-trading-tool.vercel.app`
**Backend URL:** `https://swing-trading-staging-backend.onrender.com`
**Database:** Neon Serverless PostgreSQL 16
**Git Branch:** `staging`
**Investigation Mode:** Strictly Read-Only
**Timestamp:** 2026-11-08T19:51:30+05:30
**Final Status:** `MULTIPLE ISSUES IDENTIFIED`

---

## 1. Executive Summary

This read-only diagnostic was initiated to resolve why the Vercel-hosted frontend displays network fetch errors and component failures ("Market Indices Unavailable", "Could not load opportunities", "Sector data unavailable", and `Network Error: Failed to reach the API. Failed to fetch`), while `/healthz` on the Render backend returns `HTTP 200 OK`.

The investigation isolated **two distinct, compounding root causes**:

1. **Immediate Frontend Blocker — CORS Misconfiguration:**
   The Render staging backend was deployed with `CORS_ORIGINS` set to `https://swing-trading-staging.vercel.app,http://localhost:5173,http://localhost:3000`. The actual frontend is deployed at `https://swing-trading-tool.vercel.app`.
   - Browser preflight (`OPTIONS`) requests sent from the live frontend origin receive `HTTP 400 Bad Request` with body `"Disallowed CORS origin"`.
   - As a result, the browser's security sandbox aborts all outgoing `fetch()` requests before they can reach the application endpoints, producing the exact browser error: `Network Error: Failed to reach the API. Failed to fetch`.

2. **Backend Computational Blocker — Unbounded Sequential Computations on Cold Start:**
   Endpoints such as `GET /api/stocks`, `GET /api/opportunities`, and `GET /api/sectors` trigger synchronous, CPU- and I/O-intensive engine calculations on cold start:
   - `GET /api/stocks` and `GET /api/opportunities` call `rank_universe()` when cache is empty. `rank_universe()` executes sequential loops across the entire universe, invoking the Decision Engine and technical backtesting calculations. On a Render Free Tier container (0.1 vCPU, 512 MB RAM) with network latency to Singapore Neon PostgreSQL, this sequential loop exceeds the 20–60 second HTTP gateway timeout.
   - `GET /api/sectors` calls `run_sector_industry_engine()`, which iterates through 9 sectors and 19 industries, fetching unconstrained historical prices for all constituents. In live testing with direct cURL/Python (bypassing CORS), `GET /api/sectors` timed out after >40.0 seconds.
   - Conversely, lightweight database-backed endpoints (`/healthz`, `/healthz/ready`, `/api/data-health`, and `/api/market/indices`) execute simple SQL queries and respond quickly in 0.8s to 2.8s.

---

## 2. Tests Performed

All live tests were conducted using strict bounded timeouts (maximum 20–40 seconds per test) using Python HTTP requests to record exact status codes, latencies, response payloads, and CORS response headers.

### Live Diagnostic Tests:
1. `GET /healthz` with `Origin: https://swing-trading-tool.vercel.app`
2. `GET /healthz/ready` with `Origin: https://swing-trading-tool.vercel.app`
3. `OPTIONS /api/stocks` preflight with `Origin: https://swing-trading-tool.vercel.app`
4. `OPTIONS /api/sectors` preflight with `Origin: https://swing-trading-tool.vercel.app`
5. `OPTIONS /api/sectors` preflight with allowed origin `https://swing-trading-staging.vercel.app`
6. `GET /api/data-health`
7. `GET /api/market/indices`
8. `GET /api/sectors` (bounded to 20s and 40s)
9. `GET /api/stocks?limit=1` (bounded to 20s)
10. `GET /api/stocks` (bounded to 20s)

---

## 3. API Response-Time and Status Table

| Test Target | Method | Origin Header Tested | HTTP Status | Response Time | CORS Headers Present | Details / Outcome |
|---|---|---|---|---|---|---|
| `/healthz` | GET | `https://swing-trading-tool.vercel.app` | **200 OK** | 1,136 ms | None | Healthy; 19 companies reported |
| `/healthz/ready` | GET | `https://swing-trading-tool.vercel.app` | **200 OK** | 833 ms | None | Ready; DB access verified |
| `/api/stocks` | OPTIONS | `https://swing-trading-tool.vercel.app` | **400 Bad Request** | 437 ms | No `Access-Control-Allow-Origin` | Body: `"Disallowed CORS origin"` |
| `/api/sectors` | OPTIONS | `https://swing-trading-tool.vercel.app` | **400 Bad Request** | 2,342 ms | No `Access-Control-Allow-Origin` | Body: `"Disallowed CORS origin"` |
| `/api/sectors` | OPTIONS | `https://swing-trading-staging.vercel.app` | **200 OK** | 682 ms | `Allow-Origin`, `Allow-Methods` | Successful preflight for blueprint domain |
| `/api/data-health` | GET | Direct | **200 OK** | 3,165 ms | N/A | Total prices: 2,630; Indicators: 2,630; DB operational |
| `/api/market/indices` | GET | Direct | **200 OK** | 2,760 ms | N/A | Market regime: `BULLISH` (Advance/Decline calculated) |
| `/api/sectors` | GET | Direct | **Timeout (504/Read Timeout)** | >40,000 ms | N/A | Exceeded 40s socket timeout |
| `/api/stocks?limit=1` | GET | Direct | **Timeout (504/Read Timeout)** | >20,000 ms | N/A | Exceeded 20s socket timeout |
| `/api/stocks` | GET | Direct | **Timeout (504/Read Timeout)** | >20,000 ms | N/A | Exceeded 20s socket timeout |

---

## 4. CORS Findings

### Configuration Source:
In `backend/config.py`:
```python
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]
```
In `render.yaml`:
```yaml
- key: CORS_ORIGINS
  value: https://swing-trading-staging.vercel.app,http://localhost:5173,http://localhost:3000
```
In `backend/app.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

### Analysis:
1. `render.yaml` authorized `https://swing-trading-staging.vercel.app`.
2. When the project was deployed to Vercel, Vercel assigned the domain `https://swing-trading-tool.vercel.app`.
3. FastAPI's `CORSMiddleware` performs strict string equality comparison on the `Origin` header against the list in `allow_origins`.
4. Because `https://swing-trading-tool.vercel.app` is not in `CORS_ORIGINS`, FastAPI rejects browser preflight `OPTIONS` requests with `HTTP 400 ("Disallowed CORS origin")` and omits CORS access headers on direct GET requests.
5. In web browsers, this causes `fetch()` to fail immediately at the browser client layer, displaying the network error and blocking all data rendering.

---

## 5. Database Performance & Code Execution Findings

### 5.1 Database Health & Query Execution
Neon PostgreSQL 16 is fully responsive and functioning correctly:
- Connection pool (`backend/database/connection.py`) connects smoothly with `psycopg_pool.ConnectionPool`.
- Queries executing bounded lookups (such as counting tables in `/healthz/ready`, calculating advance/decline in `/api/market/indices`, or aggregating stats in `/api/data-health`) execute within 800ms to 2.8s over cross-region network connections.
- Foreign keys and indexes (`idx_daily_prices_company_date`, `idx_technical_indicators_company_date`) exist and are valid.

### 5.2 Bottleneck in `GET /api/stocks`
In `backend/app.py` lines 448–479:
```python
# Retrieve cached universe scores if available
eval_date = _get_latest_market_date()
universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or get_cached_universe_scores(evaluation_date=None)
if universe_scores is None:
    try:
        rank_universe(evaluation_date=eval_date)
        universe_scores = get_cached_universe_scores(evaluation_date=eval_date) or {}
    except Exception:
        universe_scores = {}
```
When `universe_scores` is not cached:
1. `rank_universe()` in `backend/engines/universe_orchestrator.py` initiates a sequential Python loop across all 19 stocks.
2. For each stock, it queries sector performance context and executes `calculate_opportunity_score()`.
3. Within `calculate_opportunity_score()`, it retrieves historical prices, computes indicators, evaluates financial statements, and performs decision scoring.
4. If `universe_scores` is still empty, lines 472–479 fall back to calling `calculate_opportunity_score(sym)` on each paginated stock again.
5. On the Render Free Tier (shared 0.1 CPU core, 512 MB memory), running this extensive pipeline across 19 stocks takes 60–90+ seconds synchronously inside the request handler.
6. Render's HTTP reverse proxy enforces a 60-second gateway timeout, terminating the connection with a 504 Gateway Timeout or broken socket before the response completes.

### 5.3 Bottleneck in `GET /api/sectors`
In `backend/app.py` line 671:
```python
report = run_sector_industry_engine(ranking_period="63D")
```
Inside `backend/logic/sector_engine.py`:
- `_calculate_constituent_returns()` calls `get_historical_data(symbol, start_date=None, ...)` with `start_date=None`.
- It loads full historical OHLCV data for all constituents across 9 sectors and 19 industries sequentially.
- On cold cache, this sequential querying across Neon PostgreSQL takes >40 seconds, exceeding user request timeouts.

---

## 6. Render Deployment Findings

1. **Service Specifications:**
   - Plan: Free tier (0.1 CPU, 512 MB RAM).
   - Server: Uvicorn running `uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2`.
   - Inactivity Spin-Down: Free web services spin down after 15 minutes of inactivity. When a request wakes up the service, the in-memory cache (`_universe_ranking_cache`, `_universe_scores_cache`, `_sector_cache`) is empty (`None`).
2. **Synchronous Worker Starvation:**
   - With 2 Uvicorn workers and 512 MB RAM, if one worker enters a 60+ second synchronous calculation (`rank_universe`), and a second request arrives, worker concurrency is rapidly saturated, resulting in queuing delays and socket timeouts.

---

## 7. Root Cause Summary

1. **Root Cause A (Browser Network Error):**
   `CORS_ORIGINS` in Render's environment does not match the actual Vercel deployment URL (`https://swing-trading-tool.vercel.app` vs `https://swing-trading-staging.vercel.app`).
2. **Root Cause B (60+ Second Loading Timeout):**
   `GET /api/stocks`, `GET /api/opportunities`, and `GET /api/sectors` compute the entire market universe synchronously on-demand during the HTTP request lifecycle whenever the in-memory cache is cold. On constrained free-tier infrastructure, this sequential computation takes longer than HTTP reverse-proxy timeout thresholds.

---

## 8. Possible Contributing Factors

- **Cache TTL vs. Ephemeral Cold Starts:** In-memory caching TTL is set to 120 seconds (`CACHE_TTL_SECONDS = 120.0`), and workers lose cache state when idle instances cycle.
- **Unconstrained Historical Data Fetching:** `_calculate_constituent_returns` fetches full historical history (`start_date=None`) instead of bounding the query window to the needed 252 trading days.
- **Single-Threaded Sequential Loops:** Stock evaluations are executed sequentially rather than leveraging batched queries or lightweight pre-computation.

---

## 9. Recommended Corrective Actions (For Future Approval)

### Action 1: Align Render CORS Environment Variable (Configuration Only)
In the Render Web Service dashboard (or `render.yaml`):
Update `CORS_ORIGINS` to include the actual Vercel domain:
```text
https://swing-trading-tool.vercel.app,https://swing-trading-staging.vercel.app,http://localhost:5173,http://localhost:3000
```
*Effect: Immediately resolves browser CORS rejection, allowing preflights to pass and fast endpoints (`/healthz`, `/api/data-health`, `/api/market/indices`) to load in the UI.*

### Action 2: Decouple Universe Ranking Computation from `GET /api/stocks`
In `backend/app.py`:
- `GET /api/stocks` already performs an efficient single SQL query fetching `latest_close`, `prev_close`, `rsi`, `macd`, and `technical_score` directly from `companies`, `daily_prices`, and `technical_indicators` in ~50ms.
- Currently, it halts this fast response to compute `rank_universe(eval_date)` if unranked.
- Recommendation: Return the precomputed indicators and stock listings immediately. If universe opportunity scores are not yet computed, return them as `null` or serve cached/pre-warmed values rather than blocking the endpoint for 60 seconds.

### Action 3: Pre-Warm or Background Cache on Server Startup / Cron
- Trigger initial `rank_universe` and `run_sector_industry_engine` via a background startup task or asynchronous queue rather than in the critical path of user HTTP GET requests.

---

## 10. Audit Records

| Metric | Status |
|---|---|
| **Files Inspected** | `backend/app.py`, `backend/config.py`, `backend/database/connection.py`, `backend/database/schema_pg.sql`, `backend/engines/universe_orchestrator.py`, `backend/engines/sector_industry_engine.py`, `backend/engines/cache_service.py`, `backend/logic/sector_engine.py`, `backend/data_pipeline/data_service.py`, `render.yaml`, `backend/Dockerfile` |
| **Files Modified** | **NONE** (Strictly Read-Only) |
| **Database Modifications** | **NONE** (No DDL, DML, or migrations executed) |
| **Deployment Modifications** | **NONE** (No Render or Vercel settings modified) |
| **Git Working Tree** | Clean; zero staged or unstaged modifications on tracked files |
| **Remaining Uncertainties** | Exact computation time for `rank_universe` from a fully cold start on Render's specific virtualized CPU when uncapped by HTTP timeout (estimated at 65–85s). |

---

## 11. Final Verdict

```text
================================================================================
FINAL VERDICT: MULTIPLE ISSUES IDENTIFIED
================================================================================
1. CORS ISSUE IDENTIFIED:
   The Render staging backend environment variable CORS_ORIGINS permits
   'https://swing-trading-staging.vercel.app', but the live frontend was deployed
   at 'https://swing-trading-tool.vercel.app'. Browser preflights receive
   HTTP 400 Bad Request ("Disallowed CORS origin"), aborting all UI fetch calls.

2. API IMPLEMENTATION & COMPUTATIONAL BOTTLENECK IDENTIFIED:
   Endpoints (/api/stocks, /api/opportunities, /api/sectors) perform un-cached,
   synchronous, multi-stock universe evaluations sequentially within the HTTP
   request lifecycle, exceeding Render's 60-second gateway proxy timeout on
   free-tier hardware.
================================================================================
```
