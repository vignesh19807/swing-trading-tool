# AUDIT-015: Baseline Verification and State Integrity

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Date:** 2026-10-29  
**Audit Stage:** AUDIT-015 Controlled Backtest Readiness and Data Integrity  

---

## 1. Git Repository State

- **Active Branch:** `main`
- **Head Commit:** `77d8aff28c7966033581cea0add2c603c352b22a`
- **Commit Subject:** `fix: resolve dashboard & stock explorer data integration gaps and add readiness test suite`
- **Working Tree Inventory:**
  - 24 tracked modified files preserved intact.
  - All untracked test suites, engine modules, and prior audit artifacts preserved intact under `docs/audit_artifacts/`.

---

## 2. Active Production Database Baseline & Backup

- **Production Database Path:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool\database\swing_trading.db`
- **Backup Database Path:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool\database\swing_trading.db.bak_audit_015`
- **File Size:** `9,068,544 bytes` (8.65 MB)
- **Baseline SHA256 Checksum:** `10f40129fc710f7e49ab82d285a45f94591d19ef2ed05a74f071fb86efe92ad2`
- **Backup Verification:** Both the live database and backup file have matching bit-for-bit SHA256 checksums.

### Active Database Table Inventory:
| Table Name | Row Count | Status / Notes |
| :--- | :---: | :--- |
| `companies` | 52 | Active stock universe |
| `daily_prices` | 25,746 | Historical daily OHLCV bars (~2 years per company) |
| `quarterly_results` | 260 | 5 quarters per company across 52 stocks |
| `technical_indicators` | 25,746 | Precomputed technical indicators per daily bar |
| `financial_scores` | 0 | Dynamic engine calculation |
| `opportunity_scores` | 0 | Dynamic engine calculation |
| `backtest_runs` | 2 | Historical test runs (1 pilot + 1 legacy synthetic trace from AUDIT-010) |
| `backtest_trades` | 1 | Trade record from legacy synthetic trace |
| `backtest_equity_curve` | 125 | Equity points from legacy runs |
| `backtest_results` | 2 | Run summary rows |

---

## 3. Verification of AUDIT-014 Reconciliation Ledger

- **CSV Path:** `docs/audit_artifacts/AUDIT_014_BUY_LEDGER_127.csv` (Size: 25,607 bytes)
- **JSON Path:** `docs/audit_artifacts/AUDIT_014_BUY_LEDGER_127.json` (Size: 85,590 bytes)
- **Total Validated Records:** Exactly 127 rows across 5 pilot stocks (`TCS`: 10, `INFY`: 54, `HDFCBANK`: 25, `RELIANCE`: 24, `ITC`: 14).
- **Mutual Exclusivity Invariant:** Verified. Every single record possesses exactly one final non-null rejection reason:
  - `PRICE_OUTSIDE_ENTRY_ZONE`: 96
  - `INSUFFICIENT_RISK_REWARD_RATIO`: 27
  - `TARGET_BELOW_CURRENT_PRICE`: 2
  - `TARGET_BELOW_ENTRY_PRICE`: 2
- **Eligible Trades:** 0 executed trades.

---

## 4. Production Protection Mandate

In accordance with strict audit rules:
1. All pilot backtest executions during AUDIT-015 will execute against isolated temporary SQLite databases.
2. The active production database (`database/swing_trading.db`) will remain strictly read-only.
3. Checksums will be re-verified following all experimental executions.

