# AUDIT-016: Benchmark Validation & Comparative Methodology

**Audit Phase:** Phase 5 — Buy-and-Hold Benchmark Recalculation & Comparability Analysis  
**Execution Timestamp:** 2026-10-29T21:23:30+05:30  
**Status:** INDEPENDENTLY RECALCULATED & VERIFIED  

---

## 1. Benchmark Execution Parameters

* **Stock Universe:** 5 Benchmark stocks (`TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `ITC`) across 4 sectors (IT, Private Banking, Energy, FMCG).
* **Evaluation Window:** `2025-10-01` to `2026-03-31` (122 active market trading sessions).
* **Start Date:** `2025-10-01`
* **End Date:** `2026-03-30` (Final trading session of the fiscal half-year; March 31, 2026 was a market exchange holiday).
* **Missing Price Handling:** All 5 stocks have complete 122-day continuous daily records in `daily_prices` (610 total stock-sessions; 0 missing values).
* **Portfolio Weighting:** Equal-weight (20.0% capital allocation per constituent at inception).

---

## 2. Stock-Level Price and Return Analysis

| Ticker Symbol | Sector | Trading Sessions | Start Date | End Date | Inception Close (₹) | Terminal Close (₹) | Close-to-Close Return | Inception Open (₹) | Open-to-Close Return | Period Low (₹) | Period High (₹) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TCS** | IT Services | 122 | 2025-10-01 | 2026-03-30 | 2,914.20 | 2,358.90 | **-19.05%** | 2,891.00 | -18.41% | 2,356.00 | 3,324.90 |
| **INFY** | IT Services | 122 | 2025-10-01 | 2026-03-30 | 1,445.80 | 1,250.60 | **-13.50%** | 1,446.00 | -13.51% | 1,220.80 | 1,689.80 |
| **HDFCBANK** | Banking | 122 | 2025-10-01 | 2026-03-30 | 965.25 | 731.55 | **-24.21%** | 952.70 | -23.21% | 731.55 | 1,009.50 |
| **RELIANCE** | Energy | 122 | 2025-10-01 | 2026-03-30 | 1,368.70 | 1,343.90 | **-1.81%** | 1,367.00 | -1.69% | 1,343.90 | 1,592.30 |
| **ITC** | FMCG | 122 | 2025-10-01 | 2026-03-30 | 405.60 | 287.70 | **-29.07%** | 402.35 | -28.50% | 287.70 | 421.60 |

---

## 3. Portfolio Return Aggregation

$$\text{Portfolio Return}_{\text{Close-to-Close}} = \frac{1}{5} \sum_{i=1}^{5} R_{i,\text{close}} = \frac{-19.05\% - 13.50\% - 24.21\% - 1.81\% - 29.07\%}{5} = \mathbf{-17.53\%}$$

$$\text{Portfolio Return}_{\text{Open-to-Close}} = \frac{1}{5} \sum_{i=1}^{5} R_{i,\text{open}} = \frac{-18.41\% - 13.51\% - 23.21\% - 1.69\% - 28.50\%}{5} = \mathbf{-17.06\%}$$

---

## 4. Corporate Actions and Dividends

1. **Price Adjustment:** The underlying `daily_prices` series reflects standard corporate split and bonus adjustments as provided by historical exchanges.
2. **Dividends:** Dividend cash distributions during this period are unadjusted in price series (cash dividends do not inflate closing capital). Given the substantial capital declines (-13% to -29%), standard dividend yields (~1.0–2.0% annualized) would have negligible effect on the aggregate portfolio drawdown.

---

## 5. Comparability Analysis and Methodological Limitations

> [!WARNING]
> **Disciplined Interpretation of Cash Preservation:**
> - The simulated swing trading strategy remained 100% in cash during the evaluation period because its risk filters rejected candidate entries.
> - Preserving capital (₹100,000.00 initial $\rightarrow$ ₹100,000.00 final, 0.00% return) outperformed the buy-and-hold benchmark (-17.53%) by +17.53% net.
> - **However, cash preservation during a bear market is NOT proof of positive trading edge, profitability, or superior signal generation.**
> - A purely inactive cash account would achieve the exact same 0.00% return.
> - The benchmark comparison confirms that the platform's multi-layered risk filters (pullback support gate and risk/reward $\ge 1.5$) successfully prevented capital destruction in an adverse market environment, but cannot substitute for out-of-sample bull-market trade execution testing.

