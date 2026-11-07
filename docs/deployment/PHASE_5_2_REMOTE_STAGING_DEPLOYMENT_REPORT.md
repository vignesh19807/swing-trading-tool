# PHASE 5.2 — GITHUB BRANCH AND REMOTE STAGING DEPLOYMENT REPORT

- **Project:** Swing Trading Intelligence Platform (Indian Equities)
- **Phase:** 5.2 — GitHub Branch and Remote Staging Deployment
- **Execution Date:** 2026-11-07
- **Branch Name:** `staging`
- **Commit Hash:** `6d5a0fc` (`feat(deployment): prepare isolated staging environment`)
- **Remote Tracking:** `origin/staging` -> `https://github.com/vignesh19807/swing-trading-tool.git`
- **Auditor Role:** Senior Cloud Architect, DevOps Engineer & Site Reliability Specialist
- **Production Database SHA-256 (Invariant):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (100% Unmodified)
- **Protected Strategy Engines:**
  - `backend/logic/strategy_engine.py`: Non-existent
  - `backend/logic/signal_engine.py`: Untouched
  - `backend/logic/trade_quality_engine.py`: Untouched
  - `backend/logic/portfolio_simulator.py`: Untouched
- **Readiness / Deployment Status:** **STAGING BRANCH PUSHED — AWAITING CLOUD AUTHENTICATION**

---

## 1. Executive Summary & Audit Findings

Phase 5.2 successfully established the dedicated `staging` branch, conducted pre-deployment secret and invariant verification, confirmed database exclusion rules, and pushed the complete staging codebase to GitHub.

All financial governance invariants and protected logic files remain untouched. The production database SHA-256 hash was verified before and after operations, confirming zero modification.

### Pre-Deployment Audit Resolution: The 11 vs 10 Companies Question
**User Investigation Request:**
> *"Investigate why the staging readiness response reports 11 companies when the staging seed report describes 10 equities."*

**Audit Finding & Lineage Verification:**
1. **Initial Seed Dataset (`backend/database/staging_seed.py`):**
   The staging seed script defines exactly 10 initial equities:
   `["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK", "TATAMOTORS", "SUNPHARMA", "HINDUNILVR", "ITC", "LT"]`.
   On initial generation, `staging_seed.py` output confirms: `Companies seeded: 10`.
2. **Authorized Administrative Onboarding during Staging Validation:**
   In Phase 5.1.6, Step 10 of `scratch/verify_staging_deployment.py` tested the administrative onboarding endpoint:
   `POST /api/universe/stocks` with header `X-API-Key: staging_test_secret_key_889900` and payload `{"symbol": "STAGENEW", ...}`.
   This call succeeded with HTTP 201 Created and inserted an 11th record into the `companies` table.
3. **Volume Persistence Verification:**
   Because the Docker named volume `staging_market_data` provides persistent block storage, `STAGENEW` was written to SQLite disk. When the container was restarted and `/healthz/ready` was polled, it executed `SELECT count(*) FROM companies`, returning `11`.
4. **Architectural Significance:**
   This confirms that:
   - The administrative onboarding pipeline works end-to-end.
   - The persistent volume persists mutating data across container lifecycles.
   - The `/healthz/ready` probe dynamically inspects genuine database state rather than returning a cached or hardcoded integer.

---

## 2. Pre-Deployment Integrity & Exclusion Verification (Step 1)

Before creating or pushing the branch, the working tree was audited for secrets and sensitive artifacts:

| Check | Target / Condition | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **Production Database** | `database/swing_trading.db` excluded from Git | **VERIFIED** | Matched by `*.db` in `.gitignore`. SHA-256 `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`. |
| **Staging Database** | `database/staging_swing_trading.db` excluded | **VERIFIED** | Matched by `*.db` in `.gitignore`. Not tracked in Git. |
| **Raw Pilot Filings** | `database/staging_filings_store/` | **VERIFIED** | Added to `.gitignore` and `.dockerignore`. |
| **Scratch Files** | `scratch/` test scripts & logs | **VERIFIED** | Added to `.gitignore`. Zero scratch files committed. |
| **Environment Secrets** | `.env`, `.env.local`, `.env.*` | **VERIFIED** | Excluded; only safe `.env.example` templates committed. |
| **API Keys in Git** | Secret token scan on staged diff | **CLEAN** | Zero hardcoded keys or passwords in commit diff. |
| **Protected Logic** | `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py` | **UNTOUCHED** | Zero diff in core engine files. |

---

## 3. Dedicated Git Staging Branch (Steps 2 & 3)

The isolated `staging` branch was branched from local `main` and pushed directly to GitHub:

- **Branch Created:** `staging`
- **Commit SHA:** `6d5a0fc7c9fdf1d904f5e71e7552541c4f6ec1fe`
- **Commit Message:** `feat(deployment): prepare isolated staging environment`
- **Remote URL:** `https://github.com/vignesh19807/swing-trading-tool.git`
- **Push Command:** `git push -u origin staging` (Clean push, non-fast-forward rejected, zero force pushes).
- **Files Committed:** 155 files (staging infrastructure, `render.yaml`, `vercel.json`, `first_boot_validation.py`, `staging_seed.py`, test suites, and audit reports).

---

## 4. Cloud Deployment Status & Authentication Verification

### A. Render Backend Deployment (Step 4)
- **Configuration:** [`render.yaml`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/render.yaml)
  - Service: `swing-trading-staging-backend`
  - Runtime: Docker (`backend/Dockerfile`)
  - Plan: Starter (supports persistent disk)
  - Persistent Disk: 1 GB SSD mounted to `/data`
  - Instance Count: **Locked to 1**
  - Health Check: `/healthz`
  - Environment Variables:
    - `DATABASE_PATH`: `/data/swing_trading.db`
    - `PORT`: `8000`
    - `CORS_ORIGINS`: `https://swing-trading-staging.vercel.app,http://localhost:5173,http://localhost:3000`
    - `ADMIN_API_KEY`: Auto-generated via `generateValue: true`
- **Authentication Check:**
  - Render CLI is not installed locally.
  - Render deployments are triggered by connecting the GitHub repository `vignesh19807/swing-trading-tool` in the Render Web Dashboard (or via a Render Deploy Hook).
  - **Required User Action:** Log in to [dashboard.render.com](https://dashboard.render.com), click **New + -> Blueprint**, connect `vignesh19807/swing-trading-tool`, and select branch `staging`. Render will automatically parse `render.yaml` and provision the staging Web Service.

### B. Vercel Frontend Deployment (Step 5)
- **Configuration:** [`frontend/vercel.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/frontend/vercel.json) & [`vercel.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/vercel.json)
  - Rewrites: `/(.*)` -> `/index.html` (SPA fallback)
  - Build Command: `npm run build`
  - Output Directory: `dist`
- **Authentication Check:**
  - Vercel CLI version 58.9.0 is installed, but the local token is expired:
    `Error: The specified token is not valid. Use vercel login to generate a new token.`
  - **Required User Action:** In a terminal, run `vercel login` to authenticate the CLI, OR import `vignesh19807/swing-trading-tool` in the Vercel Dashboard, select branch `staging`, and set `VITE_API_BASE_URL` to the Render staging URL.

---

## 5. Security & Verification Invariants

1. **Production Invariant:**
   Production database SHA-256 remains `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`.
2. **Fail-Closed Security:**
   Unconfigured `ADMIN_API_KEY` returns HTTP 403 Forbidden; missing/invalid `X-API-Key` returns HTTP 401 Unauthorized.
3. **No Branch Pollution:**
   All deployment artifacts, blueprint definitions, and routing configurations were committed solely to `staging`. `main` remains protected and untouched.

---

## 6. Next Steps for Cloud Activation

1. **Connect Staging to Render:**
   In [Render Dashboard](https://dashboard.render.com):
   - Click **New +** -> **Blueprint**.
   - Select repository: `vignesh19807/swing-trading-tool`.
   - Set branch: `staging`.
   - Render provisions `swing-trading-staging-backend`.
2. **Initial Disk Seeding on Render:**
   Once Render provisions the persistent disk at `/data`:
   - Open the Render Shell for `swing-trading-staging-backend`.
   - Run: `python -m backend.database.staging_seed` (or copy the staging database to `/data/swing_trading.db`).
   - The health probe `/healthz` will immediately transition to Healthy.
3. **Connect Staging to Vercel:**
   In [Vercel Dashboard](https://vercel.com):
   - Import `vignesh19807/swing-trading-tool`.
   - Set Root Directory to `frontend`.
   - Set Environment Variable: `VITE_API_BASE_URL=https://swing-trading-staging-backend.onrender.com`.
   - Deploy.
4. **Execute Remote Validation:**
   Once live URLs are issued, run remote smoke tests against the public endpoints.
