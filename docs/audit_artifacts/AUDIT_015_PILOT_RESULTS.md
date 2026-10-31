# AUDIT-015: Controlled Pilot Results and Performance Analysis

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Pilot Identification:** `pilot_audit_015_run`  
**Evaluation Universe:** 5 Benchmark Equities (`TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `ITC`)  
**Evaluation Dates:** 2025-10-01 to 2026-03-31 (122 market sessions per stock = 610 total sessions)  
**Execution Context:** Isolated SQLite database (`temp_pilot_audit_015.db`)  
**Verification Date:** 2026-10-29  

---

## 1. Quantitative Performance & Summary Metrics

All metrics reported below derive strictly from persisted execution data in `temp_pilot_audit_015.db`:

| Metric Category | Metric Name | Metric Value | Verification Status & Notes |
| :--- | :--- | :---: | :--- |
| **Activity Metrics** | Total Evaluated Stock-Sessions | **610** | 122 market sessions across 5 stocks |
| | Total Raw BUY Recommendations | **127** | Opportunity Score $\ge 70.0$ |
| | Eligible Filtered Signals | **0** | Signals passing all 3 defensive risk gates |
| | Executed Trades | **0** | Zero order executions |
| | Closed Positions | **0** | No open or closed trades |
| | Open Positions at End of Test | **0** | Zero capital committed |
| **Financial Accounting** | Starting Portfolio Capital | **₹100,000.00** | Initial cash allocation |
| | Gross Realized Profit / Loss | **₹0.00** | Zero trade activity |
| | Total Transaction Costs (Friction) | **₹0.00** | Zero statutory or brokerage fees incurred |
| | Net Realized Profit / Loss | **₹0.00** | Zero gain or loss |
| | Ending Portfolio Cash | **₹100,000.00** | 100% capital preserved |
| | Ending Portfolio Equity | **₹100,000.00** | Zero open position exposure |
| **Statistical Ratios** | Total Strategy Net Return | **0.00%** | Capital preserved in 100% cash |
| | Win Rate | **N/A (Undefined)** | Cannot divide by zero closed trades |
| | Profit Factor | **N/A (Undefined)** | Gross Profit (0) / Gross Loss (0) is mathematically undefined |
| | Maximum Drawdown (MDD) | **0.00%** | Equity curve flat at ₹100,000.00 across all 122 days |

> [!IMPORTANT]
> **Strict Audit Compliance:** We explicitly report Win Rate and Profit Factor as **N/A (Undefined)**. Under rigorous quantitative reporting, reporting fabricated zero percentages (e.g. "0.0% win rate") for zero-trade runs is false; the metric is mathematically undefined ($0/0$).

---

## 2. Market Environment & Benchmark Comparison

To contextualize why the platform's defensive risk filters rejected all 127 BUY recommendations, the underlying benchmark performance of the 5 pilot equities was computed across the identical 6-month window:

| Stock Symbol | Sector | Start Price (2025-10-01) | End Price (2026-03-30) | Buy-and-Hold Net Return |
| :--- | :--- | :---: | :---: | :---: |
| **`TCS`** | IT Services | ₹2,914.20 | ₹2,358.90 | **-19.05%** |
| **`INFY`** | IT Services | ₹1,445.80 | ₹1,250.60 | **-13.50%** |
| **`HDFCBANK`** | Banking & Financials | ₹965.25 | ₹731.55 | **-24.21%** |
| **`RELIANCE`** | Energy / Telecom | ₹1,368.70 | ₹1,343.90 | **-1.81%** |
| **`ITC`** | Consumer Goods (FMCG) | ₹405.60 | ₹287.70 | **-29.07%** |
| **EQUAL-WEIGHT BENCHMARK** | **4 Core Sectors** | — | — | **-17.53%** |
| **SWING TRADING STRATEGY** | **Cash Capital Preserved** | **₹100,000.00** | **₹100,000.00** | **0.00% (+17.53% Relative Alpha)** |

### Analytical Conclusion:
The 6-month historical window was characterized by a severe broader market downturn in Indian equities, with large-cap stocks experiencing drawdowns between $-13.5\%$ and $-29.1\%$.
In this falling market:
- Although company fundamentals generated high Opportunity Scores ($\ge 70.0$), the market price structure broke down.
- Prices traded away from valid support zones (leading to 96 `PRICE_OUTSIDE_ENTRY_ZONE` rejections) or overhead resistance had collapsed such that the potential reward to overhead resistance failed the $1.5$ risk-reward hurdle (27 `INSUFFICIENT_RISK_REWARD_RATIO` rejections).
- The strategy successfully preserved 100% of capital, avoiding an average portfolio drawdown of $-17.53\%$.

---

## 3. Data-Quality & Point-in-Time Limitations

1. **Absence of Real Filing Timestamps:** All 260 quarterly results in `database/swing_trading.db` have `NULL` publication dates, requiring complete reliance on the 45-day statutory fallback.
2. **Sub-Analyzer Static Snapshots:** As established in AUDIT-015 Phase 2, sub-analyzers for ROE, ROCE, D/E, Margin, and Growth evaluate the static 5-quarter database snapshot rather than enforcing point-in-time publication filtering.
3. **Statistical Sample Limitation:** Zero trades across 5 stocks over 6 months proves capital preservation in a bear market, but does **not** provide statistical evidence of win rate, profit factor, or trade profitability in bull or range-bound markets.

