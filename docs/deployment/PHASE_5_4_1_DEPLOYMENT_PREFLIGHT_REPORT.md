# Phase 5.4.1 Cloud Deployment Preflight Audit Report

**Project**: Swing Trading Intelligence Platform
**Target Architecture**:
- Frontend: Vercel Hobby (React 19 + Vite 8 SPA)
- Backend: Render Free Web Service (`swing-trading-staging-backend`)
- Database: Neon Serverless PostgreSQL 16 (`ap-southeast-1`, AWS Singapore)
- Budget Target: Strictly ₹0/month
**Authoritative Git Branch**: `staging`
**Tracking Remote**: `origin/staging`
**Execution Phase**: Phase 5.4.1 — Cloud Deployment Preflight Audit
**Date**: November 8, 2026
**Status**: AUDIT COMPLETE (Zero Deployments, Zero Code Edits, Zero Resource Creations)

---

## A. Executive Summary

Phase 5.4.1 conducted an exhaustive preflight verification of the local and remote deployment posture across Git source control, GitHub Actions CI/CD pipelines, Render Blueprint specifications, Neon PostgreSQL staging configurations, Vercel frontend configurations, and security boundaries.

### Overall Readiness Assessment:
The application source code, Docker containerization, database abstraction layer (DAL), and CI/CD pipelines are fully validated and production-ready for a zero-cost cloud staging deployment.

### Critical Blockers Identified:
1. **[P0 BLOCKER] Compromised Neon Password Not Rotated**:
   - The active staging connection string in the local untracked `.env` file still contains the previously exposed Neon role password (`npg_2EblfgiIw1Mj`).
   - In accordance with Task 5 & 7 security requirements, this unrotated credential is a **critical deployment blocker**. The database owner role password must be rotated in the Neon Console before provisioning or configuring cloud services.
2. **[P2 OPERATIONAL] Inactivity Sleep & Cold Starts**:
   - Render Free Web Services spin down after 15 minutes of inactivity; initial wake-up takes ~50 seconds.
   - Neon Serverless PostgreSQL autosuspends after 5 minutes of inactivity; wake-up takes ~1.5 seconds.
   - Frontend SPA loading states handle these latencies cleanly.

### Recommended Next Action:
Rotate the Neon staging database password in the Neon Console, update the local `.env` with the newly rotated connection string, and proceed to Phase 5.4.2 provisioning.

---

## B. Git & CI/CD Verification

### 1. Git State Inspection
- **Current Branch**: `staging`
- **Remote**: `origin` (`https://github.com/vignesh19807/swing-trading-tool.git`)
- **Remote Synchronization**: `Your branch is up to date with 'origin/staging'`.
- **Recent Commit Lineage**:
  - `85e1175` — `fix(tests): import Optional for Python 3.11 compatibility` (HEAD -> staging, origin/staging)
  - `66dddc5` — `fix(config): import Optional for Python 3.11 compatibility`
  - `6915e99` — `docs(deployment): add Phase 5.3 PostgreSQL migration and deployment validation reports`
  - `f928bf4` — `feat(pipeline): adapt data services for multi-engine SQL and add test suites`
  - `8b08949` — `feat(database): implement PostgreSQL abstraction layer and Render staging blueprint`
  - `57d4541` — `docs(deployment): add Phase 5.2 remote staging deployment report`
- **Working Tree**: Zero modified tracked files; zero staged changes; 5 untracked files (2 local secret helpers, 3 Phase 5.3.9 documentation files).
- **Git-Ignored Files**: Verified `.env`, `backend/.env`, and `frontend/.env.local` remain untracked and strictly git-ignored.

### 2. GitHub Actions CI/CD Verification
- **Latest Workflow Run ID**: `42392179435`
- **Workflow Name**: Continuous Integration
- **Run URL**: [https://github.com/vignesh19807/swing-trading-tool/actions/runs/42392179435](https://github.com/vignesh19807/swing-trading-tool/actions/runs/42392179435)
- **Status**: **COMPLETED — 100% SUCCESS (ALL GREEN)**

| Job | Status | Duration | Scope |
|---|---|---|---|
| **Frontend Tests & Production Build** | **SUCCESS** | 13s | Node.js 20, 143 unit tests passed, Vite production build succeeded. |
| **Backend Tests & Governance Audit** | **SUCCESS** | 51s | Python 3.11 with live `postgres:16-alpine` service container; all portable and DAL integration tests passed. |
| **Docker Image Build Validation** | **SUCCESS** | 50s | Docker Buildx validated backend and frontend Dockerfiles. |

---

## C. Render Backend Readiness

### 1. Service Specification (`render.yaml`)
- **Service Name**: `swing-trading-staging-backend`
- **Service Type**: `web`
- **Runtime**: `docker` (`dockerfilePath: backend/Dockerfile`, `dockerContext: .`)
- **Hosting Plan**: `plan: free` (**$0/month target preserved**)
- **Region**: `oregon`
- **Persistent Disk**: **None** (stateless container; Render Free Tier compatible)
- **Health Check Path**: `/healthz`
- **Auto Deploy**: `false` (manual promotion model)

### 2. Environment Variables & Startup Guard
- **`ENVIRONMENT=production`**: Enforced. In production mode, `validate_database_environment()` requires `postgresql://` or `postgres://` and fails closed immediately on startup if missing or if pointing to SQLite.
- **`DATABASE_URL`**: Defined with `sync: false` (must be entered securely in the Render Dashboard without storing credentials in source control).
- **`ADMIN_API_KEY`**: Defined with `generateValue: true` (cryptographically generated random secret upon provisioning).
- **`PORT`**: Dynamically bound via `CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]`.
- **`CORS_ORIGINS`**: Configurable without source edits (`value: https://swing-trading-staging.vercel.app,http://localhost:5173,http://localhost:3000`).

**Render Readiness Verdict**: **READY FOR PROVISIONING**.

---

## D. Neon PostgreSQL Readiness

### 1. Configuration & Connectivity
- **Target Project**: `swing-trading-staging`
- **Database**: `neondb`
- **Role**: `neondb_owner`
- **Engine**: PostgreSQL 16.15 (AWS Singapore, `ap-southeast-1`)
- **Driver**: `psycopg` (PEP 249) + `psycopg-pool` connection pooling.
- **SSL / Security**: `sslmode=require` and `channel_binding=require` enforced.
- **Domain Tables Verified**: 15 public domain tables verified live.
- **Financial Immutability Triggers**: All 3 triggers active on live schema (`prevent_financial_metric_mutation`, etc.).
- **Synthetic Data**: 19 synthetic staging companies present; 0 production financial records uploaded.
- **Data Protection**: Zero automated production migrations or SQLite imports executed during container boot.

### 2. Credential Security Audit
- **Status**: **COMPROMISED PASSWORD UNROTATED (P0 BLOCKER)**
- **Finding**: The active database URL in `.env` still contains the password `npg_2EblfgiIw1Mj` exposed in an earlier session.
- **Remediation**: Before creating the Render web service, the password for `neondb_owner` must be reset in the Neon Console.

---

## E. Vercel Frontend Readiness

### 1. Build & Runtime Configuration
- **Framework**: React 19 + Vite 8 SPA (`frontend/package.json`)
- **Build Command**: `npm --prefix frontend run build` (configured in root `vercel.json`)
- **Output Directory**: `frontend/dist` (configured in root `vercel.json`)
- **Clean URLs**: `cleanUrls: true`
- **SPA Rewrites**:
  ```json
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
  ```
- **Node.js Compatibility**: Compatible with Node.js 18, 20, and 22.

### 2. API Service Configuration (`frontend/src/services/api.js`)
- **Configurable Base URL**: Reads `import.meta.env.VITE_API_BASE_URL`.
- **Fail-Closed Real Mode Guard**: If `VITE_USE_MOCK_DATA` is false and `VITE_API_BASE_URL` is missing or empty, throws explicit `ConfigurationError`.
- **Zero Localhost Fallback**: No hardcoded fallback to `http://localhost:8000` in production bundle.
- **Secrets Audit**: Scanned production assets in `frontend/dist/`; zero backend secrets, database passwords, or private tokens found.

**Vercel Readiness Verdict**: **READY FOR PROVISIONING**.

---

## F. Cross-Service Integration Readiness

### Communication Architecture:
```text
User Browser
     │
     ▼
Vercel Frontend (SPA)
     │
     │ HTTPS REST Calls
     ▼
Render FastAPI Backend
     │
     │ TLS 1.3 / AWS Singapore
     ▼
Neon Serverless PostgreSQL 16
```

### Integration Dependency Matrix:
1. **Render -> Neon**: Render backend connects to Neon via `DATABASE_URL` over TLS.
2. **Vercel -> Render**: Vercel SPA sends API calls to Render URL specified in `VITE_API_BASE_URL`.
3. **Render -> Vercel**: Render backend allows cross-origin requests from Vercel domain specified in `CORS_ORIGINS`.
4. **Provisioning Sequence Requirement**:
   - Render Web Service must be provisioned first to obtain the public Render URL (`https://<service-name>.onrender.com`).
   - The Render URL is then provided to Vercel as `VITE_API_BASE_URL`.
   - The Vercel URL (`https://<project-name>.vercel.app`) is provided to Render as `CORS_ORIGINS`.

---

## G. Security Findings (Categorized by Severity)

| Severity | ID | Category | Finding Description | Remediation |
|---|---|---|---|---|
| **P0** | SEC-001 | Credential Exposure | Active Neon connection string uses the previously exposed password `npg_2EblfgiIw1Mj`. | Rotate password in Neon Console prior to cloud provisioning. |
| **P2** | SEC-002 | Admin Security | Administrative write endpoints require `X-API-Key` header matching `ADMIN_API_KEY`. | Render `render.yaml` automatically generates a secure random key via `generateValue: true`. |
| **P2** | SEC-003 | CORS Origin | Staging deployment requires exact Vercel staging URL in `CORS_ORIGINS`. | Update Render `CORS_ORIGINS` once Vercel project name is assigned. |
| **P3** | SEC-004 | Node Deprecation | GitHub Actions runner warned of Node.js 20 deprecation in standard GitHub actions. | Upgrade GitHub Actions steps to Node 24 in future CI maintenance. |

---

## H. Cost & Free-Tier Readiness Analysis

**Target Budget: ₹0 / month**

| Service | Plan / Tier | Verified Free Resource Limits | Staging Consumption | Cost |
|---|---|---|---|---|
| **Vercel** | Hobby | 100 GB bandwidth, unlimited deployments, custom domains. | < 500 MB bandwidth / month | **₹0** |
| **Render** | Free Web Service | 750 free instance hours / month, 512 MB RAM, 0.1 CPU, spun down when idle. | 1 service, stateless Docker container | **₹0** |
| **Neon** | Free Tier | 0.5 GiB storage, 1 compute project, shared vCPU, autosuspend after 5 min. | ~15 MB storage (synthetic schema + 19 stocks) | **₹0** |
| **GitHub Actions** | Standard | 2,000 free runner minutes / month for public/private repos. | < 100 minutes / month | **₹0** |

**Total Estimated Monthly Hosting Cost: ₹0.00**

---

## I. Database & Trading Engine Invariant Protection

- **Production SQLite Database**:
  - Path: `database/swing_trading.db`
  - SHA-256: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**Identical**)
- **Staging SQLite Database**:
  - Path: `database/staging_financial_expansion.db`
  - SHA-256: `84263F185EC782443F8C15F08F0AEAB96C0BD8B40413D5ADD12C3AE908176BE7` (**Identical**)
- **Protected Logic Engines** (`backend/logic/`):
  - `signal_engine.py`: **0 changes**
  - `trade_quality_engine.py`: **0 changes**
  - `portfolio_simulator.py`: **0 changes**

---

## J. Final Preflight Decision

### **`READY WITH BLOCKERS`**

**Reason**:
The architecture, Dockerfiles, Render blueprint, Vercel build settings, and GitHub Actions CI pipelines are completely verified and production-ready for ₹0/month cloud deployment. However, **P0 Blocker SEC-001** requires that the database owner password be rotated in the Neon Console before the connection string is entered into Render or used for staging deployment.
