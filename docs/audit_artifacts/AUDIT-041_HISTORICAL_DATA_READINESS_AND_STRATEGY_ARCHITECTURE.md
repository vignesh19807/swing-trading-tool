# AUDIT-041: HISTORICAL DATA READINESS & STRATEGY ARCHITECTURE DECISION

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Working Directory:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Checksum (SHA-256):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Verified Invariant)  
**Date of Audit:** 2026-11-01T13:36:00+05:30  
**Audit Role:** Senior Quantitative Research Engineer, Financial-Data Engineer, Backtesting Auditor, and Python Software Auditor  

---

## 1. Executive Summary

### 1.1 Scope & Mission
This audit investigated the historical financial-data readiness of the platform, performed a comprehensive company-by-company data inventory, verified the mathematical cold-start root cause, analyzed the internal consistency of the strategy architecture, and reconciled all baseline candidate and trade metrics.

In accordance with strict audit directives:
* **The trading strategy rules, scoring formulas, and risk parameters remained completely frozen.**
* No parameters were tuned or optimized.
* All user files and working-tree modifications were preserved.
* The production database remained read-only and invariant.

### 1.2 Formal Audit Decisions
* **Historical Financial Data Readiness:** **NOT READY FOR PRE-2026 EVALUATION / CONDITIONALLY READY FOR POST-FEB-2026 RESEARCH**
  * The database only contains 5 quarters starting at `2025-Q1`. Due to multi-quarter calculation dependencies (4 quarters for TTM EPS and 5 quarters for YoY growth) combined with statutory 45-day filing lags, the financial engine was completely paralyzed for the first 11 months of the backtest (2025-04-01 to 2026-02-13, 217 sessions, 11,284 stock-sessions).
  * 100% of quarterly records (260/260) lack exchange filing timestamps (`publication_date IS NULL`), forcing reliance on statutory estimates.
* **Strategy Architecture:** **REQUIRES DESIGN DECISION**
  * The platform mixes two mutually incompatible trading paradigms: an upstream **Momentum Breakout** Decision Engine ($\text{Opp} \ge 75$, heavily rewarding high RSI, MACD positive crossovers, and EMA bullish stacks) coupled to a downstream **Deep Support Pullback** Signal Engine ($\text{support} \le P \le \text{support} + 0.5 \times \text{ATR}$).
  * This clash accounts for 77.10% (1,407 of 1,825) of all raw BUY rejections. In 100% of these rejections, the momentum breakout price had already expanded above the pullback zone ($p_{50} = +2.68\%$).
* **Strategy Evidence:** **NEGATIVE BASELINE RESULTS OBSERVED / POSITIVE EDGE NOT ESTABLISHED**
  * Baseline portfolio return: **-1.2237% (-₹1,223.69)** vs. **+2.9225%** benchmark return (negative alpha: **-4.1462%**).
  * 3 wins, 5 losses (37.50% win rate), expectancy = **-₹152.96 per trade**.
  * Sample size ($N=8$) is statistically inconclusive ($p = 0.67$).
* **Live Capital Deployment:** **STRICTLY DISAPPROVED / BLOCKED.**

---

## 2. Repository & Database Baseline State

* **Git Branch:** `main`
* **Commit HEAD:** `dc0555e39024ba075dc93da7d59896e8037a3be9`
* **Local Path:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`
* **Primary Database Path:** `database/swing_trading.db`
* **File Size:** `9,068,544 bytes`
* **Modification Timestamp:** `2026-10-29T22:47:42`
* **SHA-256 Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
* **Integrity Status:** `PRAGMA integrity_check` = `ok`
* **Table Counts:** 14 tables (companies: 52, daily_prices: 25,746, technical_indicators: 25,746, quarterly_results: 260, sectors: 17, industries: 45, backtest_equity_curve: 125, backtest_results: 2, backtest_runs: 2, backtest_trades: 1).

---

## 3. Independent Reproduction & Candidate Reconciliation

Every baseline count reported in AUDIT-040 was independently traced and verified directly against `scratch/multiyear_eval_cache.json` and `docs/audit_artifacts/audit_025_multiyear_results.json`:

```
Total Evaluated Stock-Sessions: 20,124 (52 stocks * 387 sessions)
  │
  ├── Financial Cold-Start Dormant (Pre-2026-02-13): 11,284 stock-sessions (217 dates * 52)
  │     └── Result: financial_score is None -> Recommendation = INSUFFICIENT_DATA
  │
  └── Active Stock-Sessions with Opportunity Scores: 8,840 stock-sessions (170 dates * 52)
        │
        ├── Non-BUY Recommendations (WATCH/HOLD/AVOID): 7,015 (79.36% of active)
        │
        └── Raw BUY Candidates (Opportunity Score >= 75.0): 1,825 (20.64% of active / 9.07% of total)
              │
              ├── Signal Quality Filter Rejections: 1,814 (99.40% of Raw BUYs)
              │     ├── PRICE_OUTSIDE_ENTRY_ZONE: 1,407 (77.10% of raw BUYs)
              │     ├── INSUFFICIENT_RISK_REWARD_RATIO: 305 (16.71% of raw BUYs)
              │     ├── TARGET_BELOW_ENTRY_PRICE: 84 (4.60% of raw BUYs)
              │     └── TARGET_BELOW_CURRENT_PRICE: 18 (0.99% of raw BUYs)
              │
              └── Eligible Trading Signals: 11 (0.60% of Raw BUYs)
                    │
                    ├── Blocked by Portfolio Concurrency (ALREADY_IN_POSITION): 3
                    │     ├── WIPRO on 2026-04-17 (active trade entered 2026-04-16)
                    │     ├── ETERNAL on 2026-04-20 (active trade entered 2026-04-17)
                    │     └── ETERNAL on 2026-04-21 (active trade entered 2026-04-17)
                    │
                    └── Executed Portfolio Trades: 8 (0.44% of Raw BUYs)
                          └── Open Positions at Close (2026-10-23): 0
```

### Exact Reconciliations:
* **Rejections + Eligible:** $1,407 + 305 + 84 + 18 + 11 = 1,825$ (100.0% reconciled).
* **Executed + Blocked:** $8 + 3 = 11$ (100.0% reconciled).
* **Cold-Start + Active:** $11,284 + 8,840 = 20,124$ (100.0% reconciled).

---

## 4. Historical Financial-Data Inventory & Availability Limitations

### 4.1 Company & Metric Coverage Inventory
* **Total Companies:** 52 large-cap equities.
* **Total Quarterly Result Records:** 260 rows ($52 \times 5$ quarters).
* **Quarters Present:** `2025-Q1`, `2025-Q2`, `2025-Q3`, `2025-Q4`, `2026-Q1`.
* **Metric Null Count (across all 260 rows):**
  * `revenue`: 0 nulls (100% complete)
  * `net_profit`: 0 nulls (100% complete)
  * `eps`: 0 nulls (100% complete)
  * `roe`: 0 nulls (100% complete)
  * `roce`: 0 nulls (100% complete)
  * `debt_equity`: 0 nulls (100% complete)
  * `operating_margin`: 0 nulls (100% complete)
  * `net_margin`: 0 nulls (100% complete)
* **Publication Timestamp Defect (`FND-001`):**
  * `publication_date`: **260 out of 260 (100.0%) are NULL**.
  * No corporate board meeting or exchange disclosure timestamps exist in the database.
  * Point-in-time eligibility relies entirely on an empirical statutory lag assumption:
    $$\text{Eligible Date} = \text{period\_end\_date} + 45\text{ calendar days}$$
    (Derived from SEBI LODR Regulation 33 deadline).

### 4.2 Chronological Eligibility Progression
| Quarter | Period Start | Period End | Statutory 45-Day Availability Date | Active Backtest Period |
| :---: | :---: | :---: | :---: | :--- |
| `2025-Q1` | 2025-01-01 | 2025-03-31 | **2025-05-15** | Pre-availability: 2025-04-01 to 2025-05-14 (30 sessions) |
| `2025-Q2` | 2025-04-01 | 2025-06-30 | **2025-08-14** | 1 Quarter active: 2025-05-15 to 2025-08-13 (64 sessions) |
| `2025-Q3` | 2025-07-01 | 2025-09-30 | **2025-11-14** | 2 Quarters active: 2025-08-14 to 2025-11-13 (62 sessions) |
| `2025-Q4` | 2025-10-01 | 2025-12-31 | **2026-02-14** | 3 Quarters active: 2025-11-14 to 2026-02-13 (61 sessions) |
| `2026-Q1` | 2026-01-01 | 2026-03-31 | **2026-05-15** | 4 Quarters active: 2026-02-14 to 2026-05-14 (61 sessions) |
| — | — | — | — | 5 Quarters active: 2026-05-15 to 2026-10-23 (109 sessions) |

---

## 5. Financial Cold-Start Root-Cause Verification

### 5.1 Source-Code Architectural Constraint
In [`backend/engines/financial_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/financial_engine.py#L345-L355):
```python
# 6. Composite Score & Dynamic Re-Weighting (40% Profitability / 35% Growth / 25% Valuation)
subscores = []
if profitability_score is not None:
    subscores.append(("profitability", profitability_score, 0.40))
if growth_score is not None:
    subscores.append(("growth", growth_score, 0.35))
if valuation_score is not None:
    subscores.append(("valuation", valuation_score, 0.25))

if len(subscores) < 2:
    overall_score = None
```

### 5.2 Multi-Quarter Calculation Dependencies
1. **Profitability Sub-Score (ROE, ROCE, Margin, D/E):**
   * Computable with **1 quarter** of data.
   * Became available on 2025-05-15.
2. **Valuation Sub-Score (TTM EPS & P/E Ratio):**
   * Code in [`backend/logic/valuation_analyzer.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/valuation_analyzer.py#L125) requires at least **4 consecutive quarters** to compute Trailing Twelve Month EPS:
     $$\text{TTM EPS} = \sum_{q=1}^{4} \text{EPS}_q$$
   * With 1, 2, or 3 quarters, `ttm_eps = None`, `pe_ratio = None`, and `valuation_score = None`.
   * Exactly 4 quarters (`2025-Q1` through `2025-Q4`) only became eligible on **2026-02-14**.
3. **Growth Sub-Score (YoY Revenue & Net Profit Growth):**
   * Code in [`backend/logic/growth_analyzer.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/growth_analyzer.py#L240) requires **5 quarters** to compare Quarter $T$ with Quarter $T-4$:
     $$\text{YoY Growth} = \frac{\text{Revenue}_T - \text{Revenue}_{T-4}}{\text{Revenue}_{T-4}}$$
   * 5 quarters (`2025-Q1` through `2026-Q1`) only became eligible on **2026-05-15**.

### 5.3 The 11-Month Blackout Consequence
From 2025-04-01 until 2026-02-13 (217 trading sessions):
* `subscores` contained only `profitability` (`len(subscores) == 1 < 2`).
* `overall_score` was forced to `None`.
* In `decision_engine.py`:
  ```python
  if technical_score is None or financial_score is None:
      return {"recommendation": "INSUFFICIENT_DATA"}
  ```
* Every single stock on every single session evaluated to `INSUFFICIENT_DATA`.
* **Finding:** The in-sample period (2025-04-01 to 2026-03-31, 247 sessions) had only **30 operational sessions** (2026-02-16 to 2026-03-31), producing exactly 1 executed trade (`SUNPHARMA`).

---

## 6. Strategy Architecture Consistency Analysis

### 6.1 Upstream Paradigm: Momentum & Trend Breakout
The composite Opportunity Score in [`backend/engines/decision_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/engines/decision_engine.py) is formulated as:
$$\text{Opportunity Score} = 0.40 \times \text{Tech} + 0.35 \times \text{Fin} + 0.25 \times \text{Mom}$$
* **Technical Score:** Rewards Price > EMA20 > EMA50 > EMA200 (bullish stack), RSI 50–70, and MACD line > Signal line.
* **Momentum Score:** Derived directly from RSI (50%) and MACD (50%).
* **Net RSI + MACD Influence:** $40\% \times 60\% + 25\% \times 100\% = \mathbf{49\%}$ of the final Opportunity Score.
* To achieve $\text{Opportunity Score} \ge 75.0$, a stock must be actively breaking out in an aggressive upward momentum surge.

### 6.2 Downstream Paradigm: Deep Support Pullback
In [`backend/logic/signal_engine.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/signal_engine.py#L90-L105):
$$\text{Entry Zone} = [ \text{support\_level}, \text{support\_level} + 0.50 \times \text{ATR}_{14} ]$$
$$\text{Condition: } \text{support\_level} \le \text{current\_price} \le \text{support\_level} + 0.50 \times \text{ATR}_{14}$$
* Where `support_level` is the nearest swing pivot low below the current price.
* $0.50 \times \text{ATR}$ is approximately $0.75\%$ to $1.25\%$ of price.
* The rule requires the stock to be within $\approx 1\%$ of its prior swing low.

### 6.3 The Inevitable Collision
* When a stock develops the bullish momentum required to score $\ge 75$, its price has inevitably expanded away from its prior swing low.
* In **100.0% of the 1,407 rejections**, closing price was above the upper bound ($p_{50} = +2.68\%$ above the entry zone).
* Conversely, when a stock pulls back to within 0.5 ATR of support, its momentum indicators (RSI and MACD) decay, dragging the Opportunity Score into `WATCH` or `HOLD` territory.
* **Conclusion:** The current architecture suffers from an unresolved **paradigm clash**. It attempts to apply a mean-reverting pullback execution gate to a trend-following momentum signal.

---

## 7. Conceptual Strategy Alternatives (Without Optimization)

To resolve the architectural clash without curve-fitting, three clean conceptual designs are defined:

### Alternative A — Pure Momentum Breakout Strategy
* **Philosophy:** "Buy high, sell higher." Trade momentum continuation.
* **Entry Logic:** 
  * Trigger: Opportunity Score $\ge 75.0$ AND closing price breaks above prior 20-day swing high (resistance).
  * Entry Zone: $[\text{Resistance}, \text{Resistance} + 0.50 \times \text{ATR}]$ (Breakout Entry) or $[\text{EMA}_{20} - 0.25 \times \text{ATR}, \text{EMA}_{20} + 0.25 \times \text{ATR}]$ (Moving Average Pullback).
* **Stop-Loss:** Structural stop below breakout pivot or trailing below EMA 50 ($\text{Breakout Level} - 1.0 \times \text{ATR}$).
* **Target:** Dynamic ATR expansion ($2.0 \times \text{ATR}$ to $3.0 \times \text{ATR}$) or trailing chandelier exit.
* **Failure Modes:** False breakouts ("bull traps"), whipsaws during range-bound chop.

### Alternative B — Pure Support Pullback Strategy
* **Philosophy:** "Buy low in an uptrend." Mean-reversion to value.
* **Scoring Modification:** Redesign Decision Engine to reward **pullback quality** rather than breakout momentum:
  * Trend Filter: Price > 200 EMA (Macro Bullish).
  * Momentum Oscillator: RSI in oversold territory ($30 \le \text{RSI} \le 45$), MACD histogram troughing.
* **Entry Logic:** Price enters Support Zone $[\text{Support}, \text{Support} + 0.50 \times \text{ATR}]$ with bullish reversal candlestick (hammer, engulfing).
* **Stop-Loss:** $\text{Support} - 1.0 \times \text{ATR}$.
* **Target:** Prior swing high / overhead resistance ($R:R \ge 1.50$).
* **Failure Modes:** Trend breakdown ("knife-catching"), support failure in broad market corrections.

### Alternative C — Dual-Setup Hybrid Architecture (Recommended Institutional Model)
* Explicitly branch into two distinct setup handlers:
  ```
  Decision Engine Evaluation
    │
    ├── Condition 1: RSI > 60, MACD Bullish Stack, Price near Highs
    │     └── Classify: MOMENTUM_BREAKOUT_SETUP -> Route to Breakout Entry Filters
    │
    └── Condition 2: 200 EMA Bullish, RSI 30-45, Price touching Support
          └── Classify: SUPPORT_PULLBACK_SETUP -> Route to Pullback Entry Filters
  ```
* Eliminates the conflict by decoupling the entry zone definition from the market regime.

---

## 8. Independent Trade-Ledger Integrity Reconciliation

The 8 executed portfolio trades from `sim_FULL_10bps` were independently audited:

| # | Symbol | Entry Date | Exit Date | Qty | Entry Price | Exit Price | Gross P&L (₹) | Costs (₹) | Net P&L (₹) | Return | Exit Reason |
| :-: | :--- | :---: | :---: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| 1 | SUNPHARMA | 2026-03-02 | 2026-03-09 | 11 | ₹1,713.71 | ₹1,804.79 | +₹1,001.90 | ₹42.93 | **+₹958.96** | +5.08% | TARGET_REACHED |
| 2 | WIPRO | 2026-04-16 | 2026-04-24 | 93 | ₹213.19 | ₹200.22 | -₹1,206.65 | ₹42.81 | **-₹1,249.46** | -6.44% | STOP_LOSS |
| 3 | ETERNAL | 2026-04-17 | 2026-05-18 | 78 | ₹253.25 | ₹235.87 | -₹1,355.74 | ₹42.50 | **-₹1,398.24** | -7.15% | STOP_LOSS |
| 4 | MARUTI | 2026-07-01 | 2026-07-14 | 1 | ₹14,165.15 | ₹13,519.67 | -₹645.48 | ₹30.81 | **-₹676.29** | -5.32% | STOP_LOSS |
| 5 | BAJAJFINSV | 2026-07-06 | 2026-07-31 | 10 | ₹1,886.99 | ₹2,030.97 | +₹1,439.82 | ₹43.43 | **+₹1,396.39** | +7.15% | TARGET_REACHED |
| 6 | WIPRO | 2026-08-04 | 2026-08-18 | 105 | ₹189.19 | ₹179.91 | -₹974.64 | ₹43.14 | **-₹1,017.78** | -5.28% | STOP_LOSS |
| 7 | DRREDDY | 2026-09-23 | 2026-10-08 | 16 | ₹1,211.21 | ₹1,170.64 | -₹649.06 | ₹42.40 | **-₹691.46** | -3.61% | STOP_LOSS |
| 8 | INFY | 2026-10-06 | 2026-10-15 | 19 | ₹1,019.02 | ₹1,097.90 | +₹1,498.78 | ₹44.58 | **+₹1,454.19** | +7.57% | TARGET_REACHED |
| **Total** | — | — | — | — | — | — | **-₹891.08** | **₹332.60** | **-₹1,223.69** | **-1.22%** | **3W / 5L (37.5%)** |

### Verified Summary Statistics:
* **Initial Capital:** ₹100,000.00
* **Final Equity:** ₹98,776.31
* **Net Return:** **-1.2237%**
* **Benchmark Return (52-Stock Equal Weight):** **+2.9225%**
* **Alpha (Excess Return):** **-4.1462%**
* **Peak Equity:** ₹100,958.96 (2026-03-09)
* **Trough Equity:** ₹96,880.81 (2026-10-08)
* **Max Drawdown (from Peak):** **4.0394%** (3.1192% from initial capital)
* **Profit Factor:** Gross: 0.8156 | Net: 0.7569
* **Expectancy:** **-₹152.96 per trade**
* **Sample Size Significance:** $N=8$, Student's $t = -0.438$ ($p = 0.67$). Insufficient statistical power to reject the null hypothesis of zero edge.

---

## 9. Regression Test Suite Execution

A dedicated unit and regression test suite was executed:

| Test Module | Command | Tests | Status | Execution Time |
| :--- | :--- | :---: | :---: | :---: |
| Historical Data Readiness Suite | `python -m pytest backend/tests/test_audit_041_historical_data_readiness.py -v` | 9 passed | **PASS** | 1.09s |
| Signal Starvation Diagnostics Suite | `python -m pytest backend/tests/test_audit_040_signal_starvation_diagnostics.py -v` | 10 passed | **PASS** | 1.01s |
| Financial Eligibility Suite | `python -m pytest backend/tests/test_audit_037_historical_financial_eligibility.py -q` | 32 passed | **PASS** | 1.02s |
| **Combined Dedicated Audit Tests** | `python -m pytest backend/tests/test_audit_041* backend/tests/test_audit_040* backend/tests/test_audit_037* -q` | **51 passed** | **100% PASS** | **1.77s** |

---

## 10. Database Integrity & Git Verification

### 10.1 Production Database SHA-256 Verification
* **Pre-Audit Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
* **Post-Audit Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
* **Status:** **100% INVARIANT AND UNTOUCHED** (`PRAGMA integrity_check` = `ok`).

### 10.2 Working-Tree Verification
* **Git Commit / Push:** **NONE PERFORMED.**
* **Tracked Changes:** 
  * `backend/data_pipeline/backtest_data_access_service.py`
  * `backend/data_pipeline/backtesting_dataset_service.py`
  * `backend/data_pipeline/financial_service.py`
  * `backend/tests/test_historical_financial_safety.py`
  * `docs/audit_artifacts/MASTER_AUDIT_TRACKER.md`
* **New Audit Artifacts & Tests Created:**
  * `backend/tests/test_audit_041_historical_data_readiness.py`
  * `docs/audit_artifacts/AUDIT-041_HISTORICAL_DATA_READINESS_AND_STRATEGY_ARCHITECTURE.md`

---

## 11. Recommended Next Steps

1. **Pre-2025 Financial Statement Ingestion (Priority 1):**  
   Ingest 4 quarters of historical financials for 2024 (`2024-Q1` through `2024-Q4`) to resolve the cold-start defect (`FND-015`) and allow the 2025 in-sample evaluation period to function as designed.
2. **Strategy Architecture Selection (Priority 2):**  
   Formally select between **Alternative A (Momentum Breakout)**, **Alternative B (Support Pullback)**, or **Alternative C (Dual-Setup Hybrid)** to resolve the 77.10% paradigm clash (`FND-016`).
3. **NSE Announcement Timestamp Integration (Priority 3):**  
   Replace the empirical 45-day statutory fallback with actual exchange publication timestamps in `quarterly_results.publication_date` (`FND-001`).
4. **Nifty Next 50 Expansion (Priority 4):**  
   Complete the remaining 48 stocks to reach the institutional 100-stock universe target (`FND-002`).

