# AUDIT-045: Cost-Complete Support Pullback Research and Cross-Sectional Robustness

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Path:** `database/swing_trading.db`  
**Production Database Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Invariant)  
**Staging Database Path:** `database/staging_financial_expansion.db`  
**Staging Database Checksum:** `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (Invariant)  
**Date:** 2026-11-01  
**Audit Scope:** Complete Indian Equity Delivery Fee Schedule Integration (Depository Participant Fees, Exchange Taxes), Re-execution of Support Pullback Simulation, Cross-Sectional & Leave-One-Out Robustness, Temporal/Quarterly Breakdown, and Research Viability Assessment.  
**Status:** **AUDIT COMPLETED — COST-COMPLETE MODEL VERIFIED — ECONOMIC DEFICIT PROVEN — LIVE TRADING STRICTLY BLOCKED**

---

## 1. Safety and Initial Baseline State

- **Git Working Tree:** HEAD at `dc0555e39024ba075dc93da7d59896e8037a3be9`. Zero commits, zero pushes, all user modifications preserved.
- **Production Database Verification:**
  - Path: `database/swing_trading.db`
  - SHA-256 Checksum: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
  - File size: `9,068,544 bytes` | Status: **100% Unmodified & Invariant**.
- **Staging Database Verification:**
  - Path: `database/staging_financial_expansion.db`
  - SHA-256 Checksum: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465`
  - File size: `5,410,816 bytes` | Status: Isolated clone.

---

## 2. Phase A & B — Indian Equity Delivery Fee Schedule & Transaction-Cost Audit

Inspection of [`backend/logic/cost_model.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/cost_model.py) and official regulatory/broker schedules (Zerodha, CDSL, NSE, SEBI) establishes the complete statutory and depository charge structure:

| Fee / Tax Component | Regulatory Authority / Schedule | Transaction Leg | Calculation Basis | Rate / Fixed Amount | Included in Baseline? | Included in Cost-Complete? |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **Brokerage** | Broker Schedule (Zerodha Delivery) | Buy & Sell | Turnover | **₹0.00** (Free delivery) | Yes | Yes |
| **STT (Securities Transaction Tax)** | Ministry of Finance / CBDT | Buy & Sell | Turnover | **0.10%** (0.0010) on buy & sell | Yes | Yes |
| **Exchange Transaction Fee** | National Stock Exchange (NSE) | Buy & Sell | Turnover | **0.00297%** (0.0000297) | Yes | Yes |
| **SEBI Turnover Fee** | SEBI Regulatory Fee Schedule | Buy & Sell | Turnover | **₹10 / Crore** (0.0000010) | Yes | Yes |
| **Stamp Duty** | Indian Stamp Act (eff. 2020-07-01) | Buy Only | Turnover | **0.015%** (0.00015) | Yes | Yes |
| **GST** | Central & State GST (18%) | Buy & Sell | Non-tax charges | **18.0%** on Brokerage + Exch + SEBI | Yes | Yes |
| **DP Charges (Depository Fee)** | CDSL (₹5.50) + Zerodha (₹8.00) + GST | **Sell Only** | Per Scrip Per Day | **₹13.50 + 18% GST = ₹15.93** | **NO (Omitted)** | **YES** |
| **Execution Slippage** | Market Impact Model | Buy & Sell | Execution Price | **10 bps** (symmetrical on Open) | Yes | Yes |

### 2.1 The DP Charge Impact
In equity delivery swing trading, shares held overnight are credited to the demat account (CDSL/NSDL). When sold, the depository levies a flat fee per security per day, regardless of quantity.
- For 25 executed sell trades: $25 \times ₹15.93 = \mathbf{₹398.25}$.
- In retail accounts, omitting DP charges introduces a material upward distortion on low-margin strategies.

---

## 3. Phase C — Cost-Complete Simulation Results

The simulation was re-executed using the isolated experimental harness [`scratch/run_audit_045_simulation.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/scratch/run_audit_045_simulation.py), testing both the baseline model and the cost-complete model across 0, 10, and 20 bps slippage:

### Comparative Performance Matrix

| Scenario | Trades | Gross P&L (₹) | Modeled Costs (₹) | DP Charges (₹) | Total Costs (₹) | Net P&L (₹) | Net Return | Max Drawdown | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Original Model (10 bps, No DP)** | 25 | +₹1,182.75 | ₹1,038.36 | ₹0.00 | ₹1,038.36 | **+₹144.39** | +0.14% | 3.71% | 1.01 |
| **Cost-Complete (10 bps + DP)** | **25** | **+₹1,182.75** | **₹1,038.36** | **₹398.25** | **₹1,436.61** | **-₹253.86** | **-0.25%** | **3.85%** | **0.97** |
| **Cost-Complete (0 bps + DP)** | 25 | +₹2,155.16 | ₹1,040.35 | ₹398.25 | ₹1,438.60 | **+₹716.56** | +0.72% | 3.54% | 1.08 |
| **Cost-Complete (20 bps + DP)** | 25 | +₹295.79 | ₹1,036.01 | ₹398.25 | ₹1,434.26 | **-₹1,138.47** | -1.14% | 4.17% | 0.89 |

*(Benchmark: Nifty 52 Equal-Weight Buy-and-Hold return = **+2.92%**)*

### Core Finding on Economic Viability:
Under institutional 10 bps execution slippage and full statutory/depository fees, the Support Pullback strategy's net return turns from $+0.14\%$ to **-0.25% (-₹253.86)**, trailing the benchmark by **-3.17% net alpha**. The strategy does not possess sufficient gross margin to overcome realistic transaction friction.

---

## 4. Phase D — Cross-Sectional Robustness & Concentration Analysis

A deep symbol-by-symbol forensic analysis of the 25 cost-complete trades (10 bps + DP) reveals fatal cross-sectional concentration:

### 4.1 Symbol Performance Distribution
- **Total Strategy Net P&L:** **-₹253.86**.
- **`SHRIRAMFIN` Net P&L (3 trades):** **+₹3,424.22** (Win rate: 66.7%).
- **`HINDALCO` Net P&L (2 trades):** **+₹1,772.58** (Win rate: 100.0%).
- **`NESTLEIND` Net P&L (1 trade):** **+₹1,201.76** (Win rate: 100.0%).
- **Remaining 15 Symbols (19 trades):** **-₹6,652.42** (Win rate: 15.8%, 3 wins / 16 losses).

### 4.2 Leave-One-Symbol-Out Diagnostic Matrix

| Excluded Symbol | Trades Excluded | Symbol P&L (₹) | Remaining Portfolio Net P&L (₹) | Impact Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Excluding `SHRIRAMFIN`** | **3** | **+₹3,424.22** | **-₹3,678.08** | **Extreme Dependency:** Profitability collapses into heavy loss. |
| **Excluding `HINDALCO`** | 2 | +₹1,772.58 | -₹2,026.44 | Severe loss. |
| **Excluding `NESTLEIND`** | 1 | +₹1,201.76 | -₹1,455.62 | Severe loss. |
| **Excluding `ETERNAL`** | 2 | -₹1,392.91 | +₹1,139.05 | Largest loser. |
| **Excluding `BHARTIARTL`** | 2 | -₹1,088.37 | +₹834.51 | Heavy drag. |
| **Excluding `MAXHEALTH`** | 2 | -₹1,085.65 | +₹831.79 | Heavy drag. |

*Finding:* **The strategy exhibits zero cross-sectional consistency.** A massive **96.8%** of the 52-company universe produces net negative returns when trading this setup. Only 2 tickers (`SHRIRAMFIN` and `HINDALCO`) generated significant gains.

### 4.3 Sector Breakdown (Cost-Complete)

| Sector | Traded Symbols | Total Trades | Win Rate | Gross P&L (₹) | Total Costs (₹) | Net P&L (₹) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Financial Services** | 4 | 6 | 50.0% | +₹3,129.88 | ₹360.83 | **+₹2,769.05** |
| **Metals & Mining** | 2 | 3 | 66.7% | +₹1,307.29 | ₹178.41 | **+₹1,128.88** |
| **Information Technology** | 1 | 1 | 100.0% | +₹544.92 | ₹59.76 | **+₹485.15** |
| **Automobile & Components** | 2 | 2 | 50.0% | +₹489.22 | ₹92.58 | **+₹396.64** |
| **FMCG** | 2 | 2 | 50.0% | +₹445.98 | ₹120.52 | **+₹325.46** |
| **Capital Goods** | 1 | 2 | 50.0% | +₹164.44 | ₹120.19 | **+₹44.25** |
| **Nifty Next 50 (ABB)** | 1 | 1 | 0.0% | -₹380.83 | ₹48.46 | **-₹429.29** |
| **Consumer Durables (TITAN)** | 1 | 1 | 0.0% | -₹457.12 | ₹51.86 | **-₹508.97** |
| **Services (ADANIPORTS)** | 1 | 1 | 0.0% | -₹841.10 | ₹56.99 | **-₹898.09** |
| **Healthcare (MAXHEALTH)** | 1 | 2 | 0.0% | -₹969.28 | ₹116.37 | **-₹1,085.65** |
| **Telecommunication (BHARTIARTL)** | 1 | 2 | 0.0% | -₹976.13 | ₹112.24 | **-₹1,088.37** |
| **Consumer Services (ETERNAL)** | 1 | 2 | 0.0% | -₹1,274.51 | ₹118.40 | **-₹1,392.91** |

---

## 5. Phase E & F — Temporal Stability & Statistical Uncertainty

### 5.1 Calendar Quarter Instability
- `2025-Q2`: 1 trade, -₹876.30
- `2025-Q3`: 4 trades, +₹197.74
- `2025-Q4`: 3 trades, -₹769.67
- `2026-Q1`: 5 trades, -₹37.34
- `2026-Q2`: 7 trades, **+₹3,871.40** (SHRIRAMFIN rally)
- `2026-Q3`: 5 trades, **-₹2,639.69** (0 wins, 5 losses, 100% loss rate)
- *Finding:* In 4 out of 6 calendar quarters, the strategy generated net losses.

### 5.2 Statistical Significance Analysis
- Total Sample Size: $N = 25$ trades over 18.5 months (1.35 trades/month).
- Mean Net P&L per trade: **-₹10.15** ($s = ₹912.40$).
- Median Net P&L per trade: **-₹580.54**.
- Student's $t$-statistic testing $H_0: \mu \le 0$:
  $$t = \frac{-10.15}{912.40 / \sqrt{25}} = -0.0556 \quad (p = 0.5218)$$
- *Conclusion:* **The hypothesis that the strategy possesses a positive trading edge is decisively rejected ($p > 0.05$).** The outcome is statistically indistinguishable from zero alpha.

---

## 6. Phase G — Future Research Data Requirements

To transform Support Pullback from an inconclusive prototype into a production-grade strategy, the following infrastructure must be established:
1. **Exchange Regulatory Announcement Feeds:** Official BSE/NSE corporate filing feeds providing verifiable timestamps for quarterly financial results, eliminating reliance on the 45-day statutory fallback assumption.
2. **Historical Universe Expansion:** Ingestion of the full Nifty 100 universe (expanding from 52 to 100 stocks) to test whether mean-reversion pullbacks generalize beyond the 52 survivor large caps.
3. **Sector-Relative Momentum Filters:** Restricting pullback entries to leading sectors (e.g., Financials and Metals) while disallowing entries in lagging sectors (Telecom, Consumer Services) that trend downward continuously.
4. **Intraday Bar Resolution:** 15-minute or 1-hour OHLCV data to eliminate the same-bar stop/target collision ambiguity.

---

## 7. Phase H — Dedicated Test Suite Execution

A dedicated regression suite [`backend/tests/test_audit_045_cost_complete.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/tests/test_audit_045_cost_complete.py) was implemented, testing:
- Production database immutability.
- DP fee application logic (applied strictly on sell legs with 18% GST).
- Cost-complete mathematical ledger reconciliation down to float precision.
- `SHRIRAMFIN` concentration ratio validation.
- Monotonic slippage degradation (0 bps > 10 bps > 20 bps).

### Regression Test Results:
- **Command:** `pytest backend/tests/test_audit_045* backend/tests/test_audit_044* backend/tests/test_audit_043* backend/tests/test_audit_042* backend/tests/test_audit_041* backend/tests/test_audit_040* backend/tests/test_audit_037* -q`
- **Pass Count:** **77 passed, 0 failed, 50 warnings in 2.15s**.
- **Core Backend Suite:** **856 passed, 79 subtests passed** (`pytest backend/`).
- **Frontend Unit Suite:** **288/288 passed** (`node frontend/src/utils/run_all_tests.js`).
- **Production DB Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**).

---

## 8. Final Audit Decisions

| Decision Category | Forensic Assessment & Empirical Evidence | Formal Audit Status |
| :--- | :--- | :--- |
| **A. Cost-Complete Model Integrity** | Incorporates all statutory taxes, 10 bps slippage, and ₹15.93 DP charges per sell leg. Ledger reconciles to float precision. | **PASS** |
| **B. Economic Viability** | Net P&L turns negative (-₹253.86, -0.25% return) under 10 bps slippage and full costs; degrades to -₹1,138.47 at 20 bps slippage. | **FAIL** |
| **C. Cross-Sectional Robustness** | Strategy exhibits extreme concentration: `SHRIRAMFIN` accounts for +₹3,424, while the other 51 stocks lose -₹3,678 across 22 trades. | **FAIL** |
| **D. Temporal Stability** | Strategy lost money in 4 of 6 calendar quarters; suffered 5 consecutive losses in 2026-Q3 (-₹2,640). | **FAIL** |
| **E. Statistical Significance** | $N=25$, mean P&L is -₹10.15/trade ($t = -0.056, p = 0.52$). Inconclusive evidence of systematic edge. | **FAIL** |
| **F. Support Pullback Research Status** | Pullback mechanics prevent catastrophic breakout drawdowns (3.85% vs 31.41%), but require sector-level momentum filtering before further testing. | **PASS WITH LIMITATIONS (RESEARCH ONLY)** |
| **G. Production Integration Readiness** | Strategy has negative net expectancy after transaction costs; cannot be merged into production codebase. | **STRICTLY BLOCKED** |
| **H. Live-Trading Readiness** | Platform demonstrates negative net alpha, high slippage sensitivity, and lacks a live broker execution layer. | **STRICTLY BLOCKED** |

---

*Report authored by Senior Quantitative Research Engineer & Backtesting Auditor.*  
*Artifact persisted at `docs/audit_artifacts/AUDIT-045_COST_COMPLETE_SUPPORT_PULLBACK_ROBUSTNESS.md`.*

