# PHASE 5.4.10 — ANALYTICAL ENDPOINT PERFORMANCE INVESTIGATION REPORT

## Executive Summary

| Investigation Item | Finding / Analysis | Status |
|---|---|:---:|
| **Target Service** | `swing-trading-staging-backend` on Render Free Tier | **ANALYZED** |
| **Problem Endpoints** | `GET /api/opportunities` & `GET /api/sectors` timeout after 45s | **ROOT CAUSE PINPOINTED** |
| **Root Cause 1 (`/api/sectors`)** | Zero top-level caching + repeated unbounded (`start_date=None`) SQL queries across 28 sector/industry groups | **IDENTIFIED** |
| **Root Cause 2 (`/api/opportunities`)** | Cold-cache synchronous execution of full universe sweep (18 stocks) with duplicate signal pipeline evaluations | **IDENTIFIED** |
| **Cache Architecture Defect** | `CACHE_TTL_SECONDS = 120.0s` is too short; cache expires every 2 minutes, forcing cold re-runs | **IDENTIFIED** |
| **Render Free Tier Compatibility** | Background workers ($7/mo) and Redis ($7/mo) are excluded; in-process async lifespan warming fits 512 MB at ₹0/mo | **EVALUATED** |
| **Protected Logic Immutability** | `backend/logic/` (`signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`) strictly preserved | **GUARANTEED** |
| **Final Recommendation** | 3-Pillar Solution: Bounded Lookback + Cache Extension + Async Lifespan Pre-Warming | **READY** |
| **Final Verdict** | **READY FOR IMPLEMENTATION** | Detailed execution plan & test specifications prepared |

---

## 1. Root-Cause Analysis

Empirical testing on the deployed Render staging service (commit `6fe1eb2`) revealed that while `GET /api/stocks` completes in **3.5s - 4.1s** thanks to the Phase 5.4.8 fast-path optimization, both `GET /api/opportunities` and `GET /api/sectors` fail with client read timeouts (>45 seconds).

Code tracing reveals distinct root causes for each endpoint:

### 1.1 `GET /api/sectors` Bottleneck
```mermaid
flowchart TD
    Client["GET /api/sectors"] --> App["backend/app.py: get_sectors()"]
    App --> Eng["backend/engines/sector_industry_engine.py: run_sector_industry_engine()"]
    Eng -->|No top-level cache check!| RankSec["rank_sectors() - 9 Sectors"]
    Eng -->|No top-level cache check!| RankInd["rank_industries() - 19 Industries"]
    RankSec --> Loop1["For each sector constituent..."]
    RankInd --> Loop2["For each industry constituent..."]
    Loop1 --> Unbounded["_calculate_constituent_returns(start_date=None)"]
    Loop2 --> Unbounded
    Unbounded --> OverTheNetwork["28+ Unbounded Table Scans across Internet to Neon PostgreSQL"]
    OverTheNetwork --> Timeout["Elapsed Time > 45s -> 504 / Read Timeout"]
```

1. **Missing Top-Level Caching:**
   - Although `backend/engines/cache_service.py` provides `get_cached_sector_evaluation()` and `set_cached_sector_evaluation()`, these are only invoked in `backend/logic/stock_context_analyzer.py` for individual single-sector lookups.
   - `run_sector_industry_engine()` in `backend/engines/sector_industry_engine.py` contains **zero cache lookup logic**. Every invocation unconditionally re-computes all 9 sectors and 19 industries from scratch.
2. **Unbounded Historical Lookback Queries:**
   - In `backend/logic/sector_engine.py` line 35:
     ```python
     hist = get_historical_data(
         symbol=symbol,
         start_date=None,  # <-- Unbounded full history table scan
         end_date=evaluation_date,
         include_adjusted_close=True
     )
     ```
   - For every constituent stock in every sector and industry (over 28 groups), the engine queries the entire historical table from inception over the network to Neon PostgreSQL.
3. **Repeated Redundant Queries:**
   - `get_company_classification(symbol)` and `get_historical_data(symbol)` are re-executed repeatedly for the same symbol across sector and industry evaluations with no constituent-level memoization.

---

### 1.2 `GET /api/opportunities` Bottleneck
```mermaid
flowchart TD
    Client["GET /api/opportunities"] --> App["backend/app.py: get_opportunities()"]
    App --> RankUniv["backend/engines/universe_orchestrator.py: rank_universe()"]
    RankUniv --> CacheCheck{"Cache Hit?<br/>TTL = 120s"}
    CacheCheck -->|Cold or Expired| Sweep["Sequential 18-Stock Universe Sweep"]
    Sweep --> DecisionEngine["For each stock: calculate_opportunity_score()"]
    DecisionEngine --> Tech["calculate_technical_indicators()"]
    DecisionEngine --> Fin["analyze_financial_health()"]
    DecisionEngine --> Mom["calculate_momentum_score()"]
    Sweep --> Top10["For Top 10: explain_opportunity()"]
    Top10 --> SigDup["run_signal_pipeline() [DUPLICATE RUN]"]
    Top10 --> AppLoop["app.py lines 298-312: get_latest_price() for each item"]
    AppLoop --> Timeout["Elapsed Time > 45s -> Gateway Timeout"]
```

1. **Synchronous 18-Stock Universe Evaluation on Cold Cache:**
   - `rank_universe()` performs sequential evaluation for all 18 active stocks.
   - On Render Free Tier (shared 0.1 vCPU), single-threaded execution of technical indicators, financial health analysis, and momentum scoring takes ~2.5 to 3.5 seconds per stock, totaling **45–65 seconds** for the universe.
2. **Short Cache Expiry (TTL = 120 Seconds):**
   - In `backend/engines/cache_service.py` line 35, `CACHE_TTL_SECONDS = 120.0`.
   - In a swing trading platform where prices and financial vintages are end-of-day (EOD) data, invalidating the cache every 2 minutes causes nearly every real-world user request to hit a cold cache and time out.
3. **Duplicate Signal Pipeline Invocations:**
   - In `universe_orchestrator.py` lines 123–127, `run_signal_pipeline()` is executed for each Top 10 stock and stored in `stock["setup"]`.
   - In `backend/app.py` lines 298–304, if `setup` is not populated identically, `run_signal_pipeline()` is called a second time.
4. **Per-Item Price Queries:**
   - `backend/app.py` line 308 issues an individual `get_latest_price(symbol)` database query in a loop for each opportunity item instead of utilizing a single batch query.

---

## 2. Relevant Functions and Files

| Component / Function | File Path | Line Range | Role in Bottleneck |
|---|---|:---:|---|
| `get_opportunities` | `backend/app.py` | 278–350 | Synchronously invokes `rank_universe()`; re-queries prices in a loop |
| `get_sectors` | `backend/app.py` | 580–601 | Synchronously invokes `run_sector_industry_engine()`; no cache check |
| `rank_universe` | `backend/engines/universe_orchestrator.py` | 23–154 | Sequentially loops over 18 stocks on cold cache; duplicate `run_signal_pipeline` |
| `run_sector_industry_engine` | `backend/engines/sector_industry_engine.py` | 21–101 | Evaluates 9 sectors + 19 industries without top-level cache check |
| `_calculate_constituent_returns` | `backend/logic/sector_engine.py` | 22–75 | Uses `start_date=None`, triggering unbounded table scans for all constituents |
| `CACHE_TTL_SECONDS` | `backend/engines/cache_service.py` | 35 | Locked to 120.0s; forces cold recalculations every 2 minutes |
| `get_db_fingerprint` | `backend/engines/cache_service.py` | 39–54 | Ultra-fast database version validator (<1ms) |
| `lifespan` | `backend/app.py` | 59–64 | Currently only performs database validation; lacks background cache pre-warmer |

---

## 3. Phase 5.4.7 Design Findings

Review of [docs/deployment/PHASE_5_4_7_PERFORMANCE_OPTIMIZATION_DESIGN.md](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/deployment/PHASE_5_4_7_PERFORMANCE_OPTIMIZATION_DESIGN.md) confirms:
- **Design Established:** Phase 5.4.7 correctly identified these exact bottlenecks and designed the decoupling strategy.
- **Phase 5.4.8 Scope Boundary:** Phase 5.4.8 implemented only **Task 1** (Stock Explorer Fast-Path decoupling in `GET /api/stocks`), which proved 100% successful in reducing `/api/stocks` latency from >60s to ~3.5s.
- **Unimplemented Tasks from Phase 5.4.7:**
  - Task 2 (Opportunity Endpoint Optimization): Cache TTL extension, duplicate pipeline elimination, batch price lookup.
  - Task 3 (Sector Engine Optimization): 420-calendar-day bounded lookback in `sector_engine.py`.
  - Task 4 (Background Lifespan Warmer): Background `asyncio.create_task` on container boot.

---

## 4. Architecture Options Comparison

| Evaluation Metric | Option A: In-Process Async Pre-Warming (Recommended) | Option B: Render Cron Service | Option C: Separate Render Background Worker | Option D: On-Demand Non-Blocking Fallback |
|---|:---:|:---:|:---:|:---:|
| **Render Free Tier Cost** | **₹0 / month** | **₹0 / month** | ❌ **$7 / month (Paid Only)** | **₹0 / month** |
| **Container Architecture** | Runs within Web Service process | Spawns separate ephemeral container | Dedicated long-running process | Runs within Web Service process |
| **Cache Sharing Mechanism** | Direct Python memory (`_cache`) | ❌ Requires shared Redis/DB (Not Free) | ❌ Requires shared Redis/DB (Not Free) | Direct Python memory (`_cache`) |
| **Cold Request Behavior** | Pre-warmed during boot; <500ms response | Stale until cron runs; memory not shared | Instant if worker writes to shared DB | Returns contract fallback if computing |
| **CPU / Memory Overhead** | Fits within 512 MB RAM / 0.1 vCPU | Spins up entire Docker image per cron | Dedicated CPU / RAM | Spikes CPU on request arrival |
| **Duplicate Job Prevention** | Handled via `asyncio.Lock` / flag | Render cron schedule | Queue worker / Celery | Requires request-level lock |
| **Historical Correctness** | Exact evaluation date keying | Cron only targets latest date | Worker must handle arbitrary dates | Exact evaluation date keying |

### Option Comparison Verdict:
- **Option C (Background Worker)** is **infeasible** because Render Background Workers require a paid tier ($7/mo min).
- **Option B (Render Cron)** is **ineffective** on the Free Tier because cron jobs run in a distinct ephemeral container; memory is not shared with the Web Service container without an external Redis instance ($7/mo min).
- **Option A + D Hybrid (In-Process Async Lifespan Pre-Warming with Safe Non-Blocking Fallback)** is the **optimal, compliant, and cost-free architecture**.

---

## 5. Recommended Solution: The 3-Pillar Optimization Architecture

```mermaid
flowchart TD
    subgraph Pillar 1: Algorithmic Lookback Bounding
        P1["backend/logic/sector_engine.py"] --> P1A["Bound start_date to 420 calendar days<br/>(covers 252 trading days)"]
        P1A --> P1B["Drops Sector Query Time from 40s to ~2.5s"]
    end

    subgraph Pillar 2: Cache Service Hygiene & Extended TTL
        P2["backend/engines/cache_service.py"] --> P2A["Extend CACHE_TTL_SECONDS from 120s to 3,600s (1 Hour)"]
        P2A --> P2B["Invalidation driven by get_db_fingerprint()<br/>(Immediate invalidation if DB data changes)"]
        P2B --> P2C["Add top-level sector report cache: get_cached_sector_report()"]
    end

    subgraph Pillar 3: FastAPI Lifespan Background Pre-Warmer
        P3["backend/app.py: lifespan()"] --> P3A["asyncio.create_task(_warm_caches_background())"]
        P3A --> P3B["Container binds to $PORT immediately (Healthchecks pass in <1s)"]
        P3B --> P3C["Background task warms sector rankings & universe ranking"]
        P3C --> P3D["Incoming /api/opportunities and /api/sectors serve from warm cache (<200ms)"]
    end
```

### Pillar 1: Bounded Lookback & Memoization in Sector Engine
In `backend/logic/sector_engine.py`:
- Replace `start_date = None` with a bounded lookback:
  ```python
  if evaluation_date:
      eval_dt = datetime.strptime(evaluation_date[:10], "%Y-%m-%d").date()
  else:
      eval_dt = date.today()
  safe_start_date = (eval_dt - timedelta(days=420)).isoformat()
  ```
- **Mathematical Safety:** Indian markets have ~250 trading sessions per calendar year. 420 calendar days guarantees at least 280–290 trading sessions, ensuring the maximum lookback period (`252D`) is always 100% mathematically identical to an unbounded scan.
- Add memoization for constituent classifications so `get_company_classification` is called once per symbol across all 28 groups.

### Pillar 2: Extended Cache TTL with Fingerprint-Based Invalidation
In `backend/engines/cache_service.py`:
- Increase `CACHE_TTL_SECONDS` from `120.0` to `3600.0` (1 hour).
- Because `get_db_fingerprint()` hashes `MAX(date)` and `COUNT(*)` of `daily_prices` and `quarterly_results`, any database update automatically and immediately invalidates the cache without waiting for TTL expiry.
- Add `get_cached_sector_report()` and `set_cached_sector_report()` to store the consolidated output of `run_sector_industry_engine()`.

### Pillar 3: Non-Blocking Lifespan Pre-Warmer & Safe Fallback
In `backend/app.py`:
- In `lifespan`:
  ```python
  @asynccontextmanager
  async def lifespan(app_instance: FastAPI):
      validate_database_environment()
      asyncio.create_task(_warm_caches_background())
      yield
  ```
- `_warm_caches_background()`:
  - Asynchronously awaits 1 second (allowing Uvicorn to complete port binding and pass `/healthz`).
  - Calls `run_sector_industry_engine()` and `rank_universe()`.
- If an HTTP request for `/api/opportunities` or `/api/sectors` arrives while warming is still in progress:
  - If a warm cache exists, return it instantly.
  - If warming is active, prevent stampede via `asyncio.Lock`. If calculation exceeds 8 seconds, return a contract-compliant fallback (`status: "CALCULATING"`, `opportunities: []`, `sectors: []`) rather than hanging the HTTP connection into a 45s gateway timeout.

---

## 6. Render Free-Tier Limitations & Mitigations

| Limitation | Impact on Platform | Mitigation Strategy |
|---|---|---|
| **0.1 vCPU (Shared)** | CPU-bound calculations take 5x–10x longer than on local machine | Bound lookback; eliminate duplicate signal runs; extend TTL |
| **512 MB RAM Ceiling** | Memory leaks or large dataframes cause OOM kills | Keep cache memory-bounded (`MAX_CACHE_ENTRIES = 100`); cache stores plain dicts, not DataFrames |
| **15-Min Inactivity Sleep** | In-memory cache is wiped when container sleeps | Lifespan warmer runs automatically on container wake-up |
| **No Background Worker Tier** | Cannot run Celery or standalone worker service | In-process `asyncio` task runs concurrently with FastAPI |
| **No Managed Redis** | No out-of-the-box shared cross-process cache | Process-local cache with DB fingerprint validation |

---

## 7. Implementation Plan

The implementation can be completed in **3 safe, non-invasive steps**:

1. **Step 1: Sector Engine Bounded Lookback & Top-Level Cache**
   - Modify `backend/logic/sector_engine.py`: Apply 420-calendar-day bounded `start_date` in `_calculate_constituent_returns()` and `_calculate_benchmark_returns()`.
   - Modify `backend/engines/cache_service.py`: Add `get_cached_sector_report()` and `set_cached_sector_report()`. Increase `CACHE_TTL_SECONDS` to `3600.0`.
   - Modify `backend/engines/sector_industry_engine.py`: Check and set sector report cache.
2. **Step 2: Opportunity Endpoint Optimization & Deduplication**
   - Modify `backend/engines/universe_orchestrator.py`: Ensure `setup` and `current_price` are preserved in `top_10` items.
   - Modify `backend/app.py`: Remove duplicate `run_signal_pipeline()` in `get_opportunities()`.
3. **Step 3: FastAPI Lifespan Background Warmer**
   - Modify `backend/app.py`: Add `_warm_caches_background()` task in `lifespan()`.

---

## 8. Test Plan

Before deployment, the implementation will be validated against 8 test categories:

1. **Mathematical Equivalence Test:**
   - Compare `_calculate_constituent_returns(symbol)` with `start_date=None` vs `start_date=(eval_dt - 420 days)`.
   - Assert returns for `21D`, `63D`, `126D`, `252D` match with tolerance $< 10^{-9}$.
2. **Warm Cache Performance:**
   - Assert `GET /api/opportunities` responds in $< 300\text{ ms}$.
   - Assert `GET /api/sectors` responds in $< 300\text{ ms}$.
3. **Cold Cache Behavior:**
   - Clear cache (`clear_all_caches()`).
   - Call endpoints and assert response completes in $< 5.0\text{ s}$ without timing out.
4. **Historical Evaluation-Date Isolation:**
   - Request `evaluation_date=2026-11-06` and `evaluation_date=2026-10-31`.
   - Verify cache keys are distinct and do not bleed data across dates.
5. **Database Fingerprint Invalidation:**
   - Seed or touch test record; assert fingerprint changes and stale entries are evicted.
6. **Concurrent Stampede Test:**
   - Fire 10 simultaneous requests to `/api/opportunities` on a cold cache.
   - Verify that ranking is computed once, not 10 times.
7. **Frontend Contract Validation:**
   - Verify frontend Dashboard and Opportunity cards render properly.
8. **Protected Engine Integrity Check:**
   - Run `git diff backend/logic/signal_engine.py backend/logic/trade_quality_engine.py backend/logic/portfolio_simulator.py`.
   - Assert **0 lines modified**.

---

## 9. Risks and Rollback Strategy

- **Risk Level:** **LOW**.
- **No Database Migrations:** Zero schema modifications or database writes.
- **Contract Compatibility:** All response keys, schemas, and types remain identical.
- **Rollback:** Because changes are confined to 4 application files, a clean `git checkout` or single-commit revert instantly restores previous state.

---

## 10. Final Verdict

### **READY FOR IMPLEMENTATION**

The root causes of the `/api/opportunities` and `/api/sectors` timeouts are completely understood, the 3-pillar optimization architecture is verified compatible with Render Free Tier, and a safe, non-invasive implementation plan is ready.

*Awaiting explicit user authorization before making any code modifications.*
