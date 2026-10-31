# AUDIT-018: Independent Reproduction of the Controlled 52-Stock Backtest

**Audit Execution Date:** 2026-10-29  
**Execution Environment:** Python 3.14 / SQLite 3 / Pandas 2.2  
**Database Evaluated:** `docs/audit_artifacts/temp_pilot_audit_018.db`  
**Run ID:** `audit_018_52stock_reproduction`  
**Auditor:** Independent Verification Engineer  

---

## 1. Executive Summary

AUDIT-017 reported a controlled historical simulation of all 52 active stocks across 122 trading sessions (`2025-10-01` to `2026-03-31`), yielding 255 raw BUY recommendations, 254 quality-gate rejections, 1 executed trade (`SUNPHARMA`), and a net profit of ₹978.32 (+0.98% portfolio return).

An independent reproduction script (`scratch/audit_018_reproduce_52stock_pilot.py`) executed all 6,344 stock-sessions across the decision engine, risk filters, and portfolio simulator on an isolated database copy.

### Verification Verdict
The 52-stock pilot results are **100% deterministic and reproducible**:
- **Stocks Evaluated:** 52
- **Stock-Sessions Evaluated:** 6,344
- **Raw BUY Recommendations:** 255 (Exact match)
- **Signals Rejected by Quality Gates:** 254 (Exact match)
- **Qualified & Executed Trades:** 1 (Exact match: `SUNPHARMA`)
- **Gross Profit:** ₹1,021.2477
- **Transaction Friction:** ₹42.9324
- **Net Realized Profit:** ₹978.3153 $\rightarrow$ **₹978.32**
- **Final Portfolio Equity:** **₹100,978.32** (+0.98% return, Max Drawdown 0.02%)
- **Benchmark Outperformance:** **+8.58%** vs. 52-stock equal-weight benchmark (-7.60%).

---

## 2. Signal Generation & Rejection Accounting

Across the 6,344 historical stock-sessions:
- **Total Signals Generated:** 6,344
- **HOLD / WATCH Recommendations:** 6,089 (96.0%)
- **Raw BUY Recommendations:** 255 (4.0%)

### Granular Rejection Taxonomy (254 Rejected Signals)
Every raw BUY signal was tracked through the upstream quality gates:

| Rejection Gate / Reason | Count | Percentage of Rejections | Root Cause Description |
| :--- | :--- | :--- | :--- |
| `PRICE_OUTSIDE_ENTRY_ZONE` | 202 | 79.53% | Market price exceeded upper entry boundary or fell below lower support zone |
| `INSUFFICIENT_RISK_REWARD_RATIO` | 37 | 14.57% | Potential reward-to-risk ratio was below the minimum 1.50:1 threshold |
| `TARGET_BELOW_ENTRY_PRICE` | 9 | 3.54% | Resistance-based target level was below entry price (inverted setup) |
| `TARGET_BELOW_CURRENT_PRICE` | 6 | 2.36% | Nearest resistance target already exceeded by market close |
| **Total Rejected Signals** | **254** | **100.00%** | **Rejection Rate: 99.61% of raw BUYs** |
| **Eligible Signals** | **1** | — | **`SUNPHARMA` on `2026-02-27`** |

Every single one of the 255 raw BUY recommendations has an accounted-for outcome (254 rejected, 1 qualified). There are zero dangling or unaccounted-for signals.

---

## 3. Trade Ledger Verification

Exactly one trade met all entry zone and risk criteria:

| Trade Property | Value | Audit Verification |
| :--- | :--- | :--- |
| **Trade ID** | `audit_018_52stock_reproduction_SUNPHARMA_2026-03-02_1` | Unique across entire database |
| **Symbol** | `SUNPHARMA` | Verified |
| **Direction** | `LONG` | Verified delivery long |
| **Signal Date** | `2026-02-27` | Verified |
| **Entry Date** | `2026-03-02` | Next trading session open |
| **Raw Entry Price** | ₹1,712.0000 | Official open price on 2026-03-02 |
| **Entry Price (with slippage)**| ₹1,712.8560 | $+0.05\%$ adverse slippage |
| **Stop Loss** | ₹1,691.3860 | Support-based stop loss |
| **Target Price** | ₹1,806.6000 | Resistance-based target |
| **Risk / Reward Ratio** | 1.5258 | $\ge 1.50$ threshold |
| **Quantity** | 11 whole shares | $\lfloor 20,000 / 1712.856 \rfloor$ |
| **Invested Capital** | ₹18,841.4160 | 18.84% portfolio allocation ($\le 20\%$) |
| **Exit Date** | `2026-03-09` | Verified |
| **Exit Trigger** | `TARGET_REACHED` | High ₹1,815.00 $\ge$ Target ₹1,806.60 |
| **Raw Exit Price** | ₹1,806.6000 | Max(Open, Target) |
| **Exit Price (with slippage)** | ₹1,805.6967 | $-0.05\%$ adverse slippage |
| **Holding Period** | 5 trading sessions | 2026-03-02 to 2026-03-09 |
| **Gross P/L** | +₹1,021.2477 | $(1805.6967 - 1712.8560) \times 11$ |
| **Entry Friction Costs** | ₹22.3501 | STT, NSE, SEBI, Stamp Duty, GST |
| **Exit Friction Costs** | ₹20.5823 | STT, NSE, SEBI, GST |
| **Total Transaction Friction** | ₹42.9324 | Itemized sum |
| **Net Realized P/L** | **+₹978.3153** | Gross P/L - Total Costs |
| **Trade Net Return** | **+5.1924%** | On invested capital |

---

## 4. Portfolio Performance Reconciliation

The portfolio simulator began with ₹100,000.00 cash and evaluated the portfolio on each of the 122 trading sessions:

| Metric | Pre-Simulation | Trade Open (2026-03-02) | Trade Close (2026-03-09) | End of Backtest (2026-03-31) |
| :--- | :--- | :--- | :--- | :--- |
| **Cash Balance (₹)** | 100,000.00 | 81,136.23 | 100,978.32 | 100,978.32 |
| **Open Positions Count** | 0 | 1 | 0 | 0 |
| **Open Position Value (₹)** | 0.00 | 18,841.42 | 0.00 | 0.00 |
| **Total Equity (₹)** | 100,000.00 | 99,977.65 | 100,978.32 | 100,978.32 |
| **Peak Equity (₹)** | 100,000.00 | 100,000.00 | 100,978.32 | 100,978.32 |
| **Current Drawdown (%)** | 0.00% | 0.02% | 0.00% | 0.00% |

- **Net Profit:** +₹978.32
- **Net Portfolio Return:** +0.9783% (+0.98%)
- **Maximum Drawdown:** 0.0219% (0.02%)
- **Win Rate:** 100% (1 win / 1 trade)
- **Profit Factor:** $\infty$ (zero losing trades)
- **Time in Cash:** 117 of 122 sessions (95.9%)
- **Database Persistence:** Persisted in `docs/audit_artifacts/temp_pilot_audit_018.db` (Run ID: `audit_018_52stock_reproduction`, 1 trade, 122 equity curve records).

---

## 5. Statistical Rigor & Limitations

While the simulation is technically and mathematically flawless, it must not be interpreted as statistical evidence of positive expectancy:

$$\text{Sample Size } N = 1 \text{ is statistically insignificant.}$$

The positive return (+0.98%) and outperformance (+8.58% vs. the -7.60% market benchmark) were predominantly the result of **capital preservation** (standing in cash) during a prevailing downtrend, augmented by one lucky or well-timed pharmaceutical trade. Multi-year backtesting across the full 100-stock universe is mandatory before capital deployment.

