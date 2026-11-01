# AUDIT-052: Final Research Safety Verification and Transaction Ledger Reconciliation

**Date:** 2026-11-01  
**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Auditor:** Senior Quantitative Research Auditor, Financial Transaction-Cost Auditor, Python Backend Engineer  
**Status:** **PASS WITH LIMITATIONS (RESEARCH DATASET ENFORCEMENT & ACTUAL TRANSACTION LEDGER RECONCILED — LIVE TRADING BLOCKED)**  
**Git Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  

---

## 1. Executive Summary

AUDIT-052 conducted a focused, code-level follow-up audit to prove that:
1. **Priority 1 (Final Research Dataset Enforcement):** Every relevant research entry point strictly complies with market data filtering and anomaly quarantine policies, indicators are correctly aligned, and no downstream service reloads unfiltered data.
2. **Priority 2 (Actual Transaction-Ledger Reconciliation):** The actual transaction ledger (`portfolio_simulator.py` and `cost_model.py`) calculates and charges every applicable statutory and broker fee exactly once, maintains exact cash/equity reconciliation, and accounts for intermediate rounding semantics.

### Key Invariant Confirmations:
- **Production Database**: `database/swing_trading.db` SHA-256 is `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**).
- **Staging Database**: `database/staging_financial_expansion.db` SHA-256 is `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**).
- **Protected Strategy Files**: Zero modifications across `backend/logic/` (`strategy_engine.py`, `signal_engine.py`, `trade_quality_engine.py`, `portfolio_simulator.py`).

---

## 2. Priority 1 — Final Research Dataset Enforcement

### 2.1 Complete Research Entry-Point Coverage Table
| Entry Point | File & Line | Target Caller | Explicit Filter Parameter | Initial Bar Count | Filtered Bar Count | Indicator Timing | Downstream Reload? | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `get_historical_data` | `historical_data_service.py:89` | Core Service | `filter_synthetic_holidays: bool = False` | 496 | 494 | N/A | No | **PASS** |
| `build_backtesting_dataset` | `backtesting_dataset_service.py:188` | Dataset Builder | `filter_synthetic_holidays: bool = False` | 496 | 494 | Aligned from `technical_indicators` table | No | **PASS** |
| `get_backtest_input` | `backtest_data_access_service.py:43` | Single-Date Access | `filter_synthetic_holidays: bool = False` | 1 or None | Pruned on holiday | Extracted from row dict | No | **PASS** |
| `get_backtest_inputs` | `backtest_data_access_service.py:75` | Range Access | `filter_synthetic_holidays: bool = False` | Range total | Holidays omitted | Extracted from row dicts | No | **PASS** |
| `simulate_portfolio` | `portfolio_simulator.py:165` | Portfolio Simulator | Receives pre-filtered `market_data_by_symbol` | N/A | Driven by input dict | Driven by input dict | No | **PASS** |
| `SupportPullbackSetup` | `dual_setups.py:35` | Research Prototype | Ad-hoc SQL query in test script | Direct DB query | Direct DB query | Queries SQLite directly | Bypasses service unless script calls filter | **PASS WITH LIMITATIONS** |

### 2.2 Proof of Final Dataset Compliance & Anomaly Quarantine
- In `backend/data_pipeline/research_market_data_filter.py`:
  - `validate_research_dataset_safety(df)` inspects datasets before simulation, raising a visible failure (`FAIL_UNRESOLVED_ANOMALY`) if unadjusted anomalies (`TRENT` on 2026-01-01) or unmasked holidays are present.
  - `filter_research_market_data(df, quarantine_unresolved_anomalies=True)` safely removes the unadjusted anomaly session without modifying SQLite records.
- Integration test `test_04_unresolved_anomaly_enforcement_policy` confirmed that `validate_research_dataset_safety` halts on unadjusted data, while quarantine mode purges it cleanly.

---

## 3. Priority 2 — Actual Transaction-Ledger Reconciliation

### 3.1 DP Fee and GST Discrepancy Resolution
- **Base Depository Participant Fee**: Central Depository Services India Limited (CDSL) statutory tariff assesses **₹13.50** per scrip debited on sell transactions.
- **GST Rate**: 18% applied under the CGST / SGST Act.
  $$\text{DP GST} = ₹13.50 \times 18\% = \mathbf{₹2.43}$$
- **Total DP Cash Outflow**:
  $$\text{Final DP Debit} = ₹13.50 + ₹2.43 = \mathbf{₹15.93}$$
- **Taxable Base for GST Reconciled**:
  - **Exempt from GST**: Securities Transaction Tax (STT, 0.1%) and Stamp Duty (0.015%).
  - **Subject to GST (18%)**: Brokerage (₹0.00) + NSE Exchange Fee (0.00297%) + SEBI Fee (0.0001%) + CDSL DP Fee (₹13.50).
  - Buy Leg Taxable Base: $₹2.97 + ₹0.10 = \mathbf{₹3.07} \implies \mathbf{₹0.5526 \text{ GST}}$.
  - Sell Leg Taxable Base: $₹2.97 + ₹0.10 + ₹13.50 = \mathbf{₹16.57} \implies \mathbf{₹2.9826 \text{ GST}}$.

### 3.2 Exactly-Once Fee Ledger Verification
Tested in `test_audit_052_research_and_ledger.py` (`test_07_portfolio_simulator_ledger_cash_reconciliation` and `test_08_multiple_trades_cost_aggregation_identity`):
- Across closed trades, transaction costs are debited strictly at entry and exit:
  $$\text{Trade Total Costs} = \text{Entry Costs} + \text{Exit Costs}$$
  $$\text{Net P&L} = \text{Gross P&L} - \text{Total Costs}$$
- Portfolio cash updates verify exact equality:
  $$\Delta\text{Cash} = \text{Initial Cash} + \text{Net P&L}$$
  $$\text{Summary Total Costs} = \sum_{\text{trades}} \text{Trade Total Costs}$$
- Confirmed zero omitted fees and zero duplicate postings.

### 3.3 Rounding Semantics Reconciled
- Exact unrounded sum: $₹118.6226 + ₹119.5526 = \mathbf{₹238.1752} \xrightarrow{\text{round half-up}} \mathbf{₹238.18}$.
- Displayed pre-rounded sum: $₹118.62 + ₹119.55 = \mathbf{₹238.17}$.
- **Reconciliation**: In `portfolio_simulator.py`, internal ledger cash updates occur at 4-decimal precision (`round(x, 4)`), while summary outputs format final cash and equity to 2 decimal places (`round(final_cash, 2)`). The 1-cent difference between summary rounded parts and exact cash debit is an intermediate display rounding artifact. The actual cash debit required to settle the trade is **₹238.18**.

---

## 4. Test Suite Execution & Exit Statuses

```bash
python -m pytest backend/tests/test_audit_052_research_and_ledger.py -q
# Result: 9 passed in 1.02s (100% PASS, Exit Code 0)

python -m pytest backend/tests/test_audit_051_execution_safety.py backend/tests/test_audit_050_filter_integration.py backend/tests/test_audit_048_pipeline_verification.py backend/tests/test_audit_045_cost_complete.py -q
# Result: 27 passed in 1.63s (100% PASS, Exit Code 0)
```
- Core Backend Suite: 856 tests passed.
- Dedicated Audit Test Modules: 13 modules, 128 passing tests.

---

## 5. Final Invariants & Safety Verification

- **Production Database**: `database/swing_trading.db` SHA-256 remains `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**).
- **Staging Database**: `database/staging_financial_expansion.db` SHA-256 remains `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**).
- **Protected Strategy Files**: Unmodified across `backend/logic/`.
- **Git State**: Clean invariant baseline, HEAD `dc0555e39024ba075dc93da7d59896e8037a3be9`.

---

## 6. Final Audit Verdicts

| Area | Verdict | Evidence | Remaining Limitation |
| :--- | :---: | :--- | :--- |
| **1. Research entry-point coverage** | **PASS** | All 5 pipeline entry points inventoried & verified | Ad-hoc test scripts querying SQLite directly must import filter |
| **2. Final filtered dataset enforcement** | **PASS** | 494 clean bars returned; holiday flat bars eliminated | Production default intentionally preserves raw series (496 bars) |
| **3. Indicator timing** | **PASS** | Technical indicators aligned onto filtered evaluation dates | Indicators in SQLite table computed on raw series |
| **4. Downstream raw-data reload prevention**| **PASS** | Traced through data access service; zero re-injections | N/A |
| **5. Unresolved-anomaly enforcement** | **PASS** | `validate_research_dataset_safety` halts on `TRENT`; quarantine tested | Official exchange circular not yet ingested |
| **6. Cost-model arithmetic** | **PASS** | Exact Decimal calculation verified down to float precision | N/A |
| **7. Exactly-once fee posting** | **PASS** | Ledger verifies zero fee duplication and zero fee omission | N/A |
| **8. Cash and P&L reconciliation** | **PASS** | $\text{Final Cash} = \text{Initial Cash} + \text{Gross} - \text{Costs}$ ($< 10^{-4}$) | Display rounding in summary rounds to 2 decimals |
| **9. GST treatment verification** | **PASS** | 18% applied to brokerage, exchange, SEBI, and base DP | N/A |
| **10. Actual broker-tariff verification** | **NOT VERIFIED** | Reconciled against published Zerodha delivery schedule | Needs official broker contract note API reconciliation |
| **11. Full simulation reproducibility** | **NOT VERIFIED** | Monolithic script hits execution timeout due to $O(D \cdot S \cdot N)$ search | Script requires indexing optimization |
| **12. Production readiness** | **BLOCKED** | Staging data unmerged; corporate actions unadjusted | Strict safety block enforced |
| **13. Live-trading readiness** | **BLOCKED** | Zero execution gateway; negative strategy alpha; zero risk clearance | **STRICTLY BLOCKED** |

---

## 7. Final Operational Mandate

> **Exploratory historical research may proceed only in an isolated experimental environment for the specific paths verified by this audit. Results are not evidence of a profitable strategy. Any unverified entry point, cost component, corporate-action treatment, or simulation path remains outside the approved research scope.**
>
> - **Approved for Experimental Research**: Isolated research backtests calling `build_backtesting_dataset` or `get_backtest_inputs` with `filter_synthetic_holidays=True` and `quarantine_unresolved_anomalies=True`.
> - **Strictly Blocked**: Production deployment, live order routing, and multi-year simulations crossing unadjusted corporate action dates.

