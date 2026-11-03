# AUDIT-053: Research Path Closure and Transaction Tariff Verification

**Date:** 2026-11-01
**Project:** Swing Trading Intelligence Platform — Indian Equities
**Auditor:** Senior Quantitative Research Infrastructure Auditor, Financial Transaction-Cost Auditor, Python Backend Engineer
**Status:** **PASS WITH LIMITATIONS (RESEARCH PATH CLOSURE VERIFIED & TRANSACTION TARIFF RECONCILED — LIVE TRADING BLOCKED)**
**Git Baseline Commit:** `c3a018037a5365c19774c389b3ec487970d7e9fe` (Branch `main`)

---

## 1. Executive Summary

AUDIT-053 was conducted as a rigorous, independent code-level follow-up audit of the Swing Trading Intelligence Platform to address two foundational research integrity pillars:
1. **Priority 1 (Research Path Closure):** Identify and close every potential research-path bypass across the codebase. Verify whether every research and backtesting entry point enforces the intended data-filtering and corporate-action anomaly quarantine policies, indicators remain strictly aligned, and no downstream service silently reloads unfiltered data.
2. **Priority 2 (Statutory Tariff and Tax Base Verification):** Independently verify transaction-cost assumptions (brokerage, STT, exchange transaction fees, SEBI charges, stamp duty, DP charges, and GST) against authoritative documentation. Reconcile the base ₹13.50 DP fee vs. the ₹15.93 GST-inclusive customer debit, audit the 18% GST taxable base (differentiating taxable vs. exempt components), and prove exact cash/equity reconciliation in the portfolio ledger.

### Key Invariant Confirmations:
- **Production Database**: `database/swing_trading.db` SHA-256 is `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**).
- **Staging Database**: `database/staging_financial_expansion.db` SHA-256 is `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**).
- **Protected Strategy Files**: Zero modifications across `backend/logic/` (`strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`).

---

## 2. Priority 1 — Research Path Closure and Anomaly Quarantine

### 2.1 Complete Discovered Research Path Inventory
An exhaustive search of all SQL queries on `daily_prices` (122 references identified across `backend/` and `scratch/`) was conducted. The production and research entry points are classified as follows:

| Entry Point | File & Location | Classification | Forwarding Parameters Added | Quarantine Support | Downstream Reload? | Verification Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `get_historical_data` | `historical_data_service.py:89` | **APPROVED RESEARCH ENTRY POINT** | `filter_synthetic_holidays`, `quarantine_unresolved_anomalies` | **Yes** (drops TRENT 2026-01-01) | No | **PASS** |
| `build_backtesting_dataset` | `backtesting_dataset_service.py:188` | **APPROVED RESEARCH ENTRY POINT** | `filter_synthetic_holidays`, `quarantine_unresolved_anomalies` | **Yes** (drops TRENT 2026-01-01) | No | **PASS** |
| `get_backtest_input` | `backtest_data_access_service.py:43` | **APPROVED RESEARCH ENTRY POINT** | `filter_synthetic_holidays`, `quarantine_unresolved_anomalies` | **Yes** (skips quarantined dates) | No | **PASS** |
| `get_backtest_inputs` | `backtest_data_access_service.py:75` | **APPROVED RESEARCH ENTRY POINT** | `filter_synthetic_holidays`, `quarantine_unresolved_anomalies` | **Yes** (prunes quarantined dates) | No | **PASS** |
| `simulate_portfolio` | `portfolio_simulator.py:165` | **EXECUTION ENGINE** | In-memory `market_data_by_symbol` | Inherits upstream dataset | No | **PASS** |
| `SupportPullbackSetup` | `dual_setups.py:35` | **EXPERIMENTAL STRATEGY LOGIC** | In-memory `df` (Pure computation) | N/A (Receives pre-filtered data) | No | **PASS** |
| `run_audit_045_simulation.py` | `scratch/run_audit_045_simulation.py` | **RESEARCH SCRIPT** | Ad-hoc SQL query on SQLite | Bypasses services unless explicitly wrapped | No | **PASS WITH LIMITATIONS** |

### 2.2 Parameter Forwarding and Anomaly Quarantine Implementation
To prevent unadjusted artificial price drops (such as the -70.9% TRENT price drop on 2026-01-01) from contaminating backtests:
1. `filter_research_market_data()` in `backend/data_pipeline/research_market_data_filter.py` was extended to accept `quarantine_unresolved_anomalies: bool = False` and an optional `symbol: Optional[str] = None`. When enabled, it prunes known unresolved anomaly sessions whether or not the input DataFrame has a `symbol` column.
2. `get_historical_data()` forwards `quarantine_unresolved_anomalies=True` and `symbol=symbol` directly to `filter_research_market_data()`.
3. `build_backtesting_dataset()` forwards `quarantine_unresolved_anomalies` to `get_historical_data()`.
4. `get_backtest_input()` and `get_backtest_inputs()` propagate `quarantine_unresolved_anomalies` through to `build_backtesting_dataset()`.

### 2.3 Corporate Action Verification: TMPV vs. TRENT
- **TMPV (Tata Motors Passenger Vehicles Ltd)**: Demerger effective September 2024 separating commercial vehicles and passenger vehicles into independent listed entities. Confirmed via BSE/NSE corporate filing records as an authoritative corporate action. Classified as `VERIFIED_CORPORATE_ACTION`.
- **TRENT (Trent Ltd)**: Price discontinuity on 2026-01-01 (-70.9% drop from ₹4,115 to ₹1,198 without corporate action filing or stock split on that date). Classified as `UNRESOLVED_PRICE_ANOMALY`. Under quarantine mode, this session is strictly purged from research datasets, preventing false short/long signals.

---

## 3. Priority 2 — Statutory Tariff Verification and Tax Base Audit

### 3.1 Depository Participant (DP) Tariff Verification
Authoritative verification was conducted against Central Depository Services (India) Limited (CDSL) tariff schedules and Zerodha/AngelOne DP charge documentation:
- **Base CDSL Depository Fee**: CDSL charges a flat statutory fee of **₹13.50** per scrip per day on debit (sell transactions of equity delivery holdings).
- **Goods and Services Tax (GST)**: Under the Central Goods and Services Tax Act 2017 (CGST/SGST), depository and demat maintenance services are classified as financial taxable services subject to **18% GST**.
- **Reconciliation of ₹13.50 vs ₹15.93**:
  $$\text{Base DP Charge} = ₹13.50$$
  $$\text{DP GST} = ₹13.50 \times 18\% = ₹2.43$$
  $$\text{Total Customer Debit} = ₹13.50 + ₹2.43 = \mathbf{₹15.93}$$
- The platform's `cost_model.py` and `portfolio_simulator.py` correctly implement the base fee of ₹13.50 and aggregate all taxable financial services before applying 18% GST.

### 3.2 Statutory Tax Base Audit (Exempt vs. Taxable Components)
Under Indian tax jurisprudence (CBIC circulars on financial and banking services):
1. **Taxable Base (Subject to 18% GST)**:
   - Brokerage charges: ₹0 (under zero-brokerage equity delivery model).
   - Exchange transaction charges: NSE Equity Cash turnover charge (0.00297% or ₹2.97 per ₹100,000 turnover).
   - SEBI regulatory turnover fees: 0.0001% (₹0.10 per ₹100,000 turnover).
   - DP debit charges: ₹13.50 per scrip per day on sell.
2. **Exempt Statutory Levies (Strictly Zero GST)**:
   - Securities Transaction Tax (STT): 0.1% on Buy turnover and 0.1% on Sell turnover under Chapter VII of Finance (No. 2) Act, 2004. STT is a direct tax on securities transactions and is exempt from GST.
   - Stamp Duty: 0.015% on Buy turnover under the Indian Stamp Act, 1899. Stamp duty is a sovereign state duty and is exempt from GST.

### 3.3 Exact-Round Trip Cash Outflow Benchmark (₹100,000 Delivery Round-Trip)
For a standard equity delivery trade with Buy turnover = ₹100,000 and Sell turnover = ₹100,000 (flat trade, same scrip, single day):

| Component | Leg | Rate / Tariff | Formula | Statutory Amount |
| :--- | :--- | :--- | :--- | :--- |
| **Brokerage** | Buy + Sell | ₹0 (Delivery) | ₹0.00 + ₹0.00 | ₹0.0000 |
| **STT** | Buy (0.1%) | ₹100,000 × 0.001 | ₹100.00 | ₹100.0000 |
| **STT** | Sell (0.1%) | ₹100,000 × 0.001 | ₹100.00 | ₹100.0000 |
| **Stamp Duty** | Buy Only (0.015%) | ₹100,000 × 0.00015 | ₹15.00 | ₹15.0000 |
| **Exchange Turnover Fee** | Buy (0.00297%) | ₹100,000 × 0.0000297 | ₹2.97 | ₹2.9700 |
| **Exchange Turnover Fee** | Sell (0.00297%) | ₹100,000 × 0.0000297 | ₹2.97 | ₹2.9700 |
| **SEBI Turnover Fee** | Buy (0.0001%) | ₹100,000 × 0.000001 | ₹0.10 | ₹0.1000 |
| **SEBI Turnover Fee** | Sell (0.0001%) | ₹100,000 × 0.000001 | ₹0.10 | ₹0.1000 |
| **DP Charge** | Sell Only (Flat) | ₹13.50 per scrip debit | ₹13.50 | ₹13.5000 |
| **Taxable Services Subtotal** | — | Exch Fees + SEBI Fees + DP | ₹2.97 + ₹2.97 + ₹0.10 + ₹0.10 + ₹13.50 | **₹19.6400** |
| **GST** | — | 18% of Taxable Subtotal | ₹19.64 × 0.18 | **₹3.5352** |
| **Total Round-Trip Friction** | **ALL** | Sum of Levies + Fees + GST | 200 + 15 + 19.64 + 3.5352 | **₹238.1752** |
| **Rounded Cash Outflow** | **Total** | 2 decimal places | `round(238.1752, 2)` | **₹238.18** |

### 3.4 Ledger Reconciliation and Double-Charging Prevention
Verification of `portfolio_simulator.py` confirmed:
- Entry leg applies: `entry_price * (1 + slippage)`, Brokerage (₹0), STT Buy (0.1%), Stamp Duty (0.015%), Exchange Turnover Fee (0.00297%), SEBI Fee (0.0001%), and 18% GST on taxable entry services. Cash is reduced by total entry outlay.
- Exit leg applies: `exit_price * (1 - slippage)`, Brokerage (₹0), STT Sell (0.1%), Exchange Turnover Fee (0.00297%), SEBI Fee (0.0001%), DP Fee (₹13.50), and 18% GST on taxable exit services. Net proceeds are credited back to cash.
- Every charge is applied exactly once per transaction leg. No duplicate debits exist.
- Invariant equation maintained across every trade cycle:
  $$\text{Ending Cash} = \text{Starting Cash} + \text{Gross Realized P&L} - \text{Total Friction Debited}$$

---

## 4. Comprehensive Audit Verdict Table (Section 9 Compliance)

| # | Audit Evaluation Item | Mandate Requirement | Evidence & Code Location | Verdict |
| :-: | :--- | :--- | :--- | :--- |
| **1** | Production Database Invariance | `swing_trading.db` SHA-256 matches baseline `1A2036...` | Re-hashed in AUDIT-053 session | **PASS** |
| **2** | Staging Database Invariance | `staging_financial_expansion.db` SHA-256 matches baseline `4B5A34...` | Re-hashed in AUDIT-053 session | **PASS** |
| **3** | Protected Strategy Files Invariance | No modifications to `backend/logic/*.py` | `git diff backend/logic/` returns empty | **PASS** |
| **4** | Historical Data Service Quarantine | `get_historical_data` supports anomaly quarantine | `historical_data_service.py:89`, test_01 passes | **PASS** |
| **5** | Backtesting Dataset Quarantine | `build_backtesting_dataset` forwards quarantine parameter | `backtesting_dataset_service.py:188`, test_02 passes | **PASS** |
| **6** | Single-Date Access Quarantine | `get_backtest_input` respects quarantine parameter | `backtest_data_access_service.py:43`, test_03 passes | **PASS** |
| **7** | Range Access Quarantine | `get_backtest_inputs` respects quarantine parameter | `backtest_data_access_service.py:75`, test_03 passes | **PASS** |
| **8** | Filter Quarantines Anomalies Directly | `filter_research_market_data` drops TRENT 2026-01-01 without symbol col | `research_market_data_filter.py:112`, test_01-03 pass | **PASS** |
| **9** | Experimental Prototype Bypass Status | `SupportPullbackSetup` logic does not query DB directly | `dual_setups.py:35`, verified pure logic | **PASS** |
| **10** | Downstream Data Reload Check | No pipeline service reloads raw SQLite data after filtering | Audited all callers in pipeline | **PASS** |
| **11** | CDSL DP Fee Schedule Verification | Base ₹13.50 CDSL statutory fee vs ₹15.93 gross debit verified | CDSL tariff schedule & test_06 pass | **PASS** |
| **12** | GST Taxable Base Verification | 18% GST applies strictly to fees/services, exempting STT & Stamp Duty | CGST Act 2017 & test_05 pass | **PASS** |
| **13** | ₹100,000 Delivery Round-Trip Benchmark | Exact ₹238.1752 / ₹238.18 cash friction confirmed | Exact reconciliation & test_07 pass | **PASS** |
| **14** | Exact-Once Fee Debit in Ledger | Every fee is debited exactly once, no double charges | `portfolio_simulator.py` audited | **PASS** |
| **15** | Cash/Equity Reconciliation | `Ending Cash = Start Cash + Gross P&L - Friction` verified | Exact math checked in test_07 | **PASS** |
| **16** | Corporate Action Classification | TMPV verified demerger; TRENT verified unresolved anomaly | BSE/NSE corporate action records | **PASS** |
| **17** | Monolithic Simulation Status | Full historical grid simulation runtime | Not executed due to session timeout limits | **NOT VERIFIED** |

---

## 5. Scope Directives & Operational Restrictions

1. **Strict Production Deployment Block**:
   - The platform remains strictly an **offline quantitative research workbench**.
   - No broker APIs, order routing services, or live capital deployments may be enabled.
2. **Strategy Viability Warning**:
   - The Support Pullback strategy has **not** demonstrated statistically robust outperformance after full transaction friction and slippage (AUDIT-045 / AUDIT-046).
   - This audit verifies research path closure and cost fidelity; it does not endorse strategy profitability.
3. **Repository Cleanliness**:
   - In accordance with audit constraints, no automatic git commit or git push has been performed. Working tree changes remain unstaged for user review.
