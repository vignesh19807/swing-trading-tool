# AUDIT-017: Independent Signal Reconciliation Verification

**Audit Identifier:** AUDIT-017-SIGNAL-RECONCILIATION  
**Execution Timestamp:** 2026-10-29 22:10 IST  
**Auditor:** Quantitative Trading System Auditor & Test Engineer  
**Universe:** 5 Benchmark Stocks (`TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `ITC`)  
**Evaluation Window:** `2025-10-01` to `2026-03-31` (122 trading days, 610 stock-sessions)  
**Database Used:** Isolated copy `docs/audit_artifacts/temp_pilot_audit_017.db`

---

## 1. Executive Summary

This independent audit reproduced the 5-stock historical pilot across all 610 stock-sessions under verified point-in-time fundamental isolation.

### Key Reconciliation Findings
1. **Total Stock-Sessions Evaluated:** 610
2. **Total Raw BUY Signals Generated:** **4**
3. **Total Signals Rejected by Trade Quality Filters:** **4 (100.0%)**
4. **Eligible Trades Executed:** **0 (0.0%)**
5. **Pre-Audit Lookahead Discrepancy Fully Explained:**
   - In AUDIT-015, 127 raw BUY recommendations were reported.
   - All 127 occurred prior to `2026-02-14` when unisolated sub-analyzers queried future quarters.
   - Under strict point-in-time isolation with 45-day lag, fewer than 4 quarters exist before `2026-02-14`, causing valuation and growth analyzers to correctly return `INSUFFICIENT_DATA`.
   - Only after `2026-02-14` (when Q4 2025 becomes eligible) do Opportunity Scores qualify for BUY.

---

## 2. Itemized Candidate Breakdown

The table below documents every single raw BUY signal generated during the 610-session evaluation under point-in-time isolation:

| Symbol | Evaluation Date | Financial Eligibility Status | Opp Score | Current Price (₹) | Support / Entry Zone (₹) | Stop-Loss (₹) | Target (₹) | Risk/Reward Ratio | Final Rec | Exact Rejection Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ITC** | `2026-02-17` | `PERIOD_ELIGIBLE_FALLBACK_LAG` (4 Qtrs) | 80.79 | 331.40 | [308.30, 311.96] | None (Entry filter failed) | None | N/A | BUY | `PRICE_OUTSIDE_ENTRY_ZONE` (Price ₹331.40 > Entry Upper ₹311.96) |
| **ITC** | `2026-02-18` | `PERIOD_ELIGIBLE_FALLBACK_LAG` (4 Qtrs) | 80.79 | 332.45 | [308.30, 311.99] | None (Entry filter failed) | None | N/A | BUY | `PRICE_OUTSIDE_ENTRY_ZONE` (Price ₹332.45 > Entry Upper ₹311.99) |
| **RELIANCE** | `2026-03-09` | `PERIOD_ELIGIBLE_FALLBACK_LAG` (4 Qtrs) | 76.05 | 1,424.00 | [1,400.00, 1,417.25] | None (Entry filter failed) | None | N/A | BUY | `PRICE_OUTSIDE_ENTRY_ZONE` (Price ₹1,424.00 > Entry Upper ₹1,417.25) |
| **RELIANCE** | `2026-03-20` | `PERIOD_ELIGIBLE_FALLBACK_LAG` (4 Qtrs) | 76.05 | 1,414.40 | [1,400.00, 1,416.59] (Inside entry zone) | 1,350.24 | 1,434.00 | **0.3055** | BUY | `INSUFFICIENT_RISK_REWARD_RATIO` (R:R 0.3055 < mandatory threshold 1.50) |

---

## 3. Discrepancy Analysis & Quality Gate Verification

### 3.1 Why 100% of Raw BUY Signals Were Rejected
1. **Breakout / Pullback Discipline (`PRICE_OUTSIDE_ENTRY_ZONE`):**  
   In 3 of 4 cases, the composite opportunity score signaled high technical and financial strength, but the market price had already extended substantially above nearest support (exceeding Support + 1.0 ATR). The trade quality filter correctly refused to chase extended prices.
2. **Asymmetric Risk Discipline (`INSUFFICIENT_RISK_REWARD_RATIO`):**  
   On `2026-03-20`, RELIANCE pulled back into its optimal entry zone [1400.00, 1416.59]. However, nearest structural resistance was located at ₹1434.00 while the ATR stop-loss required placement at ₹1350.24. This created a potential reward of ₹19.60 against a downside risk of ₹64.16 (R:R of 0.31:1). The production risk filter safely rejected the trade, adhering to the mandatory $\ge 1.50$ ratio.

---

## 4. Conclusion

The 4-signal reconciliation is verified. Under point-in-time isolation, no trades qualified for execution, successfully preserving 100% of capital during the pilot window.

