# AUDIT-015: Isolated Controlled Pilot Execution Report

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Pilot Identification:** `pilot_audit_015_run`  
**Execution Database:** Isolated temporary SQLite database (`docs/audit_artifacts/temp_pilot_audit_015.db`)  
**Production Database:** `database/swing_trading.db` (Read-only reference)  
**Execution Date:** 2026-10-29  
**Status:** **EXECUTION SUCCESSFUL (EXIT CODE 0) — ZERO PRODUCTION MUTATION**

---

## 1. Database Isolation Verification

- **Isolation Strategy:** `backend.config.DATABASE_PATH` and `backend.data_pipeline.backtest_result_service.DATABASE_PATH` were programmatically overridden with `Path(os.path.abspath("docs/audit_artifacts/temp_pilot_audit_015.db"))`.
- **Pre-Execution Production DB SHA256:** `10f40129fc710f7e49ab82d285a45f94591d19ef2ed05a74f071fb86efe92ad2`
- **Post-Execution Production DB SHA256:** `10f40129fc710f7e49ab82d285a45f94591d19ef2ed05a74f071fb86efe92ad2`
- **Isolation Check:** **PASSED**. Bit-for-bit checksum identity confirms zero writes, updates, or table locks touched the active application database.

---

## 2. Signal Generation & Sequential Risk Screening Log

All 610 stock-sessions (122 market dates × 5 stocks: `TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `ITC`) were evaluated using the production pipeline:

```
Loaded 122 market dates across 5 symbols (610 total sessions)
Total Raw BUY Signals: 127
Rejection Breakdown:
  INSUFFICIENT_RISK_REWARD_RATIO: 27
  PRICE_OUTSIDE_ENTRY_ZONE: 96
  TARGET_BELOW_CURRENT_PRICE: 2
  TARGET_BELOW_ENTRY_PRICE: 2
Eligible Signals forwarded to Simulator: 0
```

### Rejection Gate Diagnostic:
1. **Gate 1 — Entry Zone Gate:** Price must reside within $[Support, Support + 1.0\% \times ATR_{14}]$.
   - **96 recommendations rejected** (`PRICE_OUTSIDE_ENTRY_ZONE`). The market price was too extended above the support zone pullback boundary.
   - **31 recommendations passed** Gate 1.
2. **Gate 2 — Exit Sanity Gate:** Target must be strictly greater than entry and current price.
   - **2 recommendations rejected** with `TARGET_BELOW_CURRENT_PRICE`.
   - **2 recommendations rejected** with `TARGET_BELOW_ENTRY_PRICE`.
   - **27 recommendations passed** Gate 2.
3. **Gate 3 — Risk-Reward Ratio Gate:** Potential reward / risk must be $\ge 1.5$.
   - **All 27 remaining recommendations rejected** (`INSUFFICIENT_RISK_REWARD_RATIO`). The distance to the nearest overhead resistance level provided inadequate reward relative to the required ATR-based stop loss.
4. **Final Eligible Signals Forwarded to Simulator:** **0**.

---

## 3. Simulator Execution & Transaction Accounting

Because 0 signals passed all defensive risk gates:
- **Executed Orders:** 0
- **Closed Positions:** 0
- **Open Positions:** 0
- **Gross P/L:** ₹0.00
- **Transaction Costs (STT, NSE, SEBI, Stamp Duty, GST):** ₹0.00
- **Net Realized P/L:** ₹0.00
- **Cash Balance:** ₹100,000.00 (Unchanged)
- **Portfolio Equity:** ₹100,000.00 (Unchanged)
- **Equity Curve:** 122 daily points recorded, flat at ₹100,000.00.

---

## 4. Multi-Table Persistence Reconciliation

The run was transactionally persisted to `temp_pilot_audit_015.db`:
- `backtest_runs`: 1 run record (`pilot_audit_015_run`, status `COMPLETED`, metrics JSON validated).
- `backtest_trades`: 0 trade records.
- `backtest_equity_curve`: 122 daily equity curve records from `2025-10-01` to `2026-03-30`.
- All persisted entities reconciled with the memory simulator output with 100% consistency.

---

## 5. Architectural Finding on Zero Trades

> [!NOTE]
> **Zero trades executed is the mathematically correct and intended outcome of the platform's multi-layered defensive risk architecture.**  
> The system functioned exactly according to specification: it identified 127 high-conviction fundamental/momentum candidates, but refused to commit capital because market prices were either extended beyond support or failed the minimum 1.5 risk-reward hurdle.  
> In strict accordance with audit guidelines, **no trading rules were altered or loosened to manufacture artificial trades**.

