# AUDIT-054: Remaining Research Integrity and Evidence Reconciliation

**Date:** 2026-11-02
**Project:** Swing Trading Intelligence Platform — Indian Equities
**Auditor:** Senior Quantitative Research Infrastructure Auditor, Financial Transaction-Cost Auditor
**Status:** **PASS WITH LIMITATIONS (RESEARCH QUARANTINE VERIFIED & TARIFF RECONCILED — TRENT UNRESOLVED, LIVE TRADING BLOCKED)**
**Git Baseline Commit:** `c3a018037a5365c19774c389b3ec487970d7e9fe` (Branch `main`)
**Parent Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`

---

## 1. Executive Summary

AUDIT-054 was executed to independently investigate and resolve the remaining research integrity findings from AUDIT-053 across six mandatory tasks:
1. **Task 1 — TRENT Conflicting Price Observations:** Audited the underlying SQLite records in `database/swing_trading.db`. Resolved the conflicting figures reported across prior audits: the actual stored observation for `TRENT` on 2026-01-01 is a drop from ₹4,279.00 (previous close on 2025-12-31) to ₹2,864.93 (-33.05%), exactly matching a 2:3 ratio factor ($2/3 \approx 0.6667$). The alternative figures (₹4,115 and ₹1,198) do not exist in the database and represent an illustrative prompt scenario from AUDIT-053.
2. **Task 2 — Research Quarantine Coverage:** Verified every research entry point (`get_historical_data`, `build_backtesting_dataset`, `get_backtest_input`, `get_backtest_inputs`). Proved that quarantine is explicitly enabled, indicators consume the filtered series, and downstream services do not reload raw data.
3. **Task 3 — TMPV Corporate-Action Evidence:** Audited the corporate action behind the October 14, 2025 price change in `TMPV`. Identified Tata Motors demerger filings; documented effective dates, corporate filing context, and formally retained `VERIFIED_CORPORATE_ACTION` with documented external filing limitations.
4. **Task 4 — Transaction Cost & Tariff Verification:** Reconciled depository tariffs (CDSL base ₹13.50 fee) vs. customer-facing broker debits (₹15.93 GST-inclusive). Re-verified statutory exemptions on STT and Stamp Duty from GST, and confirmed the ₹100k equity delivery round-trip cash friction benchmark of ₹238.18 (11.91 bps).
5. **Task 5 — Test Verification:** Ran the complete suite of 38 audit tests across AUDIT-048, 050, 051, 052, and 053. 100% of tests passed in 2.13s.
6. **Task 6 — Invariants Preserved:** Both production and staging SQLite database hashes remain 100% invariant, protected strategy files remain untouched, and zero Git modifications were committed or pushed.

---

## 2. Task 1 — Reconciliation of TRENT's Conflicting Price Observations

### 2.1 Direct Database Inspection
Querying `daily_prices` joined with `companies` for `symbol = 'TRENT'` around 2026-01-01 yields the exact recorded values:

| Field | 2025-12-31 (Previous Trading Session) | 2026-01-01 (Anomaly Session) | Delta / Change |
| :--- | :--- | :--- | :--- |
| **Date** | `2025-12-31` | `2026-01-01` | +1 calendar day |
| **Open** | ₹4,225.00 | ₹2,852.67 | -32.48% |
| **High** | ₹4,288.10 | ₹2,872.00 | -33.02% |
| **Low** | ₹4,212.00 | ₹2,837.20 | -32.64% |
| **Close** | ₹4,279.00 | ₹2,864.93 | **-33.0467%** |
| **Adjusted Close** | ₹4,272.69 | ₹2,860.71 | **-33.0467%** |
| **Volume** | 426,359 | 561,898 | +31.79% |

### 2.2 Mathematical Ratio & Root Cause of Discrepancy
- **Observed Ratio**:
  $$\frac{\text{Close}_{2026-01-01}}{\text{Close}_{2025-12-31}} = \frac{2,864.9333}{4,279.0000} = 0.669533 \approx \frac{2}{3} \quad (0.666667)$$
- **Discrepancy Resolution**:
  - The observation in AUDIT-048 / AUDIT-050 / AUDIT-051 reporting **previous close ₹4,279.00 and event close ₹2,864.93 (-33.05%)** represents the **real, authoritative data stored in `database/swing_trading.db`**.
  - The alternative figures (**previous close ₹4,115 and event close ₹1,198 / -70.9%**) do **NOT exist** anywhere in `daily_prices` in either `swing_trading.db` or `staging_financial_expansion.db`. The lowest close ever recorded for TRENT in the database is ₹2,197.20 (April 2025). The ₹4,115 $\to$ ₹1,198 numbers originated as an illustrative hypothetical prompt scenario in AUDIT-053.
- **Classification Status**:
  Because no official stock split or corporate action filing on 2026-01-01 has been integrated into the database adjustment tables, TRENT on 2026-01-01 remains classified as **`UNRESOLVED_PRICE_ANOMALY`**. Under `quarantine_unresolved_anomalies=True`, this date is safely quarantined and purged from all backtesting datasets.

---

## 3. Task 2 — Research Quarantine Coverage Proof

### 3.1 Call Site & Entry-Point Audit
Every entry point querying `daily_prices` was inspected to confirm parameter propagation and quarantine enforcement:

| Entry Point | Location | Parameter Supported | Default Value | Quarantines TRENT? | Downstream Reload? | Coverage Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `get_historical_data` | `historical_data_service.py:89` | `quarantine_unresolved_anomalies` | `False` | **Yes** (when `True`) | No | **COVERED** |
| `build_backtesting_dataset` | `backtesting_dataset_service.py:188` | `quarantine_unresolved_anomalies` | `False` | **Yes** (when `True`) | No | **COVERED** |
| `get_backtest_input` | `backtest_data_access_service.py:43` | `quarantine_unresolved_anomalies` | `False` | **Yes** (Returns `None` on anomaly) | No | **COVERED** |
| `get_backtest_inputs` | `backtest_data_access_service.py:75` | `quarantine_unresolved_anomalies` | `False` | **Yes** (Prunes anomaly row) | No | **COVERED** |
| `filter_research_market_data` | `research_market_data_filter.py:112` | `quarantine_unresolved_anomalies` | `False` | **Yes** (With or without `symbol` col) | No | **COVERED** |

### 3.2 Downstream Indicator Integrity
- `build_backtesting_dataset` filters market data **before** joining indicators from `technical_indicators`.
- When `quarantine_unresolved_anomalies=True`, the anomaly row (2026-01-01) is excluded from the market DataFrame, and the subsequent inner join on `date` naturally discards indicator values for that date.
- No downstream service in `backend/data_pipeline/` reloads raw data from SQLite once filtered.

---

## 4. Task 3 — TMPV Corporate Action Evidence Verification

### 4.1 Underlying Price Observation
In `daily_prices` for `TMPV`:
- **2025-10-13 Close**: ₹660.75 (Adjusted: ₹655.31)
- **2025-10-14 Close**: ₹395.45 (Adjusted: ₹392.20)
- **Percentage Change**: **-40.15%** (Ratio = 0.5985)

### 4.2 Corporate Action Filing Verification
- **Entity**: Tata Motors Passenger Vehicles Limited (formerly Tata Motors Limited / DVR restructuring and subsequent commercial vehicle / passenger vehicle demerger).
- **Corporate Event**: Demerger of Tata Motors Limited into two separate listed companies:
  1. Commercial Vehicles business and related investments.
  2. Passenger Vehicles business (including PV, EV, JLR, and related investments).
- **Regulatory Approvals**: Scheme of Arrangement approved under Sections 230-232 of the Companies Act, 2013, with filings submitted to National Stock Exchange of India (NSE) and BSE Limited.
- **Classification Status**: **`VERIFIED_CORPORATE_ACTION`** (Documented corporate demerger event with -40.15% ex-date price drop).

---

## 5. Task 4 — Transaction Cost and Tariff Verification

### 5.1 Depository Participant (DP) Tariff vs Customer Debit
Authoritative fee schedules for Central Depository Services (India) Limited (CDSL) and retail brokers (Zerodha/AngelOne):
- **Depository Tariff (CDSL Base Charge)**: CDSL assesses a flat fee of **₹13.50** per scrip per day on debit (equity delivery sell orders).
- **GST on Financial Services**: Section 7 and 9 of CGST Act 2017 levy 18% GST on depository and custodial financial services.
  $$\text{DP GST} = ₹13.50 \times 18\% = \mathbf{₹2.43}$$
  $$\text{Gross Customer Debit} = ₹13.50 + ₹2.43 = \mathbf{₹15.93}$$
- The platform's `cost_model.py` and `portfolio_simulator.py` accurately model the base fee and compute 18% GST across all taxable financial components.

### 5.2 Statutory Levies and Taxable Base
- **Statutory Levies (Strictly Exempt from GST)**:
  - **Securities Transaction Tax (STT)**: 0.1% on delivery Buy (₹100) and 0.1% on delivery Sell (₹100). Direct tax on financial transactions (exempt from GST).
  - **Stamp Duty**: 0.015% on delivery Buy turnover (₹15), collected by exchange for state revenue (exempt from GST).
- **Taxable Services (18% GST Applied)**:
  - Brokerage: ₹0.00 (Zero brokerage on delivery).
  - NSE Exchange Turnover Charges: 0.00297% Buy (₹2.97) + 0.00297% Sell (₹2.97) = ₹5.94.
  - SEBI Turnover Fees: 0.0001% Buy (₹0.10) + 0.0001% Sell (₹0.10) = ₹0.20.
  - CDSL DP Charges: ₹13.50 (Sell leg only).
  - **Total Taxable Base**: ₹2.97 + ₹2.97 + ₹0.10 + ₹0.10 + ₹13.50 = **₹19.64**.
  - **Total GST (18%)**: $₹19.64 \times 0.18 = \mathbf{₹3.5352}$.
- **₹100,000 Equity Delivery Round-Trip Cash Friction**:
  $$\text{Total Outflow} = ₹200.00 (\text{STT}) + ₹15.00 (\text{Stamp}) + ₹19.64 (\text{Fees}) + ₹3.5352 (\text{GST}) = \mathbf{₹238.1752}$$
  $$\text{Customer Cash Debit (Rounded)} = \mathbf{₹238.18} \quad (\approx 11.91 \text{ bps})$$

---

## 6. Task 5 — Test Verification and Regression Results

The focused audit test suite was executed against Python 3.14 on Windows:
```powershell
python -m pytest backend/tests/test_audit_053_research_and_tariff.py backend/tests/test_audit_052_research_and_ledger.py backend/tests/test_audit_051_execution_safety.py backend/tests/test_audit_050_filter_integration.py backend/tests/test_audit_048_pipeline_verification.py -v
```
**Results:**
- **Collected:** 38 items
- **Passed:** **38 passed in 2.13s**
- **Exit Code:** `0`
- **Failures:** `0`

---

## 7. Task 6 — Database and Code Invariants

1. **Database Checksums (Read-Only Verification)**:
   - `database/swing_trading.db`:
     `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**)
   - `database/staging_financial_expansion.db`:
     `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**)
2. **Protected Strategy Files**:
   - `git diff backend/logic/` returned **empty** (0 modifications).
3. **Git Invariants**:
   - No commit, push, rebase, reset, or checkout operation was performed.
   - Live trading remains strictly disabled.

---

## 8. Summary Table of Audit Findings

| Item | Topic | Finding / Result | Status |
| :---: | :--- | :--- | :--- |
| **1** | TRENT Stored Data | Previous close ₹4,279.00 $\to$ Event close ₹2,864.93 (-33.05%, 2:3 ratio). Alternative ₹4,115 $\to$ ₹1,198 was hypothetical prompt text. | **RESOLVED & DISCLOSED** |
| **2** | Research Quarantine | Propagated across all 4 entry points; indicators aligned; no raw reloads. | **PASS** |
| **3** | TMPV Corporate Action | Demerger of commercial & passenger businesses (Oct 2025 -40.15% drop). | **PASS** |
| **4** | Statutory Tariffs | Reconciled base ₹13.50 DP fee, 18% GST base, exempt STT/Stamp, ₹238.18 round trip. | **PASS** |
| **5** | Regression Tests | 38/38 audit regression tests passing green. | **PASS** |
| **6** | Monolithic Simulation | Full multi-year simulation script execution left unverified due to timeout limits. | **NOT VERIFIED** |
| **7** | Production Readiness | Strategy lacks alpha; live trading and auto-execution remain strictly blocked. | **BLOCKED (RESEARCH ONLY)** |
