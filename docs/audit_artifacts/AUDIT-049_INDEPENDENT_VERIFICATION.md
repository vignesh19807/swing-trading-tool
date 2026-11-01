# AUDIT-049 — Independent Research Pipeline and Data Integrity Verification Report

**Date:** 2026-11-01  
**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Auditor:** Quantitative Research Infrastructure Auditor, Backtesting Validation Specialist  
**Status:** **PASS (Independent Verification Ratified — 14-Category Research Readiness Certified)**  
**Baseline Git Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  

---

## 1. Executive Summary

This audit independently validates the data integrity, research filter integration, corporate action anomalies, and transaction cost modeling implemented across AUDIT-040 through AUDIT-048. 

### Key Findings
1. **Production & Staging Database Invariance**:
   - Production Database (`database/swing_trading.db`):
     - SHA-256: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**)
     - File size: `9,068,544 bytes`
   - Staging Database (`database/staging_financial_expansion.db`):
     - SHA-256: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (**100% Invariant**)
     - File size: `5,410,816 bytes`
2. **Complete Market-Data Universe Classification (100% Verified)**:
   - Evaluated all 25,746 rows across 52 symbols and 496 calendar sessions (2024-10-23 to 2026-10-23).
   - Inverted OHLC ($H < L$ or $O, C \notin [L, H]$): **0**.
   - Non-positive prices ($\le 0$): **0**.
   - `NORMAL_SESSION`: **25,638** (99.58%).
   - `SYNTHETIC_HOLIDAY_BAR`: **103** (0.40%) across 2 known exchange holidays (`2025-03-18` Holi: 51 bars, `2026-01-15` Makar Sankranti/Municipal Election: 52 bars).
   - `STALE_FLAT_BAR`: **3** (0.01%) (`M&M` on 2025-09-08, `ETERNAL` on 2025-04-11 and 2025-04-15).
   - `LARGE_PRICE_DISCONTINUITY`: **2** (0.01%) (`TMPV` on 2025-10-14, `TRENT` on 2026-01-01).
3. **Corporate Action Anomaly Taxonomy**:
   - `TMPV` (2025-10-14, -40.15% drop): Classified as **`VERIFIED_CORPORATE_ACTION`** (Tata Motors Commercial Vehicle / Passenger Vehicle demerger ex-date adjustment).
   - `TRENT` (2026-01-01, -33.05% drop, ratio 0.6752): Classified as **`UNRESOLVED_PRICE_ANOMALY`** (suspected 3:2 bonus/split or unadjusted provider adjustment; pending official NSE circular confirmation).
4. **Research Filter Integration Verification**:
   - `filter_synthetic_holidays: bool = False` is backward-compatible across `historical_data_service.py`, `backtesting_dataset_service.py`, and `backtest_data_access_service.py`.
   - Production operations run unmodified with `filter_synthetic_holidays=False`. Research callers explicitly opt-in to exclude flat holiday bars.
5. **Transaction Cost Model Reconciliation**:
   - Verified statutory equity delivery tariff structure for Indian equity cash segment (SEBI, NSE, Stamp Duty 2020 Amendment, CDSL DP charges, and 18% GST).
   - For a ₹100,000 turnover order:
     - Buy side charges: **₹118.62** (STT ₹100 + NSE ₹2.97 + SEBI ₹0.10 + Stamp ₹15.00 + GST ₹0.55).
     - Sell side charges: **₹119.55** (STT ₹100 + NSE ₹2.97 + SEBI ₹0.10 + CDSL DP fee ₹15.93 + GST ₹0.55).
     - Round-trip delivery friction: **₹238.18** (~11.91 bps).

---

## 2. Research Filter Integration Audit

### Wiring & Call Path Map
- In `backend/data_pipeline/historical_data_service.py`:
  - `get_historical_data(symbol, start_date, end_date, filter_synthetic_holidays=False)`
  - When `filter_synthetic_holidays=True`, invokes `filter_research_market_data(df, drop_stale_flat=False)`.
- In `backend/data_pipeline/backtesting_dataset_service.py`:
  - `build_backtesting_dataset(symbols, start_date, end_date, filter_synthetic_holidays=False)` passes argument down to `get_historical_data`.
- In `backend/data_pipeline/backtest_data_access_service.py`:
  - `get_backtest_input(...)` and `get_backtest_inputs(...)` forward `filter_synthetic_holidays` cleanly.

### Verification of Behavioral Invariance
- Default behavior (`filter_synthetic_holidays=False`) returns 496 bars per stock.
- Filtered behavior (`filter_synthetic_holidays=True`) returns 494 bars per stock (omitting Holi `2025-03-18` and Makar Sankranti `2026-01-15`).
- Standalone research scripts that query SQLite via raw SQL bypass this filter unless they explicitly invoke `filter_research_market_data(df)`.

---

## 3. Market Data Universe Classification Verification

### Summary Metrics
| Metric | Value | Audit-048 Match |
| :--- | :--- | :--- |
| **Total Rows Examined** | 25,746 | Exact Match |
| **Unique Symbols** | 52 | Exact Match |
| **Unique Dates** | 496 | Exact Match |
| **NORMAL_SESSION** | 25,638 (99.58%) | Exact Match |
| **SYNTHETIC_HOLIDAY_BAR** | 103 (0.40%) | Exact Match |
| **STALE_FLAT_BAR** | 3 (0.01%) | Exact Match |
| **LARGE_PRICE_DISCONTINUITY** | 2 (0.01%) | Exact Match |
| **Inverted OHLC ($H < L$)** | 0 | Exact Match |
| **Non-Positive Prices ($\le 0$)** | 0 | Exact Match |

### Anomaly Breakdown
1. **`TMPV` (2025-10-14)**:
   - Previous Close: ₹660.75 | Open: ₹395.00 | High: ₹408.00 | Low: ₹391.10 | Close: ₹395.45.
   - Price Change: **-40.15%**.
   - Reason: Tata Motors demerger into separate commercial and passenger vehicle entities.
   - Formal Status: **`VERIFIED_CORPORATE_ACTION`**.
2. **`TRENT` (2026-01-01)**:
   - Previous Close: ₹4,279.00 | Open: ₹2,865.00 | High: ₹2,910.00 | Low: ₹2,840.00 | Close: ₹2,864.93.
   - Price Change: **-33.05%** (ratio = 0.6752).
   - Reason: Strongly indicates an unadjusted 3:2 corporate action (ratio $\approx 2/3$).
   - Formal Status: **`UNRESOLVED_PRICE_ANOMALY`**.
3. **`M&M` (2025-09-08)**:
   - Previous Close: ₹3,124.50 | O=H=L=C: ₹3,124.50 | Volume: 0.
   - Formal Status: **`STALE_FLAT_BAR`** (Zero trading activity / provider placeholder).
4. **`ETERNAL` (2025-04-11 & 2025-04-15)**:
   - 2025-04-11: O=H=L=C: ₹220.10 | Volume: 0.
   - 2025-04-15: O=H=L=C: ₹220.10 | Volume: 0.
   - Formal Status: **`STALE_FLAT_BAR`**.

---

## 4. Statutory Transaction Cost Reconciliation (Equity Delivery)

### Tariff Comparison: Standard Indian Broker (Zero-Brokerage Delivery)
*Benchmark: ₹100,000 Equity Delivery Buy + ₹100,000 Equity Delivery Sell*

| Fee / Levy Component | Buy Leg (₹100k) | Sell Leg (₹100k) | Round-Trip Total | Statutory Basis |
| :--- | :--- | :--- | :--- | :--- |
| **Brokerage** | ₹0.00 | ₹0.00 | ₹0.00 | Discount broker delivery tariff |
| **Securities Transaction Tax (STT)** | ₹100.00 (0.10%) | ₹100.00 (0.10%) | ₹200.00 | Finance Act / CBDT Delivery Rate |
| **NSE Exchange Transaction Fee** | ₹2.97 (0.00297%) | ₹2.97 (0.00297%) | ₹5.94 | NSE Cash Market Tariff |
| **SEBI Turnover Charges** | ₹0.10 (₹10/Cr) | ₹0.10 (₹10/Cr) | ₹0.20 | SEBI (Payment of Fees) Regs |
| **Stamp Duty** | ₹15.00 (0.015%) | ₹0.00 | ₹15.00 | Indian Stamp Act (2020 Amendment, Buy Leg Only) |
| **CDSL DP Fee** | ₹0.00 | ₹15.93 (₹13.50 + 18% GST) | ₹15.93 | Flat fee per scrip debited on sell leg |
| **GST (18%) on Services** | ₹0.55 | ₹0.55 | ₹1.10 | 18% on (Brokerage + Txn Fee + SEBI Fee) |
| **Total Cash Outflow** | **₹118.62** | **₹119.55** | **₹238.18** | **~11.91 bps total friction** |

---

## 5. 14-Category Independent Research Readiness Assessment

| # | Dimension | Status | Independent Auditor Assessment |
| :--- | :--- | :--- | :--- |
| **1** | **Market Data Cleanliness** | **PASS** | 25,746 rows 100% verified. Zero inverted bars. Holiday flat bars safely isolated. |
| **2** | **Corporate Action Handling** | **CONDITIONAL** | Demerger for `TMPV` verified. `TRENT` requires split adjustment before running momentum setups. |
| **3** | **Fundamental Data PIT** | **CONDITIONAL** | Point-in-time lag rules prevent future leakage, but lacks exact corporate filing timestamps. |
| **4** | **Fundamental Coverage** | **CONDITIONAL** | Staging expands coverage back to FY21, resolving cold start for FY24-FY26. Staging remains unmerged. |
| **5** | **Transaction Cost Realism** | **PASS** | Fully reconciled with Indian Stamp Act, SEBI, STT, and depository tariffs (including DP fees). |
| **6** | **Slippage Modeling** | **PASS** | Evaluated under 0, 10, and 20 bps slippage stress models. |
| **7** | **Execution Assumptions** | **PASS** | Next-day open execution ensures zero lookahead bias from current-day signals. |
| **8** | **Universe Survivorship** | **CONDITIONAL** | Fixed 52-stock universe exhibits historical survivorship bias; must not be used for multi-decade claims. |
| **9** | **Signal Generation Integrity** | **PASS** | Decoupled regime filters from setup conditions; prevents starvation while enforcing discipline. |
| **10** | **Portfolio Simulator Correctness**| **PASS** | Deterministic cash management, position sizing, and stop-loss logic. |
| **11** | **Test Suite Coverage** | **PASS** | 856 core backend tests + 106 dedicated audit tests all pass without failure. |
| **12** | **Database Invariance** | **PASS** | Production DB SHA-256 (`1A2036...`) and Staging DB (`4B5A34...`) 100% invariant. |
| **13** | **Research Infrastructure Isolation**| **PASS** | Experimental scripts, audit test suites, and staging tools cleanly segregated from production code. |
| **14** | **Live Trading Readiness** | **BLOCKED** | Strictly blocked pending corporate action adjustment engines, real-time broker execution API, and survivorship-free universe. |

---

## 6. Audit Conclusion & Recommendations

AUDIT-049 independently ratifies that the Swing Trading Intelligence Platform's research pipeline, data classification, and cost infrastructure are robust, verified, and transparent.

### Immediate Recommendations:
1. **Maintain Production Database Lock**: Do not ingest staging data into `swing_trading.db` until corporate action adjustment mechanisms for `TRENT` and `TMPV` are finalized.
2. **Mandate Research Market Data Filter**: Ensure all future backtest scripts import and apply `filter_research_market_data(df)` or set `filter_synthetic_holidays=True` when accessing market data.
3. **Preserve Survivorship Disclaimers**: All backtest performance figures must explicitly disclose that the universe consists of survivor Nifty 50 constituents as of 2026.

