# PRODUCTION OPERATIONS RUNBOOK
**Swing Trading Intelligence Platform — Indian Equities**  
**Document Revision:** 1.0.0 (AUDIT-036 Release Final)  
**Target Environment:** Local / On-Premise / Cloud Virtual Server  

---

## 1. System Overview & Architecture

- **Backend:** FastAPI (Python 3.12+ / 3.14), SQLite 3, Uvicorn ASGI
- **Frontend:** React 19, Vite 8, Tailwind CSS, Recharts
- **Storage:** Local SQLite Database at `database/swing_trading.db`
- **Data Ingestion:** Yahoo Finance (`yfinance`) pipeline with localized caching

---

## 2. Daily Routine & Ingestion Lifecycle

Trading on the National Stock Exchange of India (NSE) concludes at **15:30 IST (10:00 UTC)**. The post-market Bhavcopy and Yahoo Finance closing prices typically settle by **17:00 IST**.

### Daily Operational Schedule:
| Time (IST) | Task | Command / Script | Expected Duration |
| :--- | :--- | :--- | :--- |
| **17:30 IST** | **Pre-Ingestion Backup** | `python scripts/backup_db.py` | < 2 seconds |
| **17:35 IST** | **Daily OHLCV Update** | `python backend/data_pipeline/data_pipeline_orchestrator.py --daily` | ~45 seconds |
| **17:40 IST** | **Compute Technical Indicators** | `python backend/data_pipeline/technical_indicator_service.py` | ~15 seconds |
| **17:45 IST** | **Update Sector Relative Strength** | `python backend/logic/sector_engine.py` | ~10 seconds |
| **17:50 IST** | **Run Health Verification** | `curl -f http://localhost:8000/healthz/ready` | < 1 second |

---

## 3. Starting the Production Application

### Backend Startup:
```bash
# From repository root
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 2
```
Verify backend is healthy:
```bash
curl http://localhost:8000/healthz/live
# Expected: {"status": "ok", "timestamp": "..."}
curl http://localhost:8000/healthz/ready
# Expected: {"status": "ready", "companies_count": 52, ...}
```

### Frontend Startup:
```bash
# From frontend directory
cd frontend
npm run build
npm run preview -- --port 5173 --host 0.0.0.0
```
Open browser to `http://localhost:5173`.

---

## 4. Database Backup, Checksum & Recovery Procedures

### Safe Online Backup Command:
Never copy `swing_trading.db` directly while write operations are underway. Use the SQLite online backup script:
```bash
python -c "import sqlite3; src = sqlite3.connect('database/swing_trading.db'); dest = sqlite3.connect('database/backups/swing_trading_' + datetime.date.today().isoformat() + '.db'); src.backup(dest); src.close(); dest.close()"
```

### Integrity Verification:
```bash
python -c "import sqlite3; conn = sqlite3.connect('database/swing_trading.db'); print(conn.execute('PRAGMA integrity_check').fetchall())"
# Expected output: [('ok',)]
```

### Emergency Restore from Backup:
If the production database experiences corruption or unexpected mutation:
```bash
# 1. Stop backend service
# 2. Restore from known good backup
copy database\swing_trading.db.bak_audit_019 database\swing_trading.db
# 3. Verify SHA-256 fingerprint matches baseline:
python -c "import hashlib; print(hashlib.sha256(open('database/swing_trading.db', 'rb').read()).hexdigest().upper())"
# Expected: 1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8
```

---

## 5. Troubleshooting & Incident Runbook

| Alert / Symptom | Root Cause | Immediate Action |
| :--- | :--- | :--- |
| **HTTP 503 from `/healthz/ready`** | Database missing or tables empty | Verify `database/swing_trading.db` exists and has permissions. |
| **`/api/data-health` shows DATA_WARNING** | Latest prices are older than 3 business days | Check internet connection to Yahoo Finance; run manual update script. |
| **HTTP 429 from Yahoo Finance** | Rate-limiting on public API | Pipeline automatically backs off with exponential jitter. Wait 5 minutes and re-run. |
| **Negative volume or inverted H/L** | Provider data corruption | Ingestion pipeline automatically rejects invalid bars. Inspect quarantine logs. |

