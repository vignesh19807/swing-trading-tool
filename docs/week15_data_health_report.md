# Week 15 — Full Data-Layer Health Report

**Swing Trading Intelligence Platform | Data Engineering Layer**  
**Audit Date**: August 31, 2026  
**Health Test Suite**: `backend/data_pipeline/test_week15_data_health.py` (9/9 passing)  
**Quality Monitor**: `backend/data_pipeline/week15_quality_monitor.py`  
**Database Path**: `database/swing_trading.db`

---

## 1. Executive Summary

This report provides the full consolidated data-layer health validation for the Swing Trading Intelligence Platform as mandated by the Week 15 Data Engineer Checklist.

### Overall Status: **HEALTHY & PRODUCTION-READY**
- **Universe**: 50 companies, 50 distinct symbols, 0 missing symbols.
- **Market Data**: 25,495 rows across 50 companies (date span: 2024-08-14 to 2026-08-28), 0 missing stocks, 0 orphan records.
- **Technical Indicators**: 25,495 rows, 1:1 synchronization with daily price records, 0 count mismatches.
- **Financial Data**: 280 quarterly records, 50/50 companies covered (periods: 2024-12-31 to 2026-06-30).
- **Classification**: 16 sectors, 32 industries, 0 unmapped companies.
- **Point-in-Time Historical Safety**: 0 leakage violations across historical evaluation date queries.
- **Backup & Recovery**: Week 12 database backup and recovery validation verified.

---

## 2. Table-by-Table Health Audit

| Table Name | Row Count | Primary Key / Unique Constraint | Indexed Foreign Keys | Integrity Status |
| :--- | :---: | :--- | :--- | :---: |
| `companies` | **50** | `id` (PK), `symbol` (UNIQUE) | `sector_id`, `industry_id` | ✅ Pass (50 distinct symbols, 0 nulls) |
| `sectors` | **16** | `id` (PK), `name` (UNIQUE) | None | ✅ Pass (Complete master data) |
| `industries` | **32** | `id` (PK), `name` | `sector_id` | ✅ Pass (Complete master data) |
| `daily_prices` | **25,495** | `id` (PK), `(company_id, date)` | `(company_id, date)` | ✅ Pass (0 missing stocks, 0 orphans) |
| `technical_indicators` | **25,495** | `id` (PK), `(company_id, date)` | `(company_id, date)` | ✅ Pass (0 sync mismatches) |
| `quarterly_results` | **280** | `id` (PK), `(company_id, quarter)` | `(company_id, quarter)` | ✅ Pass (50/50 companies covered) |
| `financial_scores` | **0** (Transient) | `id` (PK), `(company_id, date)` | `(company_id, date)` | ✅ Pass (Idempotent table ready) |
| `opportunity_scores` | **0** (Transient) | `id` (PK), `(company_id, date)` | `(company_id, date)` | ✅ Pass (Idempotent table ready) |
| `signals` | **0** (Transient) | `id` (PK), `(company_id, date)` | `(company_id, date)` | ✅ Pass (Idempotent table ready) |
| `backtest_results` | **2** | `id` (PK), `(run_id, symbol, date)` | `(run_id, symbol, date)` | ✅ Pass (0 duplicate violations) |

---

## 3. Synchronization & Data Consistency Verification

```
                      ┌────────────────────────┐
                      │    companies (50)      │
                      └───────────┬────────────┘
                                  │ 1:N
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│  daily_prices (25495) │ │ technical_ind (25495) │ │ quarterly_res (280)   │
└───────────┬───────────┘ └───────────┬───────────┘ └───────────────────────┘
            │                         │
            └───────────┬─────────────┘
                        │ 1:1 Date Match
                        ▼
            0 Unmatched Daily Rows
            0 Unmatched Technical Rows
            0 Count Mismatches
```

1. **Market / Technical Synchronization**:
   - `daily_prices` left join `technical_indicators` on `company_id` and `date`: **0 unmatched**.
   - `technical_indicators` left join `daily_prices` on `company_id` and `date`: **0 unmatched**.
   - Row-count mismatch query across all 50 companies: **0 mismatches**.

2. **Foreign Key Integrity**:
   - `daily_prices` orphan records: **0**.
   - `technical_indicators` orphan records: **0**.
   - `quarterly_results` orphan records: **0**.

---

## 4. Point-in-Time Historical Safety Audit

The historical backtesting interface (`get_backtest_inputs`) was tested across representative universe stocks (`INFY`, `TCS`, `RELIANCE`, `HDFCBANK`, `ITC`) over historical evaluation dates.

- **Contract Condition**: For every evaluated date $T_{eval}$, any attached financial reporting period $T_{report}$ must satisfy:
  $$T_{report} \le T_{eval}$$
- **Audit Result**:
  - Total records evaluated: **90**.
  - Future financial leakage violations: **0**.
  - Historical safety check: **PASS**.

---

## 5. Backup & Recovery Verification (Week 12 Status)

- **Source Database**: `database/swing_trading.db`
- **Backup Snapshot**: `database/backups/swing_trading_*.db`
- **Recovery Database**: `database/recovery/swing_trading_recovery.db`
- **Integrity Status**: `ok` (PRAGMA integrity_check passed).
- **Table Verification**: All 10 tables restored with 100% row-count parity without overwriting production.
