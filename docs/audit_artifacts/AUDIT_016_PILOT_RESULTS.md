# AUDIT-016: Historical Pilot Results & Reconciliation

**Audit Phase:** Phase 6 — Controlled Historical Pilot Execution (Isolated Database)  
**Execution Timestamp:** 2026-10-29T21:26:30+05:30  
**Environment:** Isolated SQLite DB (`temp_pilot_audit_016.db`), Python 3.12.9 (.venv)  
**Status:** VERIFIED (100% Production DB Isolation)  

---

## 1. Executive Summary

The controlled historical pilot for AUDIT-016 re-evaluated the five benchmark stocks (`TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `ITC`) over the 6-month evaluation period (`2025-10-01` to `2026-03-31`), comprising 122 trading days and 610 stock-sessions.

This pilot operated under the **newly implemented point-in-time fundamental data isolation**, which prevents sub-analyzers from reading un-filed future quarters.

### Key Operational Results
* **Total Stock-Sessions Evaluated:** 610
* **Total Raw BUY Signals Generated:** 4
* **Signals Rejected by Trade Quality Filters:** 4 (100.0%)
* **Signals Eligible for Execution:** 0 (0.0%)
* **Closed Trades Persisted:** 0
* **Initial Capital:** ₹100,000.00
* **Final Equity:** ₹100,000.00 (0.00% Net Return, 0.00% Max Drawdown)
* **Production Database Integrity:** Verified (SHA256: `10f40129fc710f7e49ab82d285a45f94591d19ef2ed05a74f071fb86efe92ad2`)

---

## 2. Signal Generation & Rejection Breakdown

Under strict point-in-time isolation, the 4 raw BUY recommendations occurred on:

| Symbol | Evaluation Date | Current Price (₹) | Opportunity Score | Support (₹) | Proposed Entry (₹) | Stop-Loss (₹) | Target (₹) | Risk/Reward Ratio | Primary Rejection Reason | Applicable Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RELIANCE** | 2026-02-27 | 1,391.80 | 70.0 | 1,375.00 | 1,385.20 | 1,365.00 | 1,410.00 | 1.2376 | `INSUFFICIENT_RISK_REWARD_RATIO` | Minimum R:R $\ge 1.5$ |
| **RELIANCE** | 2026-03-02 | 1,398.50 | 70.0 | 1,375.00 | 1,385.20 | 1,365.00 | 1,410.00 | 1.2376 | `PRICE_OUTSIDE_ENTRY_ZONE` | Support Pullback Zone |
| **ITC** | 2026-02-24 | 312.40 | 71.5 | 305.00 | 308.10 | 300.00 | 325.00 | 2.0864 | `PRICE_OUTSIDE_ENTRY_ZONE` | Support Pullback Zone |
| **ITC** | 2026-02-25 | 314.10 | 71.5 | 305.00 | 308.10 | 300.00 | 325.00 | 2.0864 | `PRICE_OUTSIDE_ENTRY_ZONE` | Support Pullback Zone |

### Rejection Mechanics Summary
1. **`PRICE_OUTSIDE_ENTRY_ZONE` (3 rejections):**  
   Current price exceeded the optimal support pullback envelope ($Close > Support + 1.0\% \times ATR_{14}$).
2. **`INSUFFICIENT_RISK_REWARD_RATIO` (1 rejection):**  
   Reward/Risk ratio calculated at 1.24, failing the mandatory production threshold of $R:R \ge 1.5$.

---

## 3. Discrepancy Resolution: Why 127 BUYs in AUDIT-015 Became 4 BUYs in AUDIT-016

A major finding of AUDIT-016 is the complete reconciliation between previous audit reports and the current point-in-time isolated execution:

### 3.1 Pre-Audit Lookahead Leakage (AUDIT-010 to AUDIT-015)
In previous audits, `analyze_roe`, `analyze_roce`, `analyze_debt_equity`, `analyze_profit_margin`, `analyze_growth`, and `analyze_valuation` did not apply `evaluation_date`. They queried the entire `quarterly_results` table:
* In `database/swing_trading.db`, exactly 5 quarterly rows exist per company: `2025-Q1`, `2025-Q2`, `2025-Q3`, `2025-Q4`, `2026-Q1`.
* When unconstrained by `evaluation_date`, all 5 quarters were analyzed on October 1, 2025.
* This gave `valuation_analyzer` 5 quarters (satisfying its $\ge 4$ quarter TTM requirement), generating valid financial health scores ($>70$) and manufacturing **127 raw BUY recommendations** across the bear market.

### 3.2 Point-in-Time Reality (AUDIT-016)
When temporal eligibility is strictly enforced under the documented 45-day fallback lag:
* Between `2025-10-01` and `2025-11-13`: Only **2 quarters** (`2025-Q1`, `2025-Q2`) were eligible.
* Between `2025-11-14` and `2026-02-13`: Only **3 quarters** (`2025-Q1`, `2025-Q2`, `2025-Q3`) were eligible.
* Because `valuation_analyzer` requires at least 4 quarterly EPS observations to compute TTM EPS, it returned `status = "INSUFFICIENT"`, resulting in `INSUFFICIENT_DATA` overall recommendations prior to February 14, 2026.
* On `2026-02-14`, `2025-Q4` became eligible under the 45-day lag rule (Period end `2025-12-31` + 45 days = `2026-02-14`), reaching the 4-quarter threshold.
* Consequently, during February and March 2026, **4 point-in-time valid BUY recommendations** were generated.
* All 127 historical BUYs are now 100% reconciled in [`AUDIT_016_REJECTION_LEDGER.csv`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/AUDIT_016_REJECTION_LEDGER.csv) and [`AUDIT_016_REJECTION_LEDGER.json`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/docs/audit_artifacts/AUDIT_016_REJECTION_LEDGER.json).

---

## 4. Persisted Performance Metrics

The simulation ran through `backend/logic/portfolio_simulator.py` and persisted to `docs/audit_artifacts/temp_pilot_audit_016.db` under run ID `pilot_audit_016_run`:

| Metric Name | Value | Audit Verification |
| :--- | :--- | :--- |
| **Initial Capital** | ₹100,000.00 | Verified |
| **Final Capital** | ₹100,000.00 | Verified |
| **Net Portfolio Return** | 0.00% | Verified |
| **Total Trades Executed** | 0 | Verified |
| **Total Trading Costs** | ₹0.00 | Verified |
| **Win Rate** | **N/A (Undefined)** | Corrected ($\frac{0}{0}$ is mathematically undefined) |
| **Profit Factor** | **N/A (Undefined)** | Corrected ($\frac{0}{0}$ is mathematically undefined) |
| **Max Drawdown** | 0.00% | Flat equity curve (122 trading days) |
| **Buy-and-Hold Benchmark Return** | -17.53% | Recalculated across TCS, INFY, HDFC, REL, ITC |
| **Net Benchmark Outperformance** | +17.53% | Result of cash preservation during bear market |

---

## 5. Production Database Isolation

* **Production DB Path:** `database/swing_trading.db`
* **Pre-Execution SHA256:** `10f40129fc710f7e49ab82d285a45f94591d19ef2ed05a74f071fb86efe92ad2`
* **Post-Execution SHA256:** `10f40129fc710f7e49ab82d285a45f94591d19ef2ed05a74f071fb86efe92ad2`
* **State Mutation:** ZERO BYTES MODIFIED (100% Database Isolation Verified).

