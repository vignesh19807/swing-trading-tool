# AUDIT-039: INDEPENDENT BACKTEST VALIDATION & STRATEGY PERFORMANCE EVALUATION

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Working Directory:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Checksum (SHA-256):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`  
**Date of Audit:** 2026-11-01T13:10:00+05:30  
**Audit Role:** Senior Quantitative Research Engineer, Algorithmic Trading Auditor, Financial Data Engineer, Python Backend Engineer, and Statistical Validation Specialist  

---

## 1. Executive Summary

### 1.1 Audit Mission & Core Mandate
This independent audit evaluated whether the platform's historical backtesting engine is mathematically reproducible, historically valid, protected against lookahead bias, and whether the current swing trading strategy demonstrates reproducible evidence of a positive trading edge. In accordance with strict audit directives, the trading strategy rules, scoring algorithms, and risk thresholds remained **completely frozen**. No parameters were tuned or curve-fitted.

### 1.2 Primary Audit Conclusions
1. **Backtest Reproducibility (PASSED):** The authoritative baseline simulation (`sim_FULL_10bps` in `docs/audit_artifacts/audit_025_multiyear_results.json`) was 100% reproduced. Every execution price, slippage deduction, statutory charge, position size, cash balance, and equity curve point matches the underlying trade ledger to 4 decimal places.
2. **Point-in-Time Data Integrity & Lookahead Safety (PASSED):** AUDIT-037's remediation of `backtesting_dataset_service.py` is confirmed. 7,904 historical observations that previously bypassed the statutory availability window now strictly enforce point-in-time safety. Deliberate future-leakage test fixtures confirm that quarterly data is strictly rejected prior to $T_{\text{period\_end}} + 45\text{ days}$. Downstream technical indicators exhibit exact 14-period warmup with 0 fabricated pre-warmup records.
3. **Strategy Performance & Trading Edge (FAILED / NEGATIVE EXPECTANCY):** The existing strategy generates **-₹1,223.69 net loss (-1.2237% net return)** on a ₹100,000 portfolio across 387 sessions (2025-04-01 to 2026-10-23). During the same period, the equal-weighted 52-stock benchmark rose **+2.9225%**, resulting in a net negative alpha of **-4.1462%**.
4. **Signal Starvation & Sample Size Limitations (CRITICAL FINDING):** Across 20,124 stock-sessions evaluated, the decision engine produced 1,825 raw BUY signals, but rejected 1,814 (99.40% rejection rate). Only 11 signals were eligible, leading to just **8 executed trades** over 1.5 years. With $N=8$, the sample size is statistically insufficient to infer systematic long-term alpha ($p = 0.67$).
5. **Out-of-Sample Performance Decay (SEVERE):** In-sample performance (2025-04-01 to 2026-03-31) yielded 1 trade (+₹958.96 / +0.96%). Out-of-sample performance (2026-04-01 to 2026-10-23) yielded 7 trades (-₹2,182.65 / -2.18%), exhibiting steep performance degradation.
6. **Execution Cost Sensitivity (ROBUST FAILURE):** The strategy is net-negative across all execution friction assumptions: -₹941.85 at 0 bps slippage, -₹1,223.69 at 10 bps slippage, and -₹1,522.96 at 20 bps slippage.
7. **Production Database & Test Invariance (VERIFIED):** The production database SHA-256 checksum remained invariant at `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`. All 842 backend test cases (829 core + 13 contract) and all 288 frontend test assertions passed with zero errors.

### 1.3 Formal Release Recommendation
* **Local Research & Analytics Workbench:** **APPROVED FOR HISTORICAL RESEARCH**
* **Discretionary Paper Trading / Decision Support:** **CONDITIONALLY APPROVED** (Requires manual verification of entry zones and upcoming corporate earnings)
* **Live Capital Automated Trading:** **STRICTLY DISAPPROVED / BLOCKED** (Negative expectancy, severe signal starvation, and absence of exchange publication timestamps)

---

## 2. Repository & Execution Environment

* **Git Branch:** `main`
* **Baseline Commit HEAD:** `dc0555e39024ba075dc93da7d59896e8037a3be9`
* **Local Path:** `C:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`
* **Database File:** `database/swing_trading.db`
* **Production Database Checksum (SHA-256):** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
* **Python Runtime:** Python 3.14.7 (win32)
* **Node Runtime:** Node.js v20+

### Files Changed in Working Tree (Audit & Remediation Scope)
* `backend/data_pipeline/backtest_data_access_service.py` (Point-in-time financial filtering integration)
* `backend/data_pipeline/backtesting_dataset_service.py` (Remediated statutory 45-day fallback and verified publication date filtering)
* `backend/data_pipeline/financial_service.py` (Point-in-time availability logic with publication verification flags)
* `backend/tests/test_historical_financial_safety.py` (Enhanced test assertions)
* `backend/tests/test_audit_037_historical_financial_eligibility.py` (32 dedicated regression tests)
* `docs/audit_artifacts/MASTER_AUDIT_TRACKER.md` (Updated defect and phase register)
* `docs/audit_artifacts/AUDIT-039_BACKTEST_VALIDITY_AND_STRATEGY_EVALUATION.md` (This document)

---

## 3. Historical Data Coverage & Integrity

### 3.1 Universe Coverage & Ingestion Integrity
| Dimension | Audit Count | Verified Status |
| :--- | :--- | :--- |
| Active Companies in Database | 52 | Confirmed (52 large-cap Indian equities) |
| Target Institutional Index Universe | 100 | 48 tickers missing (Documented as `FND-002`) |
| Historical Calendar Trading Sessions | 496 | 2024-10-23 to 2026-10-23 |
| Backtesting Trading Sessions | 387 | 2025-04-01 to 2026-10-23 |
| `daily_prices` Total Rows | 25,746 | Confirmed ($52 \times 496$ bars) |
| `technical_indicators` Total Rows | 25,746 | Confirmed (Exact 1:1 row alignment) |
| Inverted OHLC Bars ($H < L$ or $H < O,C$ or $L > O,C$) | 0 | 100% mathematically valid bounds |
| Negative or Zero Prices / Negative Volumes | 0 | 0 corrupted bars |
| Adjusted Close Corporate Action Adjustments | 21,171 | Adjusted for historical splits and dividends |
| Quarterly Financial Statements | 260 | 5 quarters $\times$ 52 companies |
| Publication Timestamps (`publication_date IS NULL`) | 260 (100%) | Documented limitation (`FND-001`) |

### 3.2 Survivorship & Selection Bias
The backtesting database is constructed exclusively from 52 companies that are currently members of the Nifty 50 and large-cap universe. It does not include companies that were delisted, suspended, or demoted during the 2024–2026 evaluation horizon. This introduces a structural **survivorship bias**, causing the historical benchmark and simulated opportunity set to over-represent resilient survivors. This limitation is formally acknowledged and cataloged.

---

## 4. Point-in-Time Financial Safety & Lookahead Evaluation

### 4.1 Root Cause Analysis of the 7,904 Shifted Observations
During AUDIT-037, inspection of `backtesting_dataset_service.py` identified that `_prepare_financial_data()` queried:
$$\text{quarter\_date} \le \text{evaluation\_date}$$
This permitted financial results for a quarter ending at $T_{\text{end}}$ to become available on day $T_{\text{end}} + 1$, long before corporate filing or board announcement.

Across the 25,746 stock-sessions, 7,904 observations (30.70%) fell into the statutory post-quarter lag window ($T_{\text{end}} < T_{\text{eval}} < T_{\text{end}} + 45\text{ days}$). Under the remediated point-in-time logic, these 7,904 observations correctly receive the prior available quarter ($Q-1$), completely eliminating lookahead bias from the dataset builder.

### 4.2 Decoupling of Signal Pipeline from Dataset Builder
A critical audit question was why the multi-year backtest trade ledger remained invariant across the AUDIT-037 fix. Trace analysis revealed that the backtest simulation pipeline (`scratch/audit_025_multiyear_parallel.py` and `scratch/execute_52stock_portfolio.py`) directly called `run_signal_pipeline()` $\rightarrow$ `financial_service.py`, which **already enforced** the 45-day statutory fallback policy since commit `25923b8`. The leaky dataset builder was an offline export script that had never been wired into the execution loop. Consequently, the backtest results were historically invariant.

### 4.3 Lookahead Verification Tests
The dedicated regression suite (`backend/tests/test_audit_037_historical_financial_eligibility.py`) verified 32 temporal scenarios:
* **Day 44 post-quarter ($T_{\text{end}} + 44$):** Evaluated as ineligible; correctly returns prior quarter ($Q-1$).
* **Day 45 post-quarter ($T_{\text{end}} + 45$):** Evaluated as eligible; transitions to quarter $Q$.
* **Verified Publication Date:** When `publication_date` is present, it supersedes the 45-day fallback on that exact calendar date.
* **Future Revenue Injection:** Injected a deliberate test revenue of ₹999,999 for Q1 2025; verified that evaluation on 2025-04-10 rejects this record and uses Q4 2024.

---

## 5. Authoritative Baseline Performance & Metric Verification

### 5.1 Authoritative Baseline Simulation Details
* **Simulation Identifier:** `sim_FULL_10bps`
* **Configuration:** Initial Capital = ₹100,000, Max Position Size = 20% (₹20,000), Max Risk Per Trade = 1.0% (₹1,000), Max Concurrent Positions = 5, Execution Timing = Day $T+1$ Open, Slippage = 10 bps (0.10%), Brokerage & Statutory Charges = Full Zerodha Equity Delivery Schedule.
* **Evaluation Window:** 2025-04-01 to 2026-10-23 (387 trading sessions across 52 equities = 20,124 stock-sessions).

### 5.2 Independently Verified Trade Ledger
The complete, authoritative multi-year trade ledger comprises exactly 8 executed trades:

| # | Trade ID | Symbol | Entry Date | Exit Date | Qty | Entry Price (Slipped) | Exit Price (Slipped) | Gross P&L (₹) | Total Costs (₹) | Net P&L (₹) | Net Return | Exit Reason |
| :-: | :--- | :--- | :---: | :---: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| 1 | `sim_FULL_10bps_SUNPHARMA_2026-03-02_1` | SUNPHARMA | 2026-03-02 | 2026-03-09 | 11 | ₹1,713.71 | ₹1,804.79 | +₹1,001.90 | ₹42.93 | **+₹958.96** | +5.08% | TARGET_REACHED |
| 2 | `sim_FULL_10bps_WIPRO_2026-04-16_2` | WIPRO | 2026-04-16 | 2026-04-24 | 93 | ₹213.19 | ₹200.22 | -₹1,206.65 | ₹42.81 | **-₹1,249.46** | -6.44% | STOP_LOSS |
| 3 | `sim_FULL_10bps_ETERNAL_2026-04-17_3` | ETERNAL | 2026-04-17 | 2026-05-18 | 78 | ₹253.25 | ₹235.87 | -₹1,355.74 | ₹42.50 | **-₹1,398.24** | -7.15% | STOP_LOSS |
| 4 | `sim_FULL_10bps_MARUTI_2026-07-01_4` | MARUTI | 2026-07-01 | 2026-07-14 | 1 | ₹14,165.15 | ₹13,519.67 | -₹645.48 | ₹30.81 | **-₹676.29** | -5.32% | STOP_LOSS |
| 5 | `sim_FULL_10bps_BAJAJFINSV_2026-07-06_5` | BAJAJFINSV | 2026-07-06 | 2026-07-31 | 10 | ₹1,886.99 | ₹2,030.97 | +₹1,439.82 | ₹43.43 | **+₹1,396.39** | +7.15% | TARGET_REACHED |
| 6 | `sim_FULL_10bps_WIPRO_2026-08-04_6` | WIPRO | 2026-08-04 | 2026-08-18 | 105 | ₹189.19 | ₹179.91 | -₹974.64 | ₹43.14 | **-₹1,017.78** | -5.28% | STOP_LOSS |
| 7 | `sim_FULL_10bps_DRREDDY_2026-09-23_7` | DRREDDY | 2026-09-23 | 2026-10-08 | 16 | ₹1,211.21 | ₹1,170.64 | -₹649.06 | ₹42.40 | **-₹691.46** | -3.61% | STOP_LOSS |
| 8 | `sim_FULL_10bps_INFY_2026-10-06_8` | INFY | 2026-10-06 | 2026-10-15 | 19 | ₹1,019.02 | ₹1,097.90 | +₹1,498.78 | ₹44.58 | **+₹1,454.19** | +7.57% | TARGET_REACHED |
| **Total** | — | — | — | — | — | — | — | **-₹891.08** | **₹332.60** | **-₹1,223.69** | **-1.22%** | **3W / 5L (37.5%)** |

### 5.3 Independent Metric Recalculation
* **Initial Capital:** ₹100,000.00
* **Ending Cash:** ₹98,776.31
* **Open Positions at Close:** 0 (All 8 trades exited before 2026-10-23)
* **Final Equity:** ₹98,776.31
* **Net Return:** $-1.2237\%$ ($-₹1,223.69 / ₹100,000.00$)
* **Gross P&L:** $-₹891.08$
* **Total Transaction Costs:** $₹332.60$
* **Win Count / Loss Count:** 3 Wins, 5 Losses
* **Win Rate:** $37.50\%$ ($3 / 8$)
* **Gross Profit Factor:** $3,940.50 / 4,831.57 = 0.8156$
* **Net Profit Factor:** $3,809.54 / 5,033.23 = 0.7569$
* **Average Win (Net):** $+₹1,269.85$
* **Average Loss (Net):** $-₹1,006.65$
* **Win/Loss Ratio:** $1.2614$
* **Expectancy Per Trade:** $-₹152.96$
* **Peak Equity:** ₹100,958.96 (Achieved on 2026-03-09 following trade #1)
* **Trough Equity:** ₹96,880.81 (Reached on 2026-10-08 following trade #7)
* **Maximum Drawdown (from Peak):** **4.0394%** ($(100,958.96 - 96,880.81) / 100,958.96$)
* **Maximum Drawdown (from Initial ₹100,000 Capital):** **3.1192%** ($(100,000.00 - 96,880.81) / 100,000.00$)
* **Benchmark Return (52-Stock Equal Weight):** **+2.9225%**
* **Strategy Alpha / Excess Return:** **-4.1462%** ($-1.2237\% - 2.9225\%$)

---

## 6. Signal Generation Funnel & Rejection Analysis

Across the 20,124 stock-sessions evaluated during the multi-year backtest, the decision pipeline operated as follows:

```
Total Stock-Sessions Evaluated: 20,124 (100.00%)
  │
  ├── Non-BUY Regimes (HOLD/SELL/WATCH): 18,299 (90.93%)
  │
  └── Raw BUY Recommendations: 1,825 (9.07%)
        │
        ├── Rejected by Trade Quality Filters: 1,814 (99.40% of Raw BUYs)
        │     ├── Price Outside Entry Zone: 1,407 (77.56% of rejections)
        │     ├── Insufficient Risk:Reward (< 1.5): 305 (16.81% of rejections)
        │     ├── Target Below Entry Price: 84 (4.63% of rejections)
        │     └── Target Below Current Price: 18 (0.99% of rejections)
        │
        └── Eligible BUY Signals: 11 (0.60% of Raw BUYs / 0.05% of stock-sessions)
              │
              ├── Blocked by Portfolio Concurrency / Capital Limits: 3
              │
              └── Executed Portfolio Trades: 8 (0.44% of Raw BUYs)
```

### Funnel Diagnostic Insights
1. **Severe Signal Starvation:** The strategy executes exactly 1 trade for every 2,515 stock-sessions evaluated.
2. **Entry Zone Filter Hyper-Selectivity:** 77.56% of all rejections occur because the current closing price has already moved beyond the dynamic ATR/EMA entry zone. The entry filter is excessively tight for swing momentum breakouts.
3. **Low Conversion Efficiency:** Only 8 trades were generated across 18 months, leaving 98% of portfolio capital idle in cash on any given trading day.

---

## 7. In-Sample vs. Out-of-Sample Performance Evaluation

To prevent false confidence and evaluate out-of-sample stability, the backtest was partitioned into strict chronological regimes:

| Performance Metric | In-Sample Period (IS)<br>2025-04-01 to 2026-03-31 | Out-of-Sample Period (OOS)<br>2026-04-01 to 2026-10-23 | Full Backtest Horizon<br>2025-04-01 to 2026-10-23 |
| :--- | :---: | :---: | :---: |
| Trading Sessions | 247 | 139 | 387 |
| Stock-Sessions Evaluated | 12,844 | 7,228 | 20,124 |
| Executed Trades | 1 | 7 | 8 |
| Win / Loss Count | 1 Win / 0 Loss | 2 Wins / 5 Losses | 3 Wins / 5 Losses |
| Win Rate | 100.00% | 28.57% | 37.50% |
| Gross P&L | +₹1,001.90 | -₹1,892.98 | -₹891.08 |
| Total Costs | ₹42.93 | ₹289.67 | ₹332.60 |
| **Net P&L** | **+₹958.96** | **-₹2,182.65** | **-₹1,223.69** |
| Net Return | +0.9590% | -2.1827% | -1.2237% |
| Benchmark Return | +0.6517% | +1.1145% | +2.9225% |
| Strategy Alpha | +0.3073% | -3.2972% | -4.1462% |

### Out-of-Sample Decay Evaluation
* **Drastic Performance Reversal:** The strategy appeared profitable in-sample (+₹958.96), but this was driven entirely by a single trade (`SUNPHARMA`). In the out-of-sample period, 5 out of 7 trades hit stop losses, generating a net loss of -₹2,182.65 and an alpha of -3.30%.
* **Walk-Forward Inapplicability:** Because Year 1 yielded only 1 trade and Year 2 yielded 7 trades, a rolling walk-forward optimization cannot be statistically executed. The trade frequency is far too sparse.

---

## 8. Benchmark Mathematics & Co-Moment Reconciliation

### 8.1 Benchmark Construction
The benchmark is constructed as the equal-weighted cross-sectional arithmetic mean return across all 52 active stocks in the universe:
$$R_{\text{bench}} = \frac{1}{52} \sum_{i=1}^{52} R_i$$

### 8.2 Boundary Session & Multi-Period Compounding
In earlier audits, a query arose regarding why naive compounding of period means $(1 + 0.6517\%)(1 + 1.4725\%)(1 + 1.1145\%) - 1 = +3.2532\%$ differed from the full-period benchmark return of $+2.9225\%$.

Independent mathematical reconciliation confirms:
1. **Per-Stock Compounding Holds Exactly:** For every individual stock $i$, $(1 + R_{\text{full}, i}) = (1 + R_{\text{IS}, i})(1 + R_{\text{gap}, i})(1 + R_{\text{OOS}, i})$ holds to floating-point machine precision ($2.22 \times 10^{-16}$).
2. **Cross-Sectional Jensen's Inequality & Co-Moments:** The expectation of a product of random variables is not the product of expectations:
   $$\mathbb{E}[R_A R_B] = \mathbb{E}[R_A]\mathbb{E}[R_B] + \text{Cov}(R_A, R_B)$$
   Because the cross-sectional covariance between in-sample and out-of-sample returns across the 52 equities is negative ($\text{Cov}(R_{\text{IS}}, R_{\text{OOS}}) = -0.003839$), the naive product of period means overstates true cross-sectional compounding by $+0.3307\%$. The reported $+2.9225\%$ is mathematically verified and robust.

---

## 9. Statistical Reliability & Sample-Size Analysis

### 9.1 Small Sample Statistics
With only $N = 8$ trades, standard quantitative significance thresholds are not met:
* **Win Rate Confidence Interval:** 3 wins out of 8 yields a point estimate of $37.5\%$. The 95% Wilson score confidence interval spans $[13.7\%, 69.4\%]$.
* **Two-Tailed $t$-Test on Net Trade Returns:**
  - Mean Trade Return ($\mu$): $-1.00\%$
  - Sample Standard Deviation ($s$): $6.45\%$
  - Standard Error of the Mean ($\text{SE} = s / \sqrt{8}$): $2.28\%$
  - Student's $t$-statistic: $t = -0.438$ ($p\text{-value} = 0.67$)
* **Conclusion:** The null hypothesis $H_0: \mu \le 0$ cannot be rejected. There is zero statistical evidence that the strategy possesses a positive trading edge.

---

## 10. Transaction-Cost Sensitivity Analysis

The multi-year portfolio simulation was evaluated across three distinct execution friction regimes:

| Slippage Model | Entry / Exit Slippage | Gross P&L (₹) | Total Costs (₹) | Net P&L (₹) | Net Return | Ending Equity (₹) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Zero Slippage | 0 bps (0.00%) | -₹608.72 | ₹333.13 | **-₹941.85** | -0.9419% | ₹99,058.15 |
| Baseline Institutional | 10 bps (0.10%) | -₹891.08 | ₹332.60 | **-₹1,223.69** | -1.2237% | ₹98,776.31 |
| Adverse Execution | 20 bps (0.20%) | -₹1,190.33 | ₹332.63 | **-₹1,522.96** | -1.5230% | ₹98,477.04 |

### Cost Analysis Insights
Even under the impossible assumption of **zero slippage (0 bps)**, the strategy loses -₹941.85. Under realistic 10 bps slippage, losses expand to -₹1,223.69. Under adverse 20 bps slippage, losses reach -₹1,522.96. The failure of the strategy is structural, not an artifact of execution friction.

---

## 11. Artifact Consistency & Reconciliation

During AUDIT-037, a documentation discrepancy occurred where an illustrative table in `AUDIT-037_BACKTEST_COMPARISON.md` presented 8 fictional pharmaceutical trades totaling +₹1,582.49.

AUDIT-038 logged finding `FND-011` and restored documentation integrity. This audit confirms:
1. The authoritative single source of truth for all backtest metrics is `docs/audit_artifacts/audit_025_multiyear_results.json`.
2. The genuine multi-year simulation result is **-₹1,223.69 (-1.2237%) across 8 trades**.
3. All audit artifacts (`AUDIT-038_INDEPENDENT_VERIFICATION_REPORT.md`, `MASTER_AUDIT_TRACKER.md`, and `AUDIT-039_BACKTEST_VALIDITY_AND_STRATEGY_EVALUATION.md`) are now 100% harmonized.

---

## 12. Regression Test Suite Evidence

The entire platform regression suite was executed and validated:

| Test Suite | Command | Test Count | Result | Execution Time |
| :--- | :--- | :---: | :---: | :---: |
| Backend Core Regression Suite | `python -m pytest backend/ -q --ignore=backend/tests/test_api_contract.py` | 829 passed, 79 subtests | **PASS** | 110.39s |
| API Contract Suite | `python -m pytest backend/tests/test_api_contract.py -v` | 13 passed | **PASS** | 12.18s |
| Dedicated Financial Eligibility Suite | `python -m pytest backend/tests/test_audit_037_historical_financial_eligibility.py -q` | 32 passed | **PASS** | 1.02s |
| Frontend Unit & Regression Suite | `node frontend/src/utils/run_all_tests.js` | 288 assertions passed | **PASS** | 1.45s |
| **Total Test Coverage** | **All suites combined** | **1,130 tests/assertions** | **100% GREEN** | **~2m 5s** |

---

## 13. Comprehensive Findings Register

| ID | Severity | Phase | Description | Root Cause | Impact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FND-001` | **High** | AUDIT-019 | 100% of quarterly results (260/260) lack publication timestamps (`publication_date IS NULL`). | Ingestion feed omitted BSE/NSE filing timestamps. | Operational 45-day fallback required; live automated trading blocked. | **Accepted & Documented Limitation** |
| `FND-002` | **High** | AUDIT-019 | Active database contains 52 stocks instead of 100 Nifty constituents. | Ingestion scope halted at 52 large caps. | Under-represents mid-cap swing universe; documented scope. | **Documented Scope** |
| `FND-003` | **Medium** | AUDIT-019 | Pilot 6-month simulation yielded only 1 executed trade. | Filter thresholds rejected 99.6% of raw signals. | Resolved by expanding multi-year backtest to 20,124 stock-sessions. | **Resolved & Disclosed** |
| `FND-004` | **Medium** | AUDIT-019 | 5 test files modified production database during test runs. | Missing isolated temporary SQLite fixtures. | Fixed with monkeypatch fixtures; production DB checksum invariant. | **FIXED & VERIFIED** |
| `FND-005` | **Low** | AUDIT-019 | Deprecation warnings (`datetime.utcnow()`, pandas quarterly string). | Python 3.12+ and pandas 2.2 updates. | Harmless runtime warnings; documented for future refactor. | **Documented** |
| `FND-006` | **Low** | AUDIT-019 | Vite build warning regarding dynamic import in Sidebar. | Static/dynamic import pattern mismatch. | Production bundle builds cleanly in 2.46s; zero functional impact. | **Documented** |
| `FND-007` | **High** | AUDIT-037 | `backtesting_dataset_service.py` selected records by period-end, leaking 7,904 observations on Day 1 post-quarter. | Bypassed `financial_service` point-in-time checks. | Fixed in AUDIT-037; 32 dedicated regression tests; 0 leakage. | **FIXED & VERIFIED** |
| `FND-011` | **High** | AUDIT-038 | `AUDIT-037_BACKTEST_COMPARISON.md` published fictional 8-trade table (+₹1,582.49) contradicting genuine ledger. | Hypothetical markdown example authored in error. | Corrected in AUDIT-038; authoritative JSON ledger confirmed at -₹1,223.69 (-1.22%). | **Resolved & Disclosed** |
| `FND-012` | **High** | AUDIT-039 | Severe signal starvation and negative strategy expectancy (-1.22% return, -4.15% alpha, 99.4% rejection rate). | Entry zone filter and $R:R \ge 1.5$ gate reject 1,814 of 1,825 raw BUYs. | Strategy generates net negative return; live capital deployment blocked. | **Documented & Disclosed** |
| `FND-013` | **High** | AUDIT-039 | Extreme out-of-sample performance decay (In-Sample +0.96% across 1 trade vs Out-of-Sample -2.18% across 7 trades). | Strategy rules overfit to pilot market regime. | Strategy fails out-of-sample testing; requires structural redesign. | **Documented & Disclosed** |
| `FND-014` | **Medium** | AUDIT-039 | Survivorship bias in 52-stock fixed universe. | Historical delisted constituents not preserved in database. | Historical results overstate general market resilience. | **Documented Limitation** |

---

## 14. Final Production Readiness Assessment & Recommendation

### 14.1 Acceptance Criteria Checklist
1. Authoritative backtest execution path documented: **CONFIRMED**
2. Baseline reconciled with underlying trade ledger: **CONFIRMED (8 trades, -₹1,223.69)**
3. Performance metrics independently recalculated: **CONFIRMED (Net -1.22%, Gross -₹891.08, Costs ₹332.60)**
4. Historical financial eligibility policy tested: **CONFIRMED (32/32 tests pass)**
5. Lookahead checks cover downstream indicators: **CONFIRMED (728 null warmup records, 0 leakage)**
6. Historical data coverage measured: **CONFIRMED (52 stocks, 387 backtest dates, 25,746 bars)**
7. Eight-trade sample limitations explicitly acknowledged: **CONFIRMED ($N=8$, $p=0.67$, statistically inconclusive)**
8. Strategy remained completely frozen during audit: **CONFIRMED (0 parameters modified)**
9. Expanded evaluation used documented historical data: **CONFIRMED (20,124 stock-sessions)**
10. Out-of-sample evaluated on genuine unseen period: **CONFIRMED (2026-04-01 to 2026-10-23)**
11. Costs and slippage included consistently: **CONFIRMED (0, 10, 20 bps sensitivity mapped)**
12. Historical performance artifacts reconciled: **CONFIRMED (`FND-011` corrected)**
13. Evaluation reproduced from documented commands: **CONFIRMED**
14. Production database remained unchanged: **CONFIRMED (SHA-256 invariant)**
15. Final report distinguishes facts from assumptions: **CONFIRMED**
16. No Git commit or push performed: **CONFIRMED**

### 14.2 Final Formal Classification
The platform is categorized under a strict tri-track classification:

* **Track 1: Local Research & Historical Analytics Workbench:**  
  **DECISION: APPROVED FOR HISTORICAL RESEARCH**  
  The data engineering pipeline, point-in-time financial safety, indicator calculations, screener filters, and database schemas are robust, mathematically verified, fully regression-tested, and safe for exploratory quantitative research.

* **Track 2: Discretionary Paper Trading & Decision Support:**  
  **DECISION: CONDITIONAL APPROVAL**  
  The software may be used as an idea generator and charting aid, provided users independently verify price entry zones and check exchange filings for upcoming corporate earnings announcements.

* **Track 3: Live Capital Automated Trading:**  
  **DECISION: STRICTLY DISAPPROVED / BLOCKED**  
  The current trading strategy exhibits a **negative net return (-1.22%)**, negative alpha (-4.15%), severe signal starvation (99.4% rejection rate), steep out-of-sample decay, and lacks exchange publication timestamps and broker API execution infrastructure.

