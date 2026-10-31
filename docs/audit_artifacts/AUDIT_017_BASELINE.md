# AUDIT-017: Baseline Verification and Environment Integrity

**Audit Identifier:** AUDIT-017-BASELINE  
**Execution Timestamp:** 2026-10-29 21:55 IST  
**Auditor:** Quantitative Trading System Auditor & Test Engineer  
**Branch:** `main`  
**Latest Commit Hash:** `77d8aff28c7966033581cea0add2c603c352b22a`

---

## 1. Baseline System and Repository State

Prior to executing any tasks under AUDIT-017, the repository and production database states were documented:

- **Git Branch:** `main`
- **Head Commit:** `77d8aff28c7966033581cea0add2c603c352b22a`
- **Working Tree State:** All AUDIT-016 code fixes and audit deliverables (`AUDIT_016_BASELINE.md` through `AUDIT_016_FINAL_ACCEPTANCE.md`) are present and preserved.

### Production Database Integrity & Backup Verification
- **Production Database File:** `database/swing_trading.db`
- **Baseline SHA256 Checksum:** `10F40129FC710F7E49AB82D285A45F94591D19EF2ED05A74F071FB86EFE92AD2`
- **AUDIT-017 Dedicated Backup:** `database/swing_trading.db.bak_audit_017`
- **Backup Verification Checksum:** `10F40129FC710F7E49AB82D285A45F94591D19EF2ED05A74F071FB86EFE92AD2` (100% byte-for-byte identical)

---

## 2. Production Database Table Inventory

| Table Name | Record Count | Description |
| :--- | :--- | :--- |
| `companies` | 52 | Active Indian equity tickers (Nifty 50 large-caps + key liquid equities) |
| `daily_prices` | 25,746 | Historical daily OHLCV bars |
| `quarterly_results` | 260 | Quarterly financial statements (5 quarters $\times$ 52 companies) |
| `technical_indicators` | 25,746 | Precomputed technical indicators per price bar |
| `sectors` | 17 | Classification sectors |
| `industries` | 45 | Sub-sector industries |
| `backtest_runs` | 2 | Historical baseline runs |
| `backtest_results` | 2 | Run metadata |
| `backtest_trades` | 1 | Historical benchmark trade record |
| `backtest_equity_curve` | 125 | Historical benchmark equity curve points |
| `financial_scores` | 0 | Ephemeral runtime scores table |
| `opportunity_scores` | 0 | Ephemeral runtime scores table |
| `signals` | 0 | Ephemeral runtime signals table |

---

## 3. AUDIT-016 Artifacts Inventory

All 8 AUDIT-016 deliverables are verified intact under `docs/audit_artifacts/`:
1. `AUDIT_016_BASELINE.md`
2. `AUDIT_016_POINT_IN_TIME_FINDINGS.md`
3. `AUDIT_016_BENCHMARK_VALIDATION.md`
4. `AUDIT_016_REJECTION_LEDGER.csv`
5. `AUDIT_016_REJECTION_LEDGER.json`
6. `AUDIT_016_PILOT_RESULTS.md`
7. `AUDIT_016_REGRESSION_RESULTS.md`
8. `AUDIT_016_FINAL_ACCEPTANCE.md`

All audit procedures in AUDIT-017 will operate strictly on isolated scratch databases, leaving `database/swing_trading.db` completely untouched.

