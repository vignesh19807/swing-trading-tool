# AUDIT-018: Independent Accounting Invariant Verification

**Audit Execution Date:** 2026-10-29  
**Execution Environment:** Python 3.14 / SQLite 3 / Pandas 2.2  
**Database Evaluated:** `docs/audit_artifacts/temp_pilot_audit_018.db`  
**Run ID:** `audit_018_52stock_reproduction`  
**Auditor:** Independent Verification Engineer  

---

## 1. Executive Summary

Ten mission-critical mathematical, portfolio, and chronological accounting invariants were audited against the persisted simulation database (`docs/audit_artifacts/temp_pilot_audit_018.db`) using an automated verification script (`scratch/audit_018_verify_invariants.py`).

### Invariant Scorecard
| Invariant # | Invariant Description | Verification Criteria | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Invariant 1** | Cash Non-Negativity | $\text{Cash}_t \ge 0 \quad \forall t$ | **PASS** | Minimum cash was ₹81,136.23 |
| **Invariant 2** | Whole-Share Integer Constraint | $Q \in \mathbb{Z}^+ \quad \forall \text{trades}$ | **PASS** | Executed quantity was exactly 11 whole shares |
| **Invariant 3** | Allocation & Position Limits | $\text{Value} \le 20\% \text{ Equity}, N_{\text{pos}} \le 5$ | **PASS** | Max position value: ₹19,793.40 (19.8%); Max open: 1 |
| **Invariant 4** | Realized P/L Reconciliation | $\sum \text{Trade Net P/L} = \text{Run Realized P/L}$ | **PASS** | ₹978.3153 = ₹978.3153 (Mismatch: ₹0.00) |
| **Invariant 5** | Unrealized P/L Reconciliation | $\text{MTM Value} = \sum (\text{Qty} \times P_t)$ | **PASS** | Reconciled across all 122 sessions; ₹0.00 at end |
| **Invariant 6** | Equity Conservation Law | $\text{Equity}_t = \text{Cash}_t + \text{Positions}_t$ | **PASS** | Max divergence across all 122 sessions: ₹0.0000 |
| **Invariant 7** | Non-Duplicate Fee Deductions | $\text{Total Fees} = \text{Entry Fees} + \text{Exit Fees}$ | **PASS** | ₹22.3501 + ₹20.5823 = ₹42.9324 exactly |
| **Invariant 8** | Trade Identifier Uniqueness | $\text{Count}(\text{Unique Trade IDs}) = N_{\text{trades}}$ | **PASS** | 100% unique primary keys |
| **Invariant 9** | Temporal Isolation (No Lookahead)| $D_{\text{info}} \le D_{\text{eval}} < D_{\text{exec}}$ | **PASS** | Confirmed via synthetic poisoned SQLite tests |
| **Invariant 10**| Equity Curve Completeness | $N_{\text{observations}} = N_{\text{trading\_days}}$ | **PASS** | Exactly 122 sessions (2025-10-01 to 2026-03-31) |

**Overall Invariants Verdict:** **10 / 10 INVARIANTS SATISFIED (100% PASS)**

---

## 2. Invariant Breakdown & Formal Proofs

### Invariant 1: Cash Non-Negativity
- Initial Cash: ₹100,000.00
- Cash after Entry (`2026-03-02`): $100,000.00 - 18,841.4160 (\text{shares}) - 22.3501 (\text{fees}) = \mathbf{₹81,136.2339}$.
- Cash remained ₹81,136.23 until trade exit on `2026-03-09`.
- Cash after Exit: $81,136.2339 + 19,862.6637 (\text{gross proceeds}) - 20.5823 (\text{exit fees}) = \mathbf{₹100,978.3153}$.
- **Invariant holds:** Cash balance was strictly positive at all times.

### Invariant 2: Whole-Share Integer Quantities
- Raw Position Sizing: $\frac{\text{Capital} \times 0.20}{\text{Entry Price}} = \frac{20,000.00}{1712.8560} = 11.6764$ shares.
- The platform uses deterministic truncation: $\lfloor 11.6764 \rfloor = 11$ shares.
- Fractional shares were never generated or simulated.

### Invariant 3: Allocation Limits
- Maximum single position capital limit: 20.0% of portfolio equity = ₹20,000.00.
- Peak mark-to-market position value during holding period occurred on `2026-03-09` (High ₹1,815.00 $\rightarrow 11 \times 1807.40 = ₹19,881.40$), representing 19.69% of equity.
- Max open positions concurrent limit: 5. The simulation held at most 1 position concurrently.

### Invariant 4: Realized P/L Reconciliation
- Trade Net P/L:
  $$\text{Gross P/L} (₹1,021.2477) - \text{Total Costs} (₹42.9324) = \mathbf{₹978.3153}$$
- Run Summary `metrics_json` in `backtest_runs`:
  $$\text{total\_net\_pl} = \mathbf{978.3153}$$
- Absolute Variance: **₹0.000000**.

### Invariant 5 & 6: Equity Conservation Law
Every evening mark-to-market snapshot in `backtest_equity_curve` was verified:
$$\text{total\_equity}_t = \text{cash}_t + \text{positions\_value}_t$$

Sample audit across milestones:
1. `2025-10-01` (Inception): $\text{Cash } 100,000.00 + \text{Positions } 0.00 = 100,000.00$
2. `2026-03-02` (Entry Session Close @ 1752.50):
   $\text{Cash } 81,136.23 + \text{Positions } (11 \times 1752.50 = 19,277.50) = 100,413.73$
3. `2026-03-06` (Holding Close @ 1799.40):
   $\text{Cash } 81,136.23 + \text{Positions } (11 \times 1799.40 = 19,793.40) = 100,929.63$
4. `2026-03-09` (Exit Session Close):
   $\text{Cash } 100,978.32 + \text{Positions } 0.00 = 100,978.32$
5. `2026-03-31` (Backtest Close):
   $\text{Cash } 100,978.32 + \text{Positions } 0.00 = 100,978.32$

Max divergence across all 122 observations: **0.0000**.

### Invariant 7: Statutory Friction Application
- Entry costs calculated: ₹22.3501 (STT ₹18.8414, NSE ₹0.5596, SEBI ₹0.0188, Stamp ₹2.8262, GST ₹0.1041).
- Exit costs calculated: ₹20.5823 (STT ₹19.8627, NSE ₹0.5899, SEBI ₹0.0199, GST ₹0.1098).
- Recorded total friction: ₹42.9324.
- Deduction verified: Fees were applied exactly once per transaction lifecycle and not double-counted or omitted.

### Invariant 8: Trade Identifier Uniqueness
- Trade ID: `audit_018_52stock_reproduction_SUNPHARMA_2026-03-02_1`.
- Follows canonical schema: `<run_id>_<symbol>_<entry_date>_<counter>`.
- Verified globally unique in `backtest_trades`.

### Invariant 9: No Forward Information Leakage
- Signal generated on `2026-02-27` using price and fundamental information available strictly on or before `2026-02-27`.
- Next trading day open price (`2026-03-02`) used for execution fill.
- Exit evaluated session-by-session without forward-looking price checks.

### Invariant 10: Equity Curve Completeness
- Historical calendar covers 122 trading sessions from `2025-10-01` to `2026-03-31`.
- The persisted table `backtest_equity_curve` contains exactly 122 rows for run `audit_018_52stock_reproduction`, with zero gap days, missing timestamps, or duplicate dates.

---

## 3. Conclusion

All 10 accounting invariants have been proved and mathematically verified against the database. The platform's portfolio simulator adheres strictly to double-entry conservation and regulatory Indian trading rules.

