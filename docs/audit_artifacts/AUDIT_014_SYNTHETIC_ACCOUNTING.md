# AUDIT-014: Independent Verification of Synthetic Trade Accounting & Execution Friction

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Scope:** Independent recomputation of all quantitative trading calculations, friction models, and database isolation  
**Test Reference:** `backend/tests/test_audit_010_synthetic_trade.py`  
**Verification Date:** 2026-10-29  
**Execution Status:** **EXIT CODE 0 — 100% RECONCILED WITH INVARIANTS INTACT**

---

## 1. Test Isolation & Production Database Verification

- **Command:** `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe backend/tests/test_audit_010_synthetic_trade.py -v`
- **Exit Code:** `0` (1 passed in 1.85s)
- **Database Isolation Mechanism:**
  - In `test_audit_010_synthetic_trade.py`, `DATABASE_PATH` in `backend.config`, `backend.data_pipeline.backtest_result_service`, and `backend.app` is dynamically patched via `monkeypatch` to point to a temporary test database (`test_synthetic_backtest.db`) created inside pytest's isolated `tmp_path`.
- **Production Database Integrity Check:**
  - `database/swing_trading.db` SHA256 checksum prior to execution:  
    `a0bb12bdb016a75b8d5e028f691d17980a7a6a8bc9a7a691429cb2c09085367b`
  - `database/swing_trading.db` SHA256 checksum following execution:  
    `a0bb12bdb016a75b8d5e028f691d17980a7a6a8bc9a7a691429cb2c09085367b`
  - **Verdict:** True byte-for-byte identity. Zero synthetic trade data leaked into the active database.

---

## 2. Independent Step-by-Step Accounting Recomputation

### Parameters & Assumptions:
- **Starting Portfolio Capital:** ₹100,000.00
- **Allocation Rule:** Whole-share allocation, maximum 20% of capital per position (Max ₹20,000.00).
- **Signal:** BUY recommendation generated on `2026-01-01`.
- **Entry Execution:** Next-day open (`2026-01-02`), Open = ₹1,000.00.
- **Exit Execution:** Target reached on `2026-01-05` (Session High ₹1,060.00 $\ge$ Target ₹1,050.00).
- **Cost Model Configuration:**
  - Brokerage: ₹0.00 (Zero delivery brokerage)
  - STT: 0.1% on buy and 0.1% on sell turnover
  - NSE Exchange Charges: 0.00297%
  - SEBI Turnover Fee: 0.0001%
  - Stamp Duty: 0.015% on buy turnover only (exempt on sell)
  - GST: 18% on (Brokerage + Exchange + SEBI charges)
  - Slippage: 0.05% (adverse on both entry and exit)

---

### Comparison of Independent Recomputation vs System Output

| Metric / Parameter | Implementation Formula | Independent Expected Value | System Persisted Value | Variance |
| :--- | :--- | :---: | :---: | :---: |
| **Entry Slippage Multiplier** | $1.0 + 0.0005$ | $1.0005$ | $1.0005$ | 0.0000 |
| **Executed Entry Price** | $1000.00 \times 1.0005$ | ₹1,000.50 | ₹1,000.50 | 0.0000 |
| **Position Sizing (Quantity)** | $\lfloor 20000.00 / 1000.50 \rfloor$ | **19 shares** | **19 shares** | 0 shares |
| **Initial Position Value** | $19 \times 1000.50$ | ₹19,009.50 | ₹19,009.50 | ₹0.00 |
| **Exit Slippage Multiplier** | $1.0 - 0.0005$ | $0.9995$ | $0.9995$ | 0.0000 |
| **Executed Exit Price** | $1050.00 \times 0.9995$ | ₹1,049.475 | ₹1,049.475 | 0.0000 |
| **Gross Exit Turnover** | $19 \times 1049.475$ | ₹19,940.025 | ₹19,940.025 | ₹0.00 |
| **Entry STT (0.1%)** | $19009.50 \times 0.001$ | ₹19.0095 | ₹19.0095 | ₹0.00 |
| **Entry Exchange (0.00297%)**| $19009.50 \times 0.0000297$| ₹0.5646 | ₹0.5646 | ₹0.00 |
| **Entry SEBI (0.0001%)** | $19009.50 \times 0.000001$ | ₹0.0190 | ₹0.0190 | ₹0.00 |
| **Entry Stamp Duty (0.015%)**| $19009.50 \times 0.00015$ | ₹2.8514 | ₹2.8514 | ₹0.00 |
| **Entry GST (18%)** | $0.18 \times (0.56458 + 0.01901)$ | ₹0.1050 | ₹0.1050 | ₹0.00 |
| **Subtotal Entry Costs** | Sum of above | **₹22.5495** | **₹22.5495** | ₹0.00 |
| **Exit STT (0.1%)** | $19940.025 \times 0.001$ | ₹19.9400 | ₹19.9400 | ₹0.00 |
| **Exit Exchange (0.00297%)** | $19940.025 \times 0.0000297$| ₹0.5922 | ₹0.5922 | ₹0.00 |
| **Exit SEBI (0.0001%)** | $19940.025 \times 0.000001$ | ₹0.0199 | ₹0.0199 | ₹0.00 |
| **Exit Stamp Duty (0%)** | Exempt | ₹0.00 | ₹0.00 | ₹0.00 |
| **Exit GST (18%)** | $0.18 \times (0.59222 + 0.01994)$ | ₹0.1102 | ₹0.1102 | ₹0.00 |
| **Subtotal Exit Costs** | Sum of above | **₹20.6623** | **₹20.6623** | ₹0.00 |
| **Total Round-Trip Costs** | Entry Costs + Exit Costs | **₹43.2118** | **₹43.2118** | ₹0.00 |
| **Gross Realized P/L** | Exit Turnover - Entry Value | **₹930.5250** | **₹930.5250** | ₹0.00 |
| **Net Realized P/L** | Gross P/L - Total Costs | **₹887.3132** | **₹887.3132** | ₹0.00 |
| **Final Portfolio Cash** | Initial Cash + Net Realized P/L | **₹100,887.3132** | **₹100,887.3132**| ₹0.00 |
| **Net Return %** | $(\text{Net P\&L} / \text{Initial}) \times 100$ | **+0.8873%** | **+0.8873%** | 0.0000% |

---

## 3. Accounting Invariant & Double Deduction Checks

1. **No Double Deduction:**
   Total transaction costs (₹43.2118) are deducted exactly once from the gross profit. They are not applied to cash before position entry nor deducted a second time during equity curve valuation.
2. **Cash Conservation Invariant:**
   $$\Delta \text{Portfolio Cash} = ₹100,887.3132 - ₹100,000.00 = +₹887.3132 \equiv \text{Net Realized P\&L}$$
   The invariant holds with 100% mathematical precision.

---

## 4. Methodological Distinction: Mechanism vs Alpha

> [!IMPORTANT]
> **This synthetic trade test is strictly a verification of accounting mechanisms and software execution plumbing.**  
> It proves that the order management logic, whole-share rounding, bidirectional slippage model, statutory regulatory fee calculator, and database persistence operate correctly and without arithmetic defects.  
> **It does NOT constitute proof of trading strategy profitability, statistical expectancy, or real-world market alpha.**

