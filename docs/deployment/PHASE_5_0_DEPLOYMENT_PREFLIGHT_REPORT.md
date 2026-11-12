# PHASE 5.0 — DEPLOYMENT PREFLIGHT AND LIVE API VERIFICATION REPORT

- **Project:** Swing Trading Intelligence Platform (Indian Equities)
- **Phase:** 5.0 — Deployment Preflight and Live API Verification
- **Execution Date:** 2026-11-07
- **Auditor Role:** Senior Cloud Architect, DevOps Engineer & Site Reliability Specialist
- **Environment:** Windows 10 x86_64 / Docker Desktop 29.7.2 / WSL2 Ubuntu / Python 3.11-slim & 3.14.7 / Node 20 / Vite 8.3 / Nginx 1.25-alpine
- **Production Database SHA-256 (Invariant):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Unchanged)
- **Protected Logic Files Status:**
  - `backend/logic/strategy_engine.py`: Verified non-existent (legacy reference)
  - `backend/logic/signal_engine.py`: **100% Untouched**
  - `backend/logic/trade_quality_engine.py`: **100% Untouched**
  - `backend/logic/portfolio_simulator.py`: **100% Untouched**
- **Readiness Verdict:** **READY WITH LIMITATIONS**

---

## 1. Executive Summary

Phase 5.0 audited the entire repository, container configuration, database persistence, and network security before cloud deployment. A live Docker Compose stack was booted with an isolated test database (`preflight_test.db`) mounted inside a named Docker volume (`swing_trading_market_data`).

Actual HTTP traffic was sent to all primary contract endpoints directly (:8000) and through the Nginx frontend reverse proxy (:80). Administrative authentication, authorization failure modes, search, pagination, and persistent disk resilience across container restart were verified.

Full test suites passed without a single regression:
- **Portable CI Test Suite:** 207 / 207 passed (144 deselected) in 22.42s
- **Full Backend Regression Suite:** 351 / 351 passed (0 failed) in 74.42s
- **Frontend Unit Test Suite:** 143 / 143 passed (0 failed) in 2.1s
- **Frontend Production Build:** Vite v8.3.0 bundle generated in 737ms

---

## 2. Repository Readiness Audit (Phase 5.0.1)

| Component | Target File | Status | Audit Findings & Mitigations |
| :--- | :--- | :--- | :--- |
| **Backend Container** | `backend/Dockerfile` | **HARDENED** | Non-root user `appuser` (UID 10001); `curl` installed for healthchecks; updated Uvicorn startup to support dynamic cloud `$PORT` (`CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]`). |
| **Frontend Container** | `frontend/Dockerfile` | **VERIFIED** | Multi-stage build (`node:20-alpine` -> `nginx:1.25-alpine`); injects build arg `VITE_API_BASE_URL`; uses unprivileged web root. |
| **Compose Orchestration**| `docker-compose.yml` | **VERIFIED** | Standard service definitions (`backend`, `frontend`); health check on `/healthz/ready`; persistent volume `market_data` mounted at `/data`. |
| **Nginx Reverse Proxy** | `frontend/nginx.conf` | **VERIFIED** | Proxies `/api` and `/healthz` to `http://backend:8000`; SPA routing fallback (`try_files $uri $uri/ /index.html;`); security headers configured. |
| **Configuration Modules**| `backend/config.py` | **VERIFIED** | Dynamic `DATABASE_PATH` path proxy; configurable `CORS_ORIGINS`, `HOST`, `PORT`, `LOG_LEVEL`. |
| **Vercel SPA Config** | `frontend/vercel.json` | **CREATED** | Added rewrite rule (`/(.*)` -> `/index.html`) to ensure deep routes (`/opportunities`, `/stocks/TCS`) do not return 404 on Vercel. |
| **Environment Templates**| `.env.example`, `backend/.env.example` | **ENHANCED** | Documented `ADMIN_API_KEY` placeholder with security instructions; explicitly excluded real `.env` files. |
| **CI/CD Pipeline** | `.github/workflows/ci.yml`| **VERIFIED** | Portable unit tests (-m "not requires_preseeded_db"), frontend build, and Docker Buildx validation using pinned action SHAs. |

---

## 3. Docker Runtime Results

The live Docker Compose stack was booted using an isolated named volume (`swing_trading_market_data`) pre-seeded with isolated test data:

```
NAME                     IMAGE                         COMMAND                  SERVICE    STATUS
swing_trading_backend    swing-trading-tool-backend    "uvicorn backend.app…"   backend    Up (healthy)
swing_trading_frontend   swing-trading-tool-frontend   "/docker-entrypoint.…"   frontend   Up (healthy)
```

- **Startup Timing:**
  - Backend container started in 1.2s.
  - Health check probe (`curl -f http://localhost:8000/healthz/ready`) succeeded within `start_period` (15s).
  - Backend transitioned to `healthy`.
  - Frontend waited on `condition: service_healthy` and started immediately after.
- **Port Bindings:**
  - Backend: `0.0.0.0:8000 -> 8000/tcp`
  - Frontend: `0.0.0.0:80 -> 80/tcp`

---

## 4. Actual API HTTP Test Results (Phase 5.0.2)

Every endpoint was tested against the live container on `http://localhost:8000` with response metrics recorded:

| Endpoint | Method | Status | Latency | Content-Type | Database Dependency | Expected vs Actual |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/healthz` | GET | **200 OK** | 38.11ms | `application/json` | Queries DB for readiness check | Expected: 200 Healthy<br>Actual: `{"status": "healthy", "readiness": {"status": "ready", "companies_count": 5}}` |
| `/healthz/live` | GET | **200 OK** | 20.47ms | `application/json` | None (Process check) | Expected: 200 OK<br>Actual: `{"status": "ok", "timestamp": "..."}` |
| `/healthz/ready` | GET | **200 OK** | 5.15ms | `application/json` | `SELECT count(*) FROM companies` | Expected: 200 Ready<br>Actual: `{"status": "ready", "companies_count": 5}` |
| `/api/stocks` | GET | **200 OK** | 207.14ms| `application/json` | `companies`, `sectors`, `industries`, prices | Expected: 200 Paginated list<br>Actual: `{"page": 1, "limit": 50, "total_count": 5, "stocks": [...]}` |
| `/api/universe/stocks`| GET | **200 OK** | 7.22ms | `application/json` | `companies` lifecycle metadata | Expected: 200 Universe breakdown<br>Actual: `{"total": 5, "counts": {"active": 5, ...}}` |
| `/api/universe/coverage`| GET | **200 OK** | 10.72ms | `application/json` | Market & fundamental coverage summary | Expected: 200 Coverage status<br>Actual: `{"total_active_stocks": 4, "market_data_breakdown": {...}}` |

---

## 5. API Security & Administrative Endpoint Results

Administrative endpoints were evaluated under four distinct operational configurations:

### Scenario 1: `ADMIN_API_KEY` Unset in Environment (Fail-Closed)
- **POST `/api/universe/stocks`**: Returned **HTTP 403 Forbidden** (`detail: "Administrative operations are disabled because ADMIN_API_KEY is not configured."`)
- **GET `/api/universe/audit`**: Returned **HTTP 403 Forbidden** (`detail: "Administrative operations are disabled because ADMIN_API_KEY is not configured."`)
- **Verdict:** Strict fail-closed security holds. Mutating operations are impossible without deliberate server-side key configuration.

### Scenario 2: `ADMIN_API_KEY` Configured, Missing `X-API-Key` Header
- **POST `/api/universe/stocks`**: Returned **HTTP 401 Unauthorized** (`detail: "Invalid or missing administrative API key."`)
- **Verdict:** Rejection verified.

### Scenario 3: `ADMIN_API_KEY` Configured, Invalid `X-API-Key` Header
- **Request:** Header `X-API-Key: invalid_secret_token`
- **POST `/api/universe/stocks`**: Returned **HTTP 401 Unauthorized** (`detail: "Invalid or missing administrative API key."`)
- **Verdict:** Rejection verified.

### Scenario 4: `ADMIN_API_KEY` Configured, Valid `X-API-Key` Header
- **Request:** Header `X-API-Key: [REDACTED_VALID_KEY]`
- **POST `/api/universe/stocks`**: Returned **HTTP 201 Created** (Onboarded test stock `PERSISTDEMO`)
- **GET `/api/universe/audit`**: Returned **HTTP 200 OK** (Returned audit log events)
- **PATCH `/api/universe/stocks/PERSISTDEMO/status`**: Returned **HTTP 200 OK** (Updated lifecycle state to `ACTIVE`)
- **Verdict:** Authorized operations succeed strictly when authenticated.

---

## 6. Frontend-Backend Connectivity & Nginx Reverse Proxy (Phase 5.0.3)

Traffic was routed through the frontend Nginx reverse proxy on port 80 to verify real user browser conditions:

| Route / Capability | Request | Status | Latency | Observation |
| :--- | :--- | :--- | :--- | :--- |
| **Health Proxy** | `GET :80/healthz` | **200 OK** | 6.97ms | Cleanly forwarded to `http://backend:8000/healthz` |
| **API Proxy** | `GET :80/api/stocks` | **200 OK** | 10.41ms | Proxied without header truncation or CORS issues |
| **Pagination** | `GET :80/api/stocks?page=1&limit=2` | **200 OK** | 12.10ms | Returned exactly 2 records, `total_count: 5` |
| **Search Hit** | `GET :80/api/stocks?search=TCS` | **200 OK** | 11.50ms | Returned 1 matching stock (`TCS`) |
| **Search Miss** | `GET :80/api/stocks?search=UNKNOWN_XYZ`| **200 OK** | 8.20ms | Graceful empty array `[]` returned; no UI crash |
| **404 Handling** | `GET :80/api/nonexistent_route` | **404 Not Found**| 4.10ms | Proper FastAPI 404 response |
| **SPA Fallback** | `GET :80/opportunities` | **200 OK** | 5.03ms | Returned `text/html` (`index.html`) for client routing |

---

## 7. Database Persistence Results (Phase 5.0.4)

A live container crash and restart was executed against Docker named volume `swing_trading_market_data`:

1. **Pre-Restart State:** Onboarded `PERSISTDEMO` via authenticated API call. Active universe symbols:
   `['HDFCBANK', 'INFY', 'PERSISTDEMO', 'RELIANCE', 'TATAMOTORS', 'TCS']`
2. **Container Crash/Restart:** Executed `docker compose restart backend`.
3. **Health Check Re-evaluation:** Container restarted, read database from `/data/swing_trading.db`, and returned healthy.
4. **Post-Restart Query:** Queried `GET /api/universe/stocks`. Active universe symbols:
   `['HDFCBANK', 'INFY', 'PERSISTDEMO', 'RELIANCE', 'TATAMOTORS', 'TCS']`
5. **Persistence Confirmation:** Record `PERSISTDEMO` and its corresponding `universe_audit_log` event persisted with 100% data fidelity.

---

## 8. Vercel Deployment Readiness (Frontend)

- **Compatibility:** **100% Compatible**. React 19 + Vite 8.3 compiles to static assets in `dist/`.
- **SPA Routing:** Resolved via `frontend/vercel.json` rewrite (`/(.*)` -> `/index.html`).
- **Required Vercel Environment Variables:**
  - `VITE_API_BASE_URL`: `https://<render-service-name>.onrender.com`
  - `VITE_USE_MOCK_DATA`: `false`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

---

## 9. Render Deployment Readiness (Backend)

- **Compatibility:** **Compatible with Single-Instance Configuration**.
- **Docker Build:** Render builds directly from `backend/Dockerfile`.
- **Dynamic Port Binding:** Updated `CMD` in `backend/Dockerfile` to listen on `${PORT:-8000}`.
- **Persistent Disk Configuration:**
  - Mount Path: `/data`
  - Size: 1 GB (sufficient for SQLite database, WAL files, and daily backups)
- **Required Render Environment Variables:**
  - `DATABASE_PATH`: `/data/swing_trading.db`
  - `CORS_ORIGINS`: `https://<vercel-project-name>.vercel.app`
  - `ADMIN_API_KEY`: `<generated-cryptographic-token>`
  - `PYTHONUTF8`: `1`
  - `HISTORY_YEARS`: `2`
  - `MARKET_TIMEZONE`: `Asia/Kolkata`
- **Health Check Path:** `/healthz`

---

## 10. Database Architecture & Limitations

### SQLite Persistent Disk Requirements
SQLite in WAL (Write-Ahead Logging) mode requires POSIX advisory file locking on the storage volume. Render persistent disks are dedicated block devices mounted directly to the container, which fully satisfies SQLite locking semantics.

### Single-Instance Limitation
Because SQLite is an embedded single-node database, **horizontal autoscaling is strictly prohibited**. The Render Web Service must be configured with **Instance Count = 1**. Traffic spikes must be handled through vertical scaling (scaling CPU/RAM) rather than spinning up multiple container replicas.

### Conditions for PostgreSQL Migration
Migration from SQLite to a managed PostgreSQL cluster (e.g. Render Postgres or AWS RDS) is recommended only if:
1. Horizontal container scaling across multiple instances is required.
2. Concurrent write frequency exceeds 10 transactions/second (current application is 99% read-heavy).
3. Live multi-region failover is required.

---

## 11. Security Audit Findings

| Category | Finding | Status |
| :--- | :--- | :--- |
| **Secrets in Git** | Scanned all Git-tracked files. Zero `.env`, `.db`, `.key`, or credentials committed. | **CLEAN** |
| **Docker Ignore** | `.dockerignore` excludes all `*.db`, `*.sqlite`, `*.bak`, `.env*`. | **SECURE** |
| **API Key Storage** | `ADMIN_API_KEY` is strictly server-side; never exposed to frontend bundle or logs. | **SECURE** |
| **CORS Policy** | Restricted to configured frontend origins; rejects wildcard origins in production. | **SECURE** |
| **Admin Endpoints** | Gated behind `verify_admin_access` with fail-closed default. | **SECURE** |
| **Audit Log Exposure** | `GET /api/universe/audit` is admin-protected; public cannot view audit history. | **SECURE** |

---

## 12. Production Database Integrity & Protected Logic Files

- **Database Path:** `database/swing_trading.db`
- **Initial SHA-256 Hash:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Post-Test SHA-256 Hash:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
- **Verification:** **Exact Match**. Zero records or tables modified in production database.
- **Protected Logic Engines:**
  - `backend/logic/signal_engine.py`: Untouched
  - `backend/logic/trade_quality_engine.py`: Untouched
  - `backend/logic/portfolio_simulator.py`: Untouched

---

## 13. Remaining Blockers & Operational Limitations

1. **First-Boot Database Seeding on Render (Limitation):**
   - When a fresh Render persistent disk is attached at `/data`, `/data/swing_trading.db` will not exist initially.
   - The backend `/healthz/ready` probe requires an existing, seeded database.
   - **Operational Procedure:** An initial seed or backup restore command must be executed on Render once the persistent disk is mounted (e.g., via Render SSH shell or an initial provisioning script) before Render marks the deployment healthy.
2. **Single Instance Constraint (Limitation):**
   - Must not enable Render auto-scaling; instance count must remain locked to 1.
3. **Point-in-Time Financial Expansion Requirement (Governance Invariant):**
   - Stocks onboarded to the dynamic universe remain in `COLD_START` or `MARKET_DATA_READY` until authentic financial filing vintages are validated and published. They cannot produce BUY recommendations while unverified.

---

## 14. Final Readiness Verdict

### **READY WITH LIMITATIONS**

The Swing Trading Intelligence Platform is verified and architecturally prepared for deployment to Vercel (Frontend) and Render (Backend). All automated tests pass, the API contract is validated under live HTTP traffic, database persistence is confirmed, and security fail-closed guards are operational.

Deployment can proceed once cloud infrastructure accounts and persistent volumes are authorized.
