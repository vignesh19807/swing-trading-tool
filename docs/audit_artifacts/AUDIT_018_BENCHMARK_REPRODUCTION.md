# AUDIT-018: Independent Benchmark Reproduction & Methodology Audit

**Audit Execution Date:** 2026-10-29  
**Execution Environment:** Python 3.14 / SQLite 3 / Pandas 2.2  
**Database Evaluated:** `database/swing_trading.db`  
**Auditor:** Independent Verification Engineer  

---

## 1. Executive Summary

AUDIT-017 reported an equal-weight 52-stock buy-and-hold benchmark return of **-7.60%** (close-to-close) and **-6.84%** (open-to-close) across the evaluation window `2025-10-01` to `2026-03-31` (122 trading days).

An independent reproduction was executed via `scratch/audit_018_reproduce_benchmark.py` directly querying all 52 constituent companies from `daily_prices`. 

### Key Quantitative Verification Results
| Metric / Calculation Convention | Reported in AUDIT-017 | Independently Reproduced (Unrounded) | Reproduced (Display) | Reconciliation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Close-to-Close Equal-Weight Return** | -7.60% | `-7.5961%` | **-7.60%** | **EXACT MATCH** |
| **Open-to-Close Equal-Weight Return** | -6.84% | `-6.8434%` | **-6.84%** | **EXACT MATCH** |
| **Daily-Rebalanced Equal-Weight Return**| Not reported | `-8.1503%` | **-8.15%** | **VERIFIED** |
| **Trading Days / Observations** | 122 sessions | 122 sessions | 122 sessions | **EXACT MATCH** |
| **Strategy vs. Benchmark Spread (C2C)** | +8.58% | `+0.9783% - (-7.5961%) = +8.5744%` | **+8.58%** | **EXACT MATCH** |

---

## 2. Benchmark Specification & Methodology

1. **Constituent Universe:**
   - Exactly 52 NSE-listed companies defined in `companies`.
   - The strategy evaluation and the benchmark evaluation utilize the identical 52 symbols:
     `ADANIENT`, `ADANIPORTS`, `APOLLOHOSP`, `ASIANPAINT`, `AXISBANK`, `BAJAJ-AUTO`, `BAJAJFINSV`, `BAJFINANCE`, `BEL`, `BHARTIARTL`, `BPCL`, `BRITANNIA`, `CIPLA`, `COALINDIA`, `DRREDDY`, `EICHERMOT`, `GRASIM`, `HCLTECH`, `HDFCBANK`, `HDFCLIFE`, `HEROMOTOCO`, `HINDALCO`, `HINDUNILVR`, `ICICIBANK`, `INDUSINDBK`, `INFY`, `ITC`, `JSWSTEEL`, `KOTAKBANK`, `LT`, `M&M`, `MARUTI`, `NESTLEIND`, `NTPC`, `ONGC`, `POWERGRID`, `RELIANCE`, `SBILIFE`, `SBIN`, `SHRIRAMFIN`, `SUNPHARMA`, `TATACONSUM`, `TATAMOTORS`, `TATASTEEL`, `TCS`, `TECHM`, `TITAN`, `TMPV`, `TRENT`, `ULTRACEMCO`, `WIPRO`, `ZOMATO`.

2. **Date Range & Price Conventions:**
   - **Start Date:** `2025-10-01`
   - **End Date:** `2026-03-30` (the 122nd trading session within the window ending 2026-03-31)
   - **Close-to-Close Formula:**
     $$\text{Return}_{\text{C2C}} = \frac{1}{N} \sum_{i=1}^{N} \frac{P_{i, \text{end}}^{\text{close}} - P_{i, \text{start}}^{\text{close}}}{P_{i, \text{start}}^{\text{close}}} = -7.5961\%$$
   - **Open-to-Close Formula:**
     $$\text{Return}_{\text{O2C}} = \frac{1}{N} \sum_{i=1}^{N} \frac{P_{i, \text{end}}^{\text{close}} - P_{i, \text{start}}^{\text{open}}}{P_{i, \text{start}}^{\text{open}}} = -6.8434\%$$
   - **Daily Rebalanced Formula:**
     $$R_{\text{daily\_reb}} = \prod_{t=1}^{T} \left(1 + \frac{1}{N} \sum_{i=1}^{N} r_{i, t}\right) - 1 = -8.1503\%$$

3. **Data Completeness & Missing Prices:**
   - Every one of the 52 companies has complete price records for all 122 trading sessions (zero missing rows, zero null values, zero interpolation required).

4. **Dividends & Corporate Actions:**
   - This benchmark is a pure capital appreciation index (Price Return). Dividend yields and corporate spinoff adjustments are not included in the raw price series.

---

## 3. Distribution of Constituent Returns

Across the 52 stocks over the 6-month period:
- **Mean Return:** -7.60%
- **Median Return:** -6.50%
- **Standard Deviation:** 17.33%
- **Best Performer:** `SHRIRAMFIN` (+34.44%)
- **Worst Performer:** `TMPV` (-58.77%)
- **Positive Stocks:** 16 / 52 (30.8%)
- **Negative Stocks:** 36 / 52 (69.2%)

Over two-thirds of the universe declined during this 6-month market correction.

---

## 4. Quantitative Interpretation & Alpha Boundary

The strategy outperformed the equal-weight benchmark by **+8.57%** (close-to-close) and **+7.82%** (open-to-close):

$$\text{Strategy Return} (+0.98\%) - \text{Benchmark Return} (-7.60\%) = +8.58\%$$

> [!IMPORTANT]
> **Audit Finding on "Alpha":**
> This outperformance **must not be characterized as proven alpha or demonstrated trading edge**. 
> The platform spent **95.9% of the simulation duration in cash** due to strict quality gate rejection of 254 out of 255 signals. The relative outperformance was primarily achieved through capital preservation during an equity bear phase, combined with a single winning trade ($N=1$). A sample size of one trade is statistically insufficient to infer statistical edge.

