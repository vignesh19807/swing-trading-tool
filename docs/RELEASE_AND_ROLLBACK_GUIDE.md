# RELEASE AND ROLLBACK GUIDE
**Swing Trading Intelligence Platform — Indian Equities**  
**Document Revision:** 1.0.0 (Release Acceptance Final)  
**Date:** 2026-10-30  

---

## 1. Release Manifest & Artifacts

| Component | Target Location | Build / Deployment Artifact | Verification Command |
| :--- | :--- | :--- | :--- |
| **Backend API** | `backend/` | FastAPI Python Module | `pytest backend/tests/test_api_contract.py` |
| **Database** | `database/` | `swing_trading.db` (9.07 MB) | SHA-256 Checksum Verification |
| **Frontend UI** | `frontend/dist/` | Vite Static Production Bundle | `npm run build` in `frontend/` |

---

## 2. Production Environment Configuration

The following environment variables should be defined in `.env` or system environment for production deployment:

```bash
# Backend Environment
ENVIRONMENT=production
PORT=8000
DATABASE_PATH=database/swing_trading.db

# Security & CORS
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com

# Frontend Environment (.env.production in frontend/)
VITE_API_URL=http://localhost:8000
VITE_APP_NAME="Swing Trading Intelligence Platform"
```

---

## 3. Pre-Release Verification Checklist

Before approving any deployment to staging or production:
- [x] **Git Tree Cleanliness:** No uncommitted changes or unverified modifications.
- [x] **Database Baseline Checksum:** SHA-256 matches `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`.
- [x] **Backend Unit & Contract Tests:** 798/798 unit tests passed; 13/13 API contract tests passed.
- [x] **Frontend Unit & Regression Tests:** 288/288 unit assertions passed.
- [x] **Frontend Production Build:** `npm run build` generates clean assets in `dist/` with 0 errors.
- [x] **End-to-End User Journeys:** 6/6 journeys pass successfully via automated client test.
- [x] **Security & Integrity:** 0 hardcoded secrets, 0 SQL injections, `PRAGMA integrity_check` = `ok`.

---

## 4. Zero-Downtime Rollback Procedure

If a release introduces regression or instability:

### Step 1: Frontend Rollback
Since the frontend is a static Vite bundle:
1. Re-point web server (Nginx / Cloudflare Pages / Caddy) to previous `dist/` release directory.
2. Purge edge CDN cache.
3. Verification: Check app version badge in footer.

### Step 2: Backend Rollback
1. Stop Uvicorn service:
   ```bash
   kill $(pgrep -f uvicorn)
   ```
2. Checkout previous audited Git commit:
   ```bash
   git checkout 77d8aff28c7966033581cea0add2c603c352b22a
   ```
3. Restart backend service:
   ```bash
   python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 2
   ```

### Step 3: Database Rollback (Emergency Only)
If database schema migration was executed and needs rollback:
1. Stop all backend processes.
2. Copy validated backup over active database:
   ```bash
   copy database\swing_trading.db.bak_audit_019 database\swing_trading.db
   ```
3. Verify fingerprint:
   ```bash
   python -c "import hashlib; print(hashlib.sha256(open('database/swing_trading.db','rb').read()).hexdigest().upper())"
   ```
4. Restart backend and verify `/healthz/ready`.

