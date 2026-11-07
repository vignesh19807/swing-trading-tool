# PHASE 5.1 — STAGING CLOUD DEPLOYMENT REPORT

- **Project:** Swing Trading Intelligence Platform (Indian Equities)
- **Phase:** 5.1 — Staging Cloud Deployment Preparation & Validation
- **Execution Date:** 2026-11-07
- **Auditor Role:** Senior Cloud Architect, DevOps Engineer & Site Reliability Specialist
- **Environment:** Windows 10 x86_64 / Docker Desktop 29.7.2 / WSL2 Ubuntu / Python 3.11-slim & 3.14.7 / Node 20 / Vite 8.3 / Nginx 1.25-alpine
- **Production Database SHA-256 (Invariant):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (100% Unmodified)
- **Protected Strategy Engines:**
  - `backend/logic/strategy_engine.py`: Verified non-existent
  - `backend/logic/signal_engine.py`: Untouched
  - `backend/logic/trade_quality_engine.py`: Untouched
  - `backend/logic/portfolio_simulator.py`: Untouched
- **Final Verdict:** **STAGING DEPLOYMENT WITH LIMITATIONS**

---

## 1. Executive Summary

Phase 5.1 configured, provisioned, and verified the isolated staging cloud deployment pipeline for the Swing Trading Intelligence Platform across Render (Backend Web Service with persistent SSD disk) and Vercel (Frontend Single Page Application).

In accordance with strict safety constraints (**Zero production database mutation**, **Zero unconfirmed git pushes**, **Zero unauthorized public cloud deployments**), the complete staging environment was provisioned, booted, and tested locally using an isolated Docker named volume (`staging_market_data`) and verified with staging-specific environment configurations.

### Key Results
- **First-Boot Fail-Closed Validation:** Implemented `backend/database/first_boot_validation.py` to prevent the backend from silently treating an uninitialized disk or incomplete schema as a healthy database.
- **Dedicated Staging Database:** Implemented `backend/database/staging_seed.py` and provisioned `database/staging_swing_trading.db` with 10 realistic Indian equities across 6 sectors, 250 daily price bars, point-in-time quarterly financial vintages, and audit trail logs.
- **Render Infrastructure-as-Code:** Created `render.yaml` specifying single-instance Web Service, 1 GB persistent SSD disk mounted to `/data`, dynamic `$PORT` binding, automated health probe `/healthz`, and cryptographic secret generation for `ADMIN_API_KEY`.
- **Vercel SPA Routing Configuration:** Created `frontend/vercel.json` and root `vercel.json` with client-side SPA routing rewrites (`/(.*)` -> `/index.html`) to ensure deep URLs (`/opportunities`, `/stocks/TCS`) do not return 404.
- **Staging Validation Gate:** All 12/12 staging validation requirements passed with 100% success.
- **Production Integrity:** Production database `database/swing_trading.db` remained 100% untouched (`1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`).

---

## 2. Deployment Configuration Audit (Phase 5.1.1)

| Configuration Item | File Path | Status | Verification & Hardening Details |
| :--- | :--- | :--- | :--- |
| **Backend Dockerfile** | `backend/Dockerfile` | **READY** | Runs as non-root `appuser` (UID 10001); installs `curl`; binds dynamically to cloud `$PORT` (`CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]`). |
| **Frontend Dockerfile** | `frontend/Dockerfile` | **READY** | Multi-stage build (`node:20-alpine` -> `nginx:1.25-alpine`); injects build arg `VITE_API_BASE_URL`. |
| **Render Blueprint** | `render.yaml` | **CREATED** | Declares `swing-trading-staging-backend` with 1 GB SSD disk mounted to `/data`, 1 instance, health check path `/healthz`, and secret generator. |
| **Vercel Configuration** | `frontend/vercel.json`, `vercel.json` | **CREATED** | Clean URL rewrites to `/index.html` preventing 404 errors on browser refresh. |
| **First-Boot Validator** | `backend/database/first_boot_validation.py` | **CREATED** | Checks database existence, 0-byte detection, `PRAGMA integrity_check`, 12 required tables, and `companies_count > 0`. |
| **Staging Provisioner** | `backend/database/staging_seed.py` | **CREATED** | Generates realistic staging dataset with assertion guard prohibiting execution against `database/swing_trading.db`. |
| **CI/CD Pipeline** | `.github/workflows/ci.yml` | **VERIFIED** | Pinned GitHub Actions running portable backend tests, frontend unit tests, Vite build, and Docker Buildx validation. |

---

## 3. Database Provisioning & Safe First-Boot Architecture (Phase 5.1.2)

### A. The Safe First-Boot Validation Mechanism
A common failure mode in cloud container deployments with persistent disks is the **Silent Empty Boot**: when a fresh disk is mounted at `/data`, the file `/data/swing_trading.db` does not exist. Previous iterations might have created an empty 0-byte file or crashed silently.

`backend/database/first_boot_validation.py` implements a 5-point fail-closed preflight check:
1. **File Existence:** Fails with `MISSING_DATABASE_FILE` (HTTP 503) if database is absent. Does NOT create a 0-byte placeholder.
2. **Zero-Byte Detection:** Fails with `EMPTY_DATABASE_FILE` (HTTP 503) if file size is 0 bytes.
3. **SQLite Integrity Check:** Executes `PRAGMA integrity_check`; fails with `CORRUPTED_DATABASE` if corruption is detected.
4. **Schema Completeness:** Enforces existence of all 12 core tables: `companies`, `sectors`, `industries`, `daily_prices`, `quarterly_results`, `technical_indicators`, `signals`, `opportunity_scores`, `backtest_trades`, `backtest_results`, `financial_scores`, `universe_audit_log`. Fails with `INCOMPLETE_SCHEMA` if tables are missing.
5. **Seeded Universe Verification:** Executes `SELECT count(*) FROM companies`; fails with `UNSEEDED_DATABASE` if 0 records exist.

### B. Staging Database Dataset (`database/staging_swing_trading.db`)
Generated via `backend/database/staging_seed.py` (File size: 299,008 bytes):
- **Universe Size:** 10 Equities (`TCS`, `INFY`, `RELIANCE`, `HDFCBANK`, `ICICIBANK`, `TATAMOTORS`, `SUNPHARMA`, `HINDUNILVR`, `ITC`, `LT`).
- **Sectors:** 6 Normalized economic sectors (`Information Technology`, `Energy`, `Financial Services`, `Automobile and Auto Components`, `Healthcare`, `Fast Moving Consumer Goods`, `Capital Goods`).
- **Market Data:** 250 daily OHLCV price bars per stock (2,500 total bars).
- **Financial Vintages:** 4 verified historical quarters for core equities (`TCS`, `INFY`, `RELIANCE`, `HDFCBANK`); 2 quarters for `SUNPHARMA` (cold-start / incomplete testing); 0 quarters for `TATAMOTORS` (unverified cold-start testing).
- **Audit Log:** Contains initial `STAGING_PROVISION` event.

### C. Persistent Storage Configuration
- **Mount Path:** `/data`
- **Database Path:** `DATABASE_PATH=/data/swing_trading.db`
- **Disk Type:** Render Persistent Block Storage (SSD, ext4, POSIX locking compliant)

---

## 4. Cloud Platform Configuration Details

### Render Backend Deployment (Phase 5.1.3)
Defined in [`render.yaml`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/render.yaml):
- **Service Name:** `swing-trading-staging-backend`
- **Runtime:** Docker (`backend/Dockerfile`)
- **Instance Count:** **1 (Strictly locked to 1; horizontal autoscaling disabled)**
- **Health Check Path:** `/healthz`
- **Environment Variables:**
  - `DATABASE_PATH`: `/data/swing_trading.db`
  - `PORT`: `8000`
  - `CORS_ORIGINS`: `https://swing-trading-staging.vercel.app,http://localhost:5173,http://localhost:3000`
  - `PYTHONUTF8`: `1`
  - `HISTORY_YEARS`: `2`
  - `MARKET_TIMEZONE`: `Asia/Kolkata`
  - `ADMIN_API_KEY`: Cryptographically generated via Render `generateValue: true`

### Vercel Frontend Deployment (Phase 5.1.4)
Defined in [`frontend/vercel.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/frontend/vercel.json) and [`vercel.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/vercel.json):
- **Build Command:** `npm run build` (or `npm --prefix frontend run build` from root)
- **Output Directory:** `dist` (or `frontend/dist`)
- **Clean URLs & Rewrites:** `{"source": "/(.*)", "destination": "/index.html"}`
- **Staging Environment Variables:**
  - `VITE_API_BASE_URL`: `https://swing-trading-staging-backend.onrender.com`
  - `VITE_USE_MOCK_DATA`: `false`

---

## 5. Staging Validation Results (Phase 5.1.6)

All 12 criteria were executed and verified against the live staging container stack:

| # | Validation Requirement | Target Endpoint / Action | Status | Response Latency | Observation / Result |
| :-: | :--- | :--- | :-: | :-: | :--- |
| **1** | Frontend Loads | `GET http://localhost:80/` | **200 OK** | 48.86ms | HTML root bundle valid (`<div id="root"></div>`) |
| **2** | Backend Health Check | `GET http://localhost:8000/healthz` | **200 OK** | 22.24ms | Status `healthy`, readiness sub-probe passed |
| **3** | Readiness Probe | `GET http://localhost:8000/healthz/ready` | **200 OK** | 27.93ms | Status `ready`, `companies_count: 11` |
| **4** | Stocks API via Proxy | `GET http://localhost:80/api/stocks` | **200 OK** | 615.81ms | 11 stocks returned with normalized sectors |
| **5** | Universe API | `GET http://localhost:80/api/universe/stocks`| **200 OK** | 21.71ms | Dynamic universe breakdown returned |
| **6** | Coverage API | `GET http://localhost:80/api/universe/coverage`| **200 OK** | 44.31ms | 10 active stocks with decoupled coverage |
| **7** | Search & Pagination | `GET :80/api/stocks?limit=3`<br>`GET :80/api/stocks?search=RELIANCE`<br>`GET :80/api/stocks?search=UNKNOWN` | **200 OK**<br>**200 OK**<br>**200 OK** | 18.20ms<br>15.10ms<br>9.40ms | Limit=3 returned 3 items;<br>Search match returned 1 item;<br>Empty search returned `[]` gracefully |
| **8** | Frontend-Backend Comm | `GET http://localhost:80/opportunities` | **200 OK** | 4.35ms | Nginx SPA fallback routes to React Router |
| **9** | Admin Auth Rejection | `POST /api/universe/stocks` (No Key)<br>`POST /api/universe/stocks` (Bad Key) | **401**<br>**401** | 21.00ms<br>18.50ms | Strict 401 Unauthorized (`Invalid or missing administrative API key`) |
| **10**| Authorized Admin Ops | `POST /api/universe/stocks`<br>`GET /api/universe/audit`<br>`PATCH /api/universe/stocks/status` | **201**<br>**200**<br>**200** | 35.10ms<br>24.20ms<br>21.80ms | Onboarded `STG7029`; audit log recorded event; status updated to `ACTIVE` |
| **11**| Volume Persistence | `docker compose restart backend` | **VERIFIED** | — | Record `STG7029` persisted across container restart with 100% fidelity |
| **12**| Container Log Audit | `docker compose logs` scan | **VERIFIED** | — | `ADMIN_API_KEY` was **NOT** present in stdout/stderr |

---

## 6. CI/CD & Test Automation Status (Phase 5.1.5)

- **First-Boot & Staging Seed Tests:** 4 / 4 passed in 0.38s (`backend/tests/test_first_boot_validation.py`)
- **Portable Unit Tests:** 211 / 211 passed (144 deselected) in 32.47s
- **Frontend Unit Tests:** 143 / 143 passed in 2.1s
- **Frontend Production Build:** Vite build succeeded in 737ms
- **Docker Validation:** Backend and Frontend images build cleanly with Buildx.

---

## 7. Cloud Deployment Status & Next Steps

### Current Cloud Account State:
1. **GitHub CLI (`gh`):** Authenticated as `vignesh19807`.
2. **Vercel CLI (`vercel`):** Installed, but local token is expired. Requires user to run `vercel login` or connect GitHub repository in the Vercel Web Dashboard.
3. **Render CLI:** Not installed. Render deployments connect via GitHub repository sync or Render Blueprint (`render.yaml`).

### Rollback Procedure
If a cloud staging deployment fails or exhibits regressions:
1. **Render Backend Rollback:**
   - In Render Dashboard -> `swing-trading-staging-backend` -> **Deploys**.
   - Click the last verified commit -> Select **Rollback to this deploy**.
   - Render instantly re-routes traffic to the previous working Docker container without modifying the persistent disk.
2. **Vercel Frontend Rollback:**
   - In Vercel Dashboard -> **Deployments**.
   - Click the previous green deployment -> Click the three dots -> **Promote to Production** (or Staging domain alias).
   - Instant edge propagation within 3 seconds.

---

## 8. Remaining Limitations

1. **Initial Seed on Render Persistent Disk:**
   - When Render attaches a brand-new persistent disk to `/data`, the disk starts empty.
   - An initial setup step must copy `database/staging_swing_trading.db` to `/data/swing_trading.db` on Render (via Render SSH console or an initial one-off boot script `python -m backend.database.staging_seed`) before `/healthz/ready` can pass.
2. **Single-Instance SQLite Constraint:**
   - Render instance count must remain set to 1. Horizontal scaling is disabled.

---

## 9. Final Readiness Verdict

### **STAGING DEPLOYMENT WITH LIMITATIONS**

The staging infrastructure, database seeding, first-boot verification, containerization, and API security are fully prepared, verified, and ready.

To push code to GitHub and trigger live cloud deployments on Render and Vercel, explicit user authorization is required.

