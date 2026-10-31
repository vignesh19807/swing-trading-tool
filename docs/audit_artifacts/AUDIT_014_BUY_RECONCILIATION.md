# AUDIT-014: Independent Reproduction and Evidence Reconciliation of All 127 BUY Recommendations

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Scope:** 5 Pilot Stocks (`TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `ITC`)  
**Evaluation Dates:** 2025-10-01 to 2026-03-31 (122 trading days × 5 stocks = 610 stock-sessions)  
**Verification Date:** 2026-10-29  
**Execution Status:** **EXIT CODE 0 — 100% INDEPENDENTLY REPRODUCED**

---

## 1. Investigation of Prior Non-Zero Exit Codes

In AUDIT-013, the script execution task (`task-1325`) threw an unhandled exception at its final line:
```
OSError: Cannot save file into a non-existent directory: 'scratch'
```
**Root Cause:**
The script successfully computed all 610 stock-sessions, identified all 127 BUY recommendations, evaluated the full pipeline sequentially, and printed the summary counts to stdout. However, at line 111, it called `df.to_csv('scratch/buy_reconciliation_127.csv')` assuming a `scratch` directory existed in the current project root, whereas the scratch directory was located within the agent environment app-data directory.

**Resolution in AUDIT-014:**
The corrected runner script (`scratch/reconcile_127_buys_audit_014.py`) creates the target directory programmatically and outputs directly to `docs/audit_artifacts/AUDIT_014_BUY_LEDGER_127.csv` and `docs/audit_artifacts/AUDIT_014_BUY_LEDGER_127.json`.
- **Command:** `$env:PYTHONPATH="."; .\.venv\Scripts\python.exe "C:\Users\vigne\.gemini\antigravity\brain\f7e35db9-6a37-4075-b14d-39ff0aefd450\scratch\reconcile_127_buys_audit_014.py"`
- **Exit Code:** `0`
- **Machine-Readable Ledger Artifacts:**
  - CSV: [`AUDIT_014_BUY_LEDGER_127.csv`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/AUDIT_014_BUY_LEDGER_127.csv)
  - JSON: [`AUDIT_014_BUY_LEDGER_127.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/AUDIT_014_BUY_LEDGER_127.json)

---

## 2. Independent Reproduction Results

### Rejection Distribution:
| Pipeline Primary Rejection Reason | Reconciled Count | Percentage of Raw BUYs | Sequential Pipeline Gate |
| :--- | :---: | :---: | :--- |
| **`PRICE_OUTSIDE_ENTRY_ZONE`** | **96** | 75.59% | **Gate 1:** Price not in $[Support, Support + 1.0\% \times ATR_{14}]$ |
| **`INSUFFICIENT_RISK_REWARD_RATIO`** | **27** | 21.26% | **Gate 3:** $R:R < 1.5$ |
| **`TARGET_BELOW_CURRENT_PRICE`** | **2** | 1.57% | **Gate 2:** Target $\le$ Current Price |
| **`TARGET_BELOW_ENTRY_PRICE`** | **2** | 1.57% | **Gate 2:** Target $\le$ Entry Price |
| **TOTAL RAW BUY RECOMMENDATIONS** | **127** | **100.0%** | **0 Trades Executed** |

### Per-Stock Breakdown:
| Stock | Total Evaluated Sessions | Raw BUY Recommendations | `PRICE_OUTSIDE_ENTRY_ZONE` | `INSUFFICIENT_RISK_REWARD_RATIO` | `TARGET_BELOW_CURRENT_PRICE` | `TARGET_BELOW_ENTRY_PRICE` | Final Eligible Trades |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **INFY** | 122 | 54 | 37 | 14 | 2 | 1 | 0 |
| **HDFCBANK** | 122 | 25 | 17 | 8 | 0 | 0 | 0 |
| **RELIANCE** | 122 | 24 | 23 | 0 | 0 | 1 | 0 |
| **ITC** | 122 | 14 | 10 | 4 | 0 | 0 | 0 |
| **TCS** | 122 | 10 | 9 | 1 | 0 | 0 | 0 |
| **TOTAL** | **610** | **127** | **96** | **27** | **2** | **2** | **0** |

---

## 3. Invariant Verification

An automated verification script executed against `AUDIT_014_BUY_LEDGER_127.csv` proved the following structural invariants:
1. **Completeness:** Exactly 127 rows present, representing all dates where `opportunity_score >= 70.0` and `recommendation == 'BUY'` across the 610 stock-sessions.
2. **Mutual Exclusivity:** Every record has exactly one non-null primary rejection reason (`df['rejection_reason'].isna().sum() == 0`).
3. **Deterministic Capital Preservation:** All 127 records have `eligibility_decision == False`. Exactly 0 trades were executed by the trade simulator.

---

## 4. Chronology of Audit Discrepancies (AUDIT-010 through AUDIT-014)

1. **AUDIT-010 (Step 480 vs Step 496):**
   - In Step 480, while an exploratory simulation task was running, an early script log showed 125 outside entry zone and 2 target below entry price based on non-short-circuit checking.
   - When Step 496 completed, the authoritative numbers (96, 27, 2, 2) were calculated.
2. **AUDIT-011:**
   - Authoritatively recorded and published the complete 127-itemized ledger matching the 96/27/2/2 distribution.
3. **AUDIT-012:**
   - Focus was on resolving the 18 failing legacy backend unit tests. The introductory summary text mistakenly copy-pasted the draft numbers from AUDIT-010 Step 480 (125/2).
4. **AUDIT-013:**
   - Re-verified the pipeline mathematically and identified the AUDIT-012 text error. However, the scratch script errored on CSV output due to a relative path directory mismatch.
5. **AUDIT-014:**
   - Fixed the CSV/JSON output path, executed with exit code 0, generated the complete machine-readable ledger, and verified mutual exclusivity and accounting invariants.

