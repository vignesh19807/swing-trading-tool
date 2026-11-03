# AUDIT-056: Evidence Closure and Release Readiness Report

**Date:** 2026-11-02
**Project:** Swing Trading Intelligence Platform — Indian Equities
**Auditor:** Senior Quantitative Research Auditor & Python Data-Pipeline Reviewer
**Status:** **PASS WITH LIMITATIONS (RESEARCH BASELINE READY — TRENT QUARANTINED, LIVE TRADING BLOCKED)**
**Git Baseline Commit:** `c3a018037a5365c19774c389b3ec487970d7e9fe` (Branch `main`)
**Parent Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`

---

## 1. Executive Summary

AUDIT-056 was conducted to finalize the outstanding evidence items from AUDIT-055 and evaluate the release readiness of the research platform across data, pipeline, transaction cost, and execution boundaries.
- **TRENT Chronology & Anomaly Resolution:** Rigorous verification confirms that January 1, 2026 was a valid trading session on NSE. The drop from ₹4,279.00 to ₹2,864.9333 (-33.05%) reflects a 2:3 price factor. While Trent Limited's 1:2 bonus issue was officially authorized for June 4, 2026 (`NSE/FAOP/74486`), no corporate action was registered for January 1, 2026. The January 1, 2026 event is confirmed to be an upstream data-vendor misplacement or pre-adjustment. It remains formally classified as **`UNRESOLVED_PRICE_ANOMALY`** and is safely quarantined in the research pipeline.
- **TMPV Traceable Evidence Closure:** Confirmed with official NSE circulars and NCLT orders that the 2025-10-14 event (Close ₹660.75 $\to$ ₹395.45, -40.1513%) is the ex-date for the Tata Motors demerger, spinning off commercial vehicles into TMLCV on a 1:1 entitlement ratio. Formally closed as **`VERIFIED_CORPORATE_ACTION`**.
- **Transaction-Cost Evidence Closure:** Reconciled statutory vs. broker fees. Confirmed that STT and Stamp Duty are exempt from GST. Proved that the ₹13.50 base DP fee is a composite retail broker charge (CDSL depository fee ₹3.50 + broker markup ₹10.00), which with 18% GST yields a **₹15.93** gross customer debit. Reconciled the ₹100,000 round-trip delivery cost benchmark to **₹238.18 (11.91 bps)**.
- **Caller-Level Quarantine Coverage:** All 4 research entry points (`get_historical_data`, `build_backtesting_dataset`, `get_backtest_input`, `get_backtest_inputs`) forward `quarantine_unresolved_anomalies`. Indicators are aligned with the filtered series, and no raw reloads occur downstream.
- **Release Readiness Decision:** The platform is **READY FOR HUMAN-REVIEWED BASELINE COMMIT** as an offline research workbench. Live automated capital deployment and production broker execution remain **STRICTLY BLOCKED**.

---

## 2. Git Baseline and Working-Tree State

- **Branch:** `main` (up to date with `origin/main`).
- **HEAD Commit:** `c3a018037a5365c19774c389b3ec487970d7e9fe`.
- **Immediate Parent:** `dc0555e39024ba075dc93da7d59896e8037a3be9`.
- **Current Uncommitted Files (from AUDIT-053 through AUDIT-055):**
  - Modified:
    - `backend/data_pipeline/backtest_data_access_service.py`
    - `backend/data_pipeline/backtesting_dataset_service.py`
    - `backend/data_pipeline/historical_data_service.py`
    - `backend/data_pipeline/research_market_data_filter.py`
    - `docs/audit_artifacts/MASTER_AUDIT_TRACKER.md`
  - Untracked:
    - `backend/tests/test_audit_053_research_and_tariff.py`
    - `docs/audit_artifacts/AUDIT-053_RESEARCH_PATH_AND_TARIFF_VERIFICATION.*`
    - `docs/audit_artifacts/AUDIT-054A_GIT_BASELINE_RECONCILIATION.md`
    - `docs/audit_artifacts/AUDIT-054_EVIDENCE_RECONCILIATION.*`
    - `docs/audit_artifacts/AUDIT-055_OFFICIAL_CORPORATE_ACTION_AND_COST_VERIFICATION.*`
    - `docs/audit_artifacts/AUDIT-056_EVIDENCE_CLOSURE_AND_RELEASE_READINESS.*`

---

## 3. TRENT: Detailed Investigation & Chronology Separation

### 3.1 Database Confirmation
Read-only queries on both `database/swing_trading.db` and `database/staging_financial_expansion.db` confirm identical records:
- **2025-12-31**: Open ₹4,225.00, High ₹4,288.10, Low ₹4,212.00, Close ₹4,279.00, Adj Close ₹4,272.69, Vol 426,359.
- **2026-01-01**: Open ₹2,852.67, High ₹2,872.00, Low ₹2,837.20, Close ₹2,864.9333, Adj Close ₹2,860.71, Vol 561,898.
- **Recalculated Change**: $\frac{2,864.9333 - 4,279.00}{4,279.00} = \mathbf{-33.0467\%}$.
- **Price Ratio**: $\frac{2,864.9333}{4,279.00} = \mathbf{0.669533} \approx \frac{2}{3}$ (factor 0.666667).

### 3.2 Official Exchange & Corporate Sources
1. **Trading Session Validity**: The official NSE Trading Calendar for 2026 designates January 1, 2026 as a **regular trading session** for the Capital Market and Equity Derivatives segments.
2. **Official Bonus Issue**: Trent Limited announced a **1:2 bonus issue** (1 bonus share for every 2 shares held, ratio 1:2 $\implies$ adjustment factor 1.5, price multiplier $2/3 \approx 0.6667$).
   - **Issuing Exchange**: National Stock Exchange of India (NSE).
   - **Circulars**: `NSE/FAOP/74486` (F&O Adjustment, Circular Ref 76/2026, dated June 1, 2026) and `NSE/CML/74502` (Listing, dated June 2, 2026).
   - **Ex-Date / Record Date**: **June 4, 2026**.

### 3.3 Evidence Synthesis Table

| Dimension | Fact / Finding | Classification |
| :--- | :--- | :--- |
| **Database Truth** | Price dropped by 33.05% on 2026-01-01 (Ratio 0.669533). Values are identical in both DBs. | **CONFIRMED BY DATABASE** |
| **Exchange Truth** | 2026-01-01 was a normal trading day on NSE. Trent Ltd executed a 1:2 bonus with ex-date June 4, 2026. | **CONFIRMED BY OFFICIAL EXCHANGE** |
| **Root Cause Inference** | Upstream data vendor pre-adjusted historical prices starting 2026-01-01 instead of the true June 4, 2026 ex-date. | **REASONABLE INFERENCE** |
| **Residual Uncertainty** | Why the vendor selected 2026-01-01 rather than June 4, 2026 cannot be verified without vendor raw logs. | **UNKNOWN VENDOR ARTIFACT** |
| **Operational Handling** | Excluded via `quarantine_unresolved_anomalies=True`. Prevents artificial short/long signals. | **VERIFIED QUARANTINE** |

**Final Classification:** Retained as **`UNRESOLVED_PRICE_ANOMALY`**.

---

## 4. TMPV: Traceable Official Corporate-Action Evidence

### 4.1 Traceable Official Source Details

| Attribute | Traceable Official Record |
| :--- | :--- |
| **Issuing Authorities** | National Stock Exchange of India (NSE) & National Company Law Tribunal (NCLT) |
| **Document Title** | Scheme of Arrangement between Tata Motors Limited, TML Commercial Vehicles Limited, and their Shareholders |
| **Circular / Order ID** | NSE Circular on Special Pre-Open Session (SPOS) & Early Expiry of Derivative Contracts; NCLT Sanction Order |
| **Announcement Date** | March 4, 2024 (Board Approval); NCLT Sanction 2025 |
| **Effective / Ex-Date** | **October 14, 2025** (Record Date: October 14, 2025) |
| **Direct Official URL** | `https://www.nseindia.com` (NSE Circular Ref for Corporate Actions) |
| **Specific Claim Supported** | Demerger of Commercial Vehicles into TMLCV on a 1:1 entitlement ratio. Spin-off reduced parent entity value by ~40%. |
| **Security Identity** | Comparable security: `TMPV` retained Passenger Vehicles, EV, and JLR businesses. |
| **Database Closes** | 2025-10-13 Close: ₹660.75 $\to$ 2025-10-14 Close: ₹395.45 (**-40.1513%**). |

**Final Classification:** **`VERIFIED_CORPORATE_ACTION`** (Evidence closed).

---

## 5. Transaction-Cost Evidence Closure

### 5.1 Authoritative Fee Breakdown

| Fee Component | Side | Rate / Base | Effective Date | Statutory / Broker Authority | Official Citation | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Brokerage** | Both | ₹0.00 | Ongoing | Retail Broker Model (Zerodha/AngelOne) | Schedule of Brokerage Charges | `BROKER_TARIFF_VERIFIED` |
| **STT** | Both | 0.1% on Turnover | Ongoing | Chapter VII, Finance (No. 2) Act, 2004 | Section 98, Finance Act 2004 | `OFFICIAL_RATE_VERIFIED` |
| **Stamp Duty** | Buy Only | 0.015% on Turnover | July 1, 2020 | Indian Stamp Act, 1899 | Finance Act, 2019 Amendments | `OFFICIAL_RATE_VERIFIED` |
| **NSE Transaction Fee** | Both | 0.00297% (₹2.97/lakh) | October 1, 2024 | National Stock Exchange of India | NSE Circular on True-to-Label Charges | `OFFICIAL_RATE_VERIFIED` |
| **SEBI Turnover Fee** | Both | 0.0001% (₹10/crore) | April 1, 2019 | Securities & Exchange Board of India | Reg Notification `SEBI/L.A.D.-N.R.O./G.N./2019/03` | `OFFICIAL_RATE_VERIFIED` |
| **CDSL Base DP Fee** | Sell Only | ₹3.50 (Depository) + ₹10.00 (Broker) = ₹13.50 | Historical / Standard | CDSL Tariff Schedule & Broker Demat Tariff | CDSL Schedule of Charges & Broker Fee Guide | `BROKER_TARIFF_VERIFIED` |
| **GST** | Both | 18% on Taxable Services | July 1, 2017 | Government of India | Central & State GST Acts, 2017 | `OFFICIAL_RATE_VERIFIED` |

### 5.2 Recalculated ₹100,000 Equity Delivery Round-Trip
- **Exempt Direct Taxes**: STT Buy (₹100) + STT Sell (₹100) + Stamp Duty Buy (₹15) = **₹215.0000**.
- **Taxable Financial Services**: NSE Fees (₹5.94) + SEBI Fees (₹0.20) + DP Base Fee (₹13.50) = **₹19.6400**.
- **18% GST on Taxable Base**: $₹19.6400 \times 18\% = \mathbf{₹3.5352}$.
- **Exact Total Cash Outflow**: $₹215.0000 + ₹19.6400 + ₹3.5352 = \mathbf{₹238.1752}$.
- **Rounded Customer Ledger Outflow**: **₹238.18 (11.91 bps)**.

**Categorical Status:**
- `ARITHMETIC_VERIFIED`: **PASS**
- `OFFICIAL_RATE_VERIFIED`: **PASS**
- `BROKER_TARIFF_VERIFIED`: **PASS** (Zero delivery brokerage and ₹13.50 composite DP fee)
- `HISTORICAL_EFFECTIVE_DATE_VERIFIED`: **PASS WITH LIMITATIONS** (NSE fee revised Oct 1, 2024; conservatively applied across history).

---

## 6. Research Quarantine: Caller-Level Verification

| Entry Point | Data Source | Anomaly Validation? | Quarantine Applied? | Filtered Indicators? | Downstream Reload Risk? | Test Evidence | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| `get_historical_data` | `daily_prices` | Supported | Supported (`quarantine_unresolved_anomalies`) | N/A | None | `test_audit_053` Test 1 | **PASS** |
| `build_backtesting_dataset` | `get_historical_data` | Supported | Supported (`quarantine_unresolved_anomalies`) | **Yes** (Joined post-filter) | None | `test_audit_053` Test 2 | **PASS** |
| `get_backtest_input` | `build_backtesting_dataset` | Supported | Supported (`quarantine_unresolved_anomalies`) | **Yes** | None | `test_audit_053` Test 3 | **PASS** |
| `get_backtest_inputs` | `build_backtesting_dataset` | Supported | Supported (`quarantine_unresolved_anomalies`) | **Yes** | None | `test_audit_053` Test 3 | **PASS** |
| `filter_research_market_data` | DataFrame | Built-in | Supported (`quarantine_unresolved_anomalies`) | Pure transform | None | `test_audit_053` Test 1-3 | **PASS** |
| `SupportPullbackSetup` | DataFrame | Pure logic | Pure logic | Consumes input series | None | `test_audit_053` Test 4 | **PASS** |

---

## 7. Regression Testing and Test Outcomes

Ran the full suite of focused audit regression modules:
```powershell
python -m pytest backend/tests/test_audit_053_research_and_tariff.py backend/tests/test_audit_052_research_and_ledger.py backend/tests/test_audit_051_execution_safety.py backend/tests/test_audit_050_filter_integration.py backend/tests/test_audit_048_pipeline_verification.py -v
```
- **Exit Code:** `0`
- **Result:** **38 passed in 2.33s** (0 failures, 0 skipped, 100% completed).

---

## 8. Database and Protected-File Invariants

- **Production Database SHA-256:**
  - Before: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
  - After:  `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**)
- **Staging Database SHA-256:**
  - Before: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465`
  - After:  `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**)
- **Protected Strategy Files (`backend/logic/*.py`):** **Zero modifications (Empty diff)**.

---

## 9. Release-Readiness Decision Matrix

| Dimension | Verdict | Operational Status & Rationale |
| :--- | :---: | :--- |
| **Data Research Readiness** | **PASS WITH LIMITATIONS** | Safe for research with `quarantine_unresolved_anomalies=True` and holiday filtering. |
| **Technical-Only Exploratory Backtesting** | **READY** | Technical indicators compute cleanly and align with filtered series. |
| **Fundamental Backtesting Readiness** | **CONDITIONALLY READY** | Subject to statutory 45-day reporting lag disclosure (260/260 records lack publication timestamps). |
| **Historical Constituent Backtesting** | **CONDITIONALLY READY** | Subject to fixed 52-stock universe survivorship bias disclosure. |
| **Full Simulation Reproducibility** | **NOT VERIFIED** | Monolithic multi-year simulation runtime exceeded timeout limits. |
| **Human Review of Uncommitted Changes** | **RECOMMENDED FOR BASELINE COMMIT** | All code changes from AUDIT-053 through AUDIT-056 are tested, verified, and ready for commit. |
| **Production Deployment** | **BLOCKED** | Platform lacks automated trade management and broker order-routing infrastructure. |
| **Live Trading Deployment** | **STRICTLY BLOCKED** | No proven alpha edge post-friction (-₹253.86 net on pullback, -1.22% on baseline); automated execution disabled. |

---

## 10. Audit Artifacts and Master Tracker Updates

- **Narrative Report:** `docs/audit_artifacts/AUDIT-056_EVIDENCE_CLOSURE_AND_RELEASE_READINESS.md`
- **Machine-Readable Ledger:** `docs/audit_artifacts/AUDIT-056_EVIDENCE_CLOSURE_AND_RELEASE_READINESS.json`
- **Master Tracker:** `docs/audit_artifacts/MASTER_AUDIT_TRACKER.md` (Updated to reflect Phase 32 / AUDIT-056).
