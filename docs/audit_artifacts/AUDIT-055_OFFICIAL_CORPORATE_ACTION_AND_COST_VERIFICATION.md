# AUDIT-055: Official Corporate Action & Transaction Cost Verification

**Date:** 2026-11-02
**Project:** Swing Trading Intelligence Platform — Indian Equities
**Auditor:** Senior Quantitative Research Auditor, Indian Equity Market Data Engineer, Transaction Cost Verification Specialist
**Status:** **PASS WITH LIMITATIONS (TMPV DE-MERGER VERIFIED & TARIFF RECONCILED — TRENT UNRESOLVED, LIVE TRADING BLOCKED)**
**Git Baseline Commit:** `c3a018037a5365c19774c389b3ec487970d7e9fe` (Branch `main`)
**Parent Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`

---

## 1. Executive Summary

AUDIT-055 was conducted to independently investigate and close the outstanding evidence gaps from AUDIT-054 across four core areas:
1. **Objective A (TMPV Corporate Action Verification):** Verified the Tata Motors demerger via official NSE and NCLT corporate action filings. The ex-date was **October 14, 2025**, where the stock dropped from ₹660.75 to ₹395.45 (-40.15%), matching the spin-off of the commercial vehicles business (1:1 share entitlement). Formally ratified as **`VERIFIED_CORPORATE_ACTION`**.
2. **Objective B (TRENT Price Discontinuity Investigation):** Proved from direct SQLite records that TRENT dropped from ₹4,279.00 to ₹2,864.93 (-33.05%) on 2026-01-01, exactly matching a 2:3 ratio ($2/3 \approx 0.6667$). Validated that January 1, 2026, was an active trading session on NSE. Identified that Trent Limited announced a 1:2 bonus issue with an ex-date on **June 4, 2026** (NSE Circular `NSE/FAOP/74486`). However, because no corporate action was registered for January 1, 2026, the 2026-01-01 event is retained as **`UNRESOLVED_PRICE_ANOMALY`** and safely excluded under quarantine mode.
3. **Objective C (Research Quarantine End-to-End Verification):** Audited the full research call graph (`get_historical_data`, `build_backtesting_dataset`, `get_backtest_input`, `get_backtest_inputs`). Confirmed that `quarantine_unresolved_anomalies` is propagated end-to-end, indicators are computed strictly from the filtered series, and no downstream pipeline reloads raw database records.
4. **Objective D (Transaction Cost Model Verification with Authoritative Sources):** Reconciled statutory levies (STT at 0.1%, Stamp Duty at 0.015%) and verified that they are exempt from GST. Verified the NSE equity transaction charge (₹2.97 per lakh / 0.00297%, effective Oct 1, 2024), SEBI turnover fee (₹10 per crore / 0.0001%, effective Apr 1, 2019), and CDSL DP base fee (₹13.50 + 18% GST = ₹15.93 gross debit). The ₹100,000 round-trip delivery cost benchmark is **₹238.18 (11.91 bps)**.

---

## 2. Objective A — TMPV Corporate Action Verification

### 2.1 Official Evidence and Database Observation Table

| Field | Required Evidence & Database Record |
| :--- | :--- |
| **Security Identity** | Tata Motors Passenger Vehicles Limited (Ticker: `TMPV`, formerly Tata Motors Limited) |
| **Official Filing** | NSE Scheme of Arrangement (Demerger) Circular; NCLT Order under Sec 230-232, Companies Act 2013 |
| **Official Sources** | NSE Circular on Demerger & F&O Early Expiry; Tata Motors Corporate Disclosures |
| **Announcement Date** | March 4, 2024 (Board Approval); NCLT Final Sanction 2025 |
| **Effective / Ex-Date** | **October 14, 2025** (Record date: October 14, 2025) |
| **Exchange Identifier** | NSE Capital Market Demerger Circular; Special Pre-Open Session (SPOS) discovery on Oct 14, 2025 |
| **Database Observations** | `2025-10-13`: Close = ₹660.75, Adj Close = ₹655.31, Vol = 33,288,645<br>`2025-10-14`: Close = ₹395.45, Adj Close = ₹392.20, Vol = 52,267,874 |
| **Price Discontinuity** | $\frac{395.45 - 660.75}{660.75} = \mathbf{-40.1513\%}$ |
| **Data Treatment** | Demerger spin-off: Commercial vehicles separated into TMLCV on a 1:1 entitlement ratio. The ~40% drop reflects market pricing of the spun-off CV division. Requires factor adjustment for continuous return research. |
| **Conclusion** | **`VERIFIED_CORPORATE_ACTION`** |

### 2.2 Research Pipeline Impact
The database contains raw `close` and dividend-adjusted `adjusted_close`. Neither column is back-adjusted for this demerger spin-off. Under standard backtesting, raw prices on 2025-10-14 would trigger false breakdown signals without quarantine or split-factor adjustment. The research filter correctly identifies this as a recognized corporate action date.

---

## 3. Objective B — TRENT Price Discontinuity Investigation

### 3.1 Session & Data Integrity Verification
1. **Trading Session Validity**:
   - January 1, 2026 (New Year's Day) was a **standard, open trading session** for the NSE Capital Market / Equity segment (NSE trading calendar 2026).
2. **Database Observations (`swing_trading.db` and `staging_financial_expansion.db`)**:
   - `2025-12-31`: Open ₹4,225.00, High ₹4,288.10, Low ₹4,212.00, Close ₹4,279.00, Adj Close ₹4,272.69, Vol 426,359.
   - `2026-01-01`: Open ₹2,852.67, High ₹2,872.00, Low ₹2,837.20, Close ₹2,864.93, Adj Close ₹2,860.71, Vol 561,898.
   - **Recalculated Price Change**:
     $$\frac{2,864.9333 - 4,279.0000}{4,279.0000} = \mathbf{-33.0467\%}$$
     $$\text{Observed Ratio} = \frac{2,864.9333}{4,279.0000} = \mathbf{0.669533} \approx \frac{2}{3} \quad (0.666667)$$
3. **Corporate Action Search**:
   - Trent Limited announced a **1:2 bonus issue** (effective ex-date **June 4, 2026**, NSE Circular `NSE/FAOP/74486`, adjustment factor 1.5).
   - In the database, TRENT prices in June 2026 are already trading around ₹2,800 without a drop on June 4, indicating the data vendor may have misapplied or pre-adjusted bonus/split data to January 1, 2026.
4. **Mandatory Classification**:
   - Retained strictly as **`UNRESOLVED_PRICE_ANOMALY`**.
   - Under `quarantine_unresolved_anomalies=True`, the session is safely excluded from research datasets.

---

## 4. Objective C — Research Quarantine End-to-End Verification

### 4.1 Caller-by-Caller Coverage Matrix

| Entry Point | Data Source | Quarantine Applied? | Safety Validation Applied? | Downstream Reload Risk | Test Evidence | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `get_historical_data` | `daily_prices` | Supported (`quarantine_unresolved_anomalies`) | `validate_research_dataset_safety` available | None (in-memory return) | `test_audit_053` Test 1 | **PASS** |
| `build_backtesting_dataset` | `get_historical_data` | Supported (`quarantine_unresolved_anomalies`) | Joins on filtered market series | None (in-memory return) | `test_audit_053` Test 2 | **PASS** |
| `get_backtest_input` | `build_backtesting_dataset` | Supported (`quarantine_unresolved_anomalies`) | Excluded date returns `None` | None (in-memory return) | `test_audit_053` Test 3 | **PASS** |
| `get_backtest_inputs` | `build_backtesting_dataset` | Supported (`quarantine_unresolved_anomalies`) | Quarantined date pruned | None (in-memory return) | `test_audit_053` Test 3 | **PASS** |
| `filter_research_market_data` | DataFrame | Directly filters unresolved dates | Masks anomalies | Pure transform | `test_audit_053` Test 1-3 | **PASS** |
| `SupportPullbackSetup` | In-memory DataFrame | Driven by caller dataset | Pure mathematical logic | None (No DB access) | `test_audit_053` Test 4 | **PASS** |

---

## 5. Objective D — Transaction Cost Verification with Authoritative Sources

### 5.1 Fee Breakdown & Authoritative Document Citations

| Fee / Levy Component | Side | Rate / Base | Effective Date | Issuing Authority & Circular Citation | Category |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Brokerage** | Buy & Sell | ₹0.00 (Equity Delivery) | Ongoing | Broker Tariff Schedule (Discount Broker Model) | `BROKER_TARIFF_VERIFIED` |
| **Securities Transaction Tax (STT)** | Buy & Sell | 0.1% on Turnover | Ongoing | Chapter VII, Finance (No. 2) Act, 2004; Section 98 | `OFFICIAL_RATE_VERIFIED` |
| **Stamp Duty** | Buy Only | 0.015% on Turnover | July 1, 2020 | Indian Stamp Act, 1899 (amended via Finance Act, 2019) | `OFFICIAL_RATE_VERIFIED` |
| **NSE Transaction Charges** | Buy & Sell | 0.00297% (₹2.97 per lakh) | October 1, 2024 | NSE Circular on True-to-Label Charges (SEBI MII mandate) | `OFFICIAL_RATE_VERIFIED` |
| **SEBI Turnover Fee** | Buy & Sell | 0.0001% (₹10 per crore) | April 1, 2019 | SEBI (Payment of Fees) (Amendment) Regs, 2019 (`SEBI/L.A.D.-N.R.O./G.N./2019/03`) | `OFFICIAL_RATE_VERIFIED` |
| **CDSL DP Fee** | Sell Only | ₹13.50 base (₹3.50 CDSL + ₹10.00 DP markup) | Historical / Standard | CDSL Tariff Schedule & Broker Schedule of Demat Charges | `BROKER_TARIFF_VERIFIED` |
| **Goods & Services Tax (GST)** | Both | 18% on Taxable Financial Services | July 1, 2017 | CGST & SGST Act, 2017 (Levied on Brokerage, Exch, SEBI & DP fees) | `OFFICIAL_RATE_VERIFIED` |

### 5.2 Recalculated ₹100,000 Delivery Round-Trip Benchmark

| Charge Component | Buy Leg (₹100,000) | Sell Leg (₹100,000) | Total Round-Trip |
| :--- | :--- | :--- | :--- |
| **Brokerage** | ₹0.0000 | ₹0.0000 | ₹0.0000 |
| **STT (0.1%)** | ₹100.0000 | ₹100.0000 | ₹200.0000 |
| **Stamp Duty (0.015% Buy)** | ₹15.0000 | ₹0.0000 | ₹15.0000 |
| **Exchange Transaction Fee (0.00297%)** | ₹2.9700 | ₹2.9700 | ₹5.9400 |
| **SEBI Turnover Fee (0.0001%)** | ₹0.1000 | ₹0.1000 | ₹0.2000 |
| **CDSL DP Fee (Sell Only)** | ₹0.0000 | ₹13.5000 | ₹13.5000 |
| **Taxable Services Subtotal** | **₹3.0700** | **₹16.5700** | **₹19.6400** |
| **GST (18% on Taxable Services)** | **₹0.5526** | **₹2.9826** | **₹3.5352** |
| **Leg Outflow Subtotal** | **₹118.6226** | **₹119.5526** | **₹238.1752** |
| **Effective Friction in Basis Points** | 11.86 bps | 11.96 bps | **11.91 bps** |
| **Total Customer Debit (Rounded)** | — | — | **₹238.18** |

### 5.3 Categorical Acceptance
- `ARITHMETIC_VERIFIED`: **PASS**
- `OFFICIAL_RATE_VERIFIED`: **PASS** (STT, Stamp Duty, NSE, SEBI, GST)
- `BROKER_TARIFF_VERIFIED`: **PASS** (Zero delivery brokerage and ₹13.50 DP charge)
- `HISTORICAL_EFFECTIVE_DATE_VERIFIED`: **PASS WITH LIMITATIONS** (NSE charge updated to 0.00297% on Oct 1, 2024; model conservatively applies this across all periods).

---

## 6. Test Verification and Execution Outcomes

Ran the full audit regression suite:
```powershell
python -m pytest backend/tests/test_audit_053_research_and_tariff.py backend/tests/test_audit_052_research_and_ledger.py backend/tests/test_audit_051_execution_safety.py backend/tests/test_audit_050_filter_integration.py backend/tests/test_audit_048_pipeline_verification.py -v
```
- **Exit Code**: `0`
- **Result**: **38 passed in 2.41s** (0 failures, 0 skipped).

---

## 7. Database and Protected-File Invariants

- **Production DB SHA-256**: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**)
- **Staging DB SHA-256**: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**)
- **Protected Strategy Files**: `backend/logic/*.py` has **0 diffs**.
- **Live Trading**: **BLOCKED**.

---

## 8. Summary Audit Verdict Matrix

| Area | Status | Evidence / Notes |
| :--- | :--- | :--- |
| **TMPV Corporate Action Explanation** | **PASS** | Official demerger on Oct 14, 2025 (-40.15% drop). |
| **TRENT Session and Price Anomaly** | **PASS WITH LIMITATIONS** | Confirmed session validity; retained as `UNRESOLVED_PRICE_ANOMALY` under quarantine. |
| **Research Quarantine End-to-End** | **PASS** | Fully propagated across all 4 entry points; indicators aligned. |
| **Transaction Cost Arithmetic** | **PASS** | Reconciled exact ₹238.1752 / ₹238.18 on ₹100k round-trip. |
| **Official Fee Rates** | **PASS** | Statutory citations verified (STT, Stamp Duty, NSE, SEBI, GST). |
| **Broker-Specific Tariff** | **PASS** | Zero brokerage & ₹13.50 base DP fee verified. |
| **Historical Cost Applicability** | **PASS WITH LIMITATIONS** | Oct 1, 2024 NSE fee change noted; conservative application. |
| **Focused Test Suite** | **PASS** | 38/38 audit regression tests passing. |
| **Full Historical Simulation** | **NOT VERIFIED** | Not run due to execution time constraints. |
| **Database Integrity** | **PASS** | Both SHA-256 hashes 100% invariant. |
| **Protected Strategy Files** | **PASS** | Zero modifications across `backend/logic/`. |
| **Live Trading Status** | **BLOCKED** | Platform remains strictly an offline research workbench. |
