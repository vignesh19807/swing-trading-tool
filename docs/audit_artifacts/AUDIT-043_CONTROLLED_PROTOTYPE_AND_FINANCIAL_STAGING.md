# AUDIT-043: Controlled Dual-Setup Prototype and Financial Data Staging

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Path:** `database/swing_trading.db`  
**Production Database Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Invariant)  
**Staging Database Path:** `database/staging_financial_expansion.db` (Initialized & Isolated)  
**Date:** 2026-11-01  
**Audit Scope:** Financial Data Provenance Investigation, Staging Database Preparation, Isolated Strategy Prototyping (Momentum Breakout & Support Pullback), Deterministic Hybrid Arbitration, and 4-Way Comparative Backtest Evaluation.  
**Status:** **PROTOTYPE EXPERIMENTS COMPLETED — PRODUCTION STRATEGY & DATABASE 100% UNTOUCHED — LIVE TRADING NOT APPROVED**

---

## 1. Baseline and Repository State

Prior to initiating any experimental prototypes or staging preparations, the repository baseline was verified:

- **Git Branch:** `main`, HEAD commit: `dc0555e39024ba075dc93da7d59896e8037a3be9`
- **Working Tree State:** Tracked modifications preserved without commit (`backtest_data_access_service.py`, `backtesting_dataset_service.py`, `financial_service.py`, `test_historical_financial_safety.py`, `MASTER_AUDIT_TRACKER.md`).
- **Production Database Verification:**
  - File path: `database/swing_trading.db`
  - File size: `9,068,544 bytes`
  - SHA-256 Checksum: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
  - `PRAGMA integrity_check` = `ok`
- **Starting Quantitative Funnel (AUDIT-040 to AUDIT-042 Baseline):**
  - Evaluated Stock-Sessions: 20,124 (52 stocks across 387 sessions).
  - Dormant Cold-Start Sessions: 11,284 (2025-04-01 to 2026-02-13; `len(subscores) < 2`).
  - Active Sessions: 8,840.
  - Raw BUY Candidates: 1,825.
  - Signal-Quality Rejections: 1,814 (99.40% rejection rate).
  - Eligible Signals: 11.
  - Executed Trades: 8 (3 wins, 5 losses, 37.5% win rate, -₹1,223.69 net P&L, -1.22% return, -4.15% alpha).

---

## 2. Phase A — Historical Financial Source Investigation & Provenance

A rigorous source audit was conducted for the proposed pre-2025 quarterly records (`2024-Q1` through `2024-Q4`) across the 52-stock audit universe:

### 2.1 Provider Investigation
1. **Public APIs (`yfinance`):**
   - Querying `yfinance` endpoints (e.g. `ticker.quarterly_income_stmt`, `ticker.quarterly_financials`) for NSE equities returns only the rolling 4 to 5 most recent quarters (e.g., `2025-Q4` to `2026-Q3`).
   - Historical quarters for `2024` are dropped from yfinance rolling quarterly balance sheet and income statement series for non-US equities.
   - Exact corporate regulatory announcement timestamps (`publication_date`) are **not available** via yfinance for Indian equities (`ticker.news` returns 0 rows, `sec_filings` is empty).
2. **Current Database Baseline Inventory (`quarterly_results`):**
   - The production database contains 260 rows across 5 quarters (`2025-Q1` to `2026-Q1`).
   - Forensic analysis of these rows shows that 258 out of 260 rows contain standardized placeholder baseline values (`revenue = 10000.0`, `net_profit = 1500.0`, `eps = 15.0`), with only 2 rows in INFY containing real data.
   - Crucially, **100.0% of records (260/260) have `publication_date IS NULL`**.
3. **Regulatory Provenance Classification:**
   - Classification: **`SOURCE_UNVERIFIED` / `PUBLICATION_DATE_UNKNOWN`**.
   - Neither yfinance nor existing local offline files provide verified, audited BSE/NSE corporate announcement timestamps for 2024 quarters across all 52 equities.
   - Under strict audit instructions (*"Do not manufacture records or timestamps. If a reliable source cannot be identified, report the gap rather than fabricating data"*), **0 fabricated records were created**.

---

## 3. Phase B — Isolated Staging Database Preparation

The proposed staging database [`database/staging_financial_expansion.db`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/database/staging_financial_expansion.db) was initialized cleanly:

- **Isolation Guarantee:** Staging is completely decoupled from `database/swing_trading.db`.
- **Schema Parity:** Initialized directly from the production SQLite DDL, retaining tables `companies`, `sectors`, `industries`, `daily_prices`, `technical_indicators`, and `quarterly_results`.
- **Integrity Validation:**
  - Foreign key constraints: Validated.
  - Primary keys & unique constraints (`company_id, quarter`): Active and verified.
  - Initial `quarterly_results` row count: 260 (exact clone of baseline).
- **Staging Status:** Verified ready to receive verified historical records once an institutional exchange feed (BSE/NSE announcement API) is connected.

---

## 4. Phase C — Point-in-Time Financial Eligibility Analysis

The evaluation engine's point-in-time logic distinguishes:
1. `reporting_period_end_date` (e.g., 2024-03-31 for Q1)
2. `publication_date` (verified official filing timestamp)
3. `estimated_availability_date` (statutory fallback: `period_end_date + 45 days` per SEBI LODR Regulation 33)
4. `evaluation_date` (trading session timestamp)

### 4.1 In-Sample Timeline Sensitivity
- If 2024-Q4 ended 2024-12-31, its statutory eligibility date was **2025-02-14**.
- By the backtest start on **2025-04-01**, all four 2024 quarters (`2024-Q1` through `2024-Q4`) would be over 45 days old.
- However, because actual BSE/NSE filing timestamps are not yet ingested, any historical evaluation across 2025 relies on the **statutory 45-day lag assumption**, which must be explicitly disclosed as an operational model rather than verified empirical timestamps.

---

## 5. Phase D & E — Isolated Experimental Prototypes

To test whether resolving the paradigm clash (`FND-016`) yields viable trading models, isolated experimental classes were developed in [`backend/experimental/dual_setups.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/experimental/dual_setups.py):

### 5.1 Momentum Breakout Prototype (`MomentumBreakoutSetup`)
- **Lookback:** Trailing 20 trading sessions.
- **Trend Stack:** $\text{Close} > \text{EMA}_{20} > \text{EMA}_{50}$.
- **Momentum:** $55.0 \le \text{RSI}_{14} \le 75.0$, $\text{MACD Histogram} > 0$.
- **Breakout Level:** 20-day trailing highest close.
- **Volume Expansion:** $\text{Volume} \ge 1.20 \times \text{SMA}_{20}(\text{Volume})$.
- **Entry Zone:** $[\text{Breakout Level}, \text{Breakout Level} + 0.50 \times \text{ATR}_{14}]$.
- **Stop Loss:** $\min(\text{Low}_T, \text{Breakout Level}) - 0.75 \times \text{ATR}_{14}$ (risk capped at $1.50 \times \text{ATR}_{14}$).
- **Target:** Volatility expansion $\text{Close} + \max(2.0 \times \text{ATR}_{14}, 2.0 \times \text{Risk})$, guaranteeing $R:R \ge 1.50$.

### 5.2 Support Pullback Prototype (`SupportPullbackSetup`)
- **Macro Trend:** $\text{Close} > \text{EMA}_{200}$ and $\text{EMA}_{50} > \text{EMA}_{200}$.
- **Oversold/Pullback:** $30.0 \le \text{RSI}_{14} \le 48.0$.
- **Support Proximity:** Nearest pivot support below price; $\text{Close} \in [\text{Support}, \text{Support} + 0.50 \times \text{ATR}_{14}]$.
- **Reversal Confirmation:** Bullish candle close ($\text{Close} > \text{Open}$ or lower shadow $> 50\%$ of candle range).
- **Stop Loss:** $\text{Support Zone Low} - 1.00 \times \text{ATR}_{14}$.
- **Target:** Nearest overhead resistance zone low; gate: $R:R \ge 1.50$.

### 5.3 Deterministic Hybrid Arbitrator (`DualSetupArbitrator`)
- Priority Rule:
  1. When both setups qualify, select the setup with higher $R:R$ if delta $> 0.25$.
  2. If $R:R$ is within $0.25$, default to Breakout for momentum continuation.
  3. Emit structured arbitration reason.

---

## 6. Phase F & G — Four-Way Comparative Backtest Evaluation

The four configurations were backtested across the entire 20,124 stock-session history (387 sessions from 2025-04-01 to 2026-10-23 across all 52 stocks) under strictly identical execution conditions:
- **Capital:** ₹100,000 initial cash.
- **Position Sizing:** Whole-share integer sizing, max 20% allocation per position ($\le ₹20,000$).
- **Portfolio Constraints:** Max 5 concurrent positions, 1 position per symbol (`ALREADY_IN_POSITION`).
- **Execution Timing:** Next-day Open ($T+1$) with Day $T+1$ same-bar stop/target evaluation.
- **Cost Model:** Full Zerodha statutory charges + **10 bps slippage** (applied symmetrically on entry and exit).

### 6.1 Four-Way Comparative Scorecard

| Configuration | Signals Generated | Executed Trades | Win Rate | Profit Factor | Net P&L (₹) | Net Return | Max Drawdown | Total Costs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config A: Baseline (Monolithic Control)** | **11** | **8** | **37.5%** | **0.76** | **-₹1,223.69** | **-1.22%** | **4.04%** | **₹332.60** |
| **Config B: Standalone Momentum Breakout** | **220** | **132** | **25.0%** | **0.54** | **-₹27,196.97** | **-27.20%** | **31.41%** | **₹5,146.06** |
| **Config C: Standalone Support Pullback** | **42** | **25** | **36.0%** | **1.01** | **+₹144.39** | **+0.14%** | **3.71%** | **₹1,038.36** |
| **Config D: Dual-Setup Hybrid (Arbitrated)** | **262** | **150** | **26.7%** | **0.64** | **-₹22,603.30** | **-22.60%** | **28.96%** | **₹5,720.61** |

*(Benchmark: Nifty 52 Equal-Weight Buy-and-Hold return = **+2.92%**)*

### 6.2 Signal Rejection Attribution
- **Momentum Breakout Top Rejections:**
  - `TREND_NOT_ALIGNED` ($\text{Close} \le \text{EMA}_{20}$ or $\text{EMA}_{20} \le \text{EMA}_{50}$): 12,692 sessions (63.1%)
  - `PRICE_BELOW_BREAKOUT_LEVEL`: 2,421 sessions (12.0%)
  - `RSI_OUT_OF_MOMENTUM_RANGE` ($\text{RSI} < 55$ or $> 75$): 1,689 sessions (8.4%)
  - `NON_POSITIVE_MACD_HISTOGRAM`: 1,687 sessions (8.4%)
  - `INSUFFICIENT_VOLUME_EXPANSION` ($V < 1.20 \times \text{SMA}_{20}(V)$): 1,038 sessions (5.2%)
- **Support Pullback Top Rejections:**
  - `MACRO_TREND_NOT_BULLISH` ($\text{Close} \le \text{EMA}_{200}$ or $\text{EMA}_{50} \le \text{EMA}_{200}$): 10,443 sessions (51.9%)
  - `RSI_NOT_IN_PULLBACK_RANGE` ($\text{RSI} < 30$ or $> 48$): 7,229 sessions (35.9%)
  - `PRICE_OUTSIDE_ENTRY_ZONE`: 1,380 sessions (6.9%)
  - `NO_BULLISH_REVERSAL_CONFIRMATION`: 594 sessions (3.0%)
  - `INSUFFICIENT_RISK_REWARD_RATIO`: 424 sessions (2.1%)

---

## 7. Phase H — Statistical Findings & Temporal Validation

### 7.1 In-Sample (IS) vs. Out-of-Sample (OOS) Performance Breakdown
- **In-Sample Period:** 2025-04-01 to 2026-03-31 (247 sessions)
- **Out-of-Sample Period:** 2026-04-01 to 2026-10-23 (140 sessions)

| Configuration | In-Sample Trades | In-Sample Net P&L | Out-of-Sample Trades | Out-of-Sample Net P&L |
| :--- | :---: | :---: | :---: | :---: |
| **Config A (Baseline)** | 1 | +₹958.96 | 7 | -₹2,182.65 |
| **Config B (Breakout)** | 97 | -₹30,341.56 | 35 | +₹3,144.59 |
| **Config C (Pullback)** | 13 | -₹1,278.52 | 12 | +₹1,422.91 |
| **Config D (Hybrid)** | 107 | -₹28,809.65 | 43 | +₹6,206.35 |

### 7.2 Critical Quantitative Insights
1. **Breakout Failure Rate in Choppy Regimes:**
   - Standalone Momentum Breakout increased trade frequency drastically ($N=132$ vs $N=8$).
   - However, it suffered a **75.0% loss rate** (99 losses out of 132 trades) and severe drawdown (-27.20% net return, 31.41% max drawdown).
   - In Indian large-cap equities during consolidating or range-bound market regimes, simple 20-day high breakouts suffer false expansions, triggering immediate stop-loss hits on subsequent mean-reversion.
2. **Support Pullback Resilience:**
   - Standalone Support Pullback generated **25 trades** with positive net P&L (+₹144.39, +0.14% return), a 36.0% win rate, a 1.01 Profit Factor, and a low drawdown of **3.71%**.
   - Out-of-sample performance was positive (+₹1,422.91 across 12 trades).
   - However, the sample size ($N=25$) is still too small to establish statistical significance ($t = 0.12, p = 0.90$).
3. **Transaction Cost Drag:**
   - Config B incurred **₹5,146.06** in friction; Config D incurred **₹5,720.61**. High turnover in low-edge breakout systems compounds statutory taxes and slippage, accelerating portfolio decay.

---

## 8. Phase I — Regression Testing & Database Integrity

1. **Dedicated Audit Test Suite:**
   - Created [`backend/tests/test_audit_043_controlled_prototype.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/tests/test_audit_043_controlled_prototype.py) (6 test cases).
   - Full dedicated audit test command:
     `pytest backend/tests/test_audit_043* backend/tests/test_audit_042* backend/tests/test_audit_041* backend/tests/test_audit_040* backend/tests/test_audit_037* -q`
   - **Result:** **65 passed, 0 failed, 50 warnings in 1.22s**.
2. **Core Backend Suite:**
   - **856 passed, 79 subtests passed** in 111.26s (`pytest backend/`).
3. **Frontend Unit Suite:**
   - **288/288 unit assertions passed** (`node frontend/src/utils/run_all_tests.js`).
4. **Production Database Checksum:**
   - Path: `database/swing_trading.db`
   - Hash: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (**100% Invariant**).

---

## 9. Final Audit Decisions

| Decision Category | Audit Finding & Assessment | Formal Audit Status |
| :--- | :--- | :--- |
| **1. Financial-Data Staging Quality** | Staging database initialized cleanly with verified schema. Zero fabricated records staged; yfinance lacks historical 2024 quarterly balance sheets and regulatory filing timestamps for NSE stocks. | **APPROVED (INFRASTRUCTURE READY / PENDING OFFICIAL EXCHANGE FEED)** |
| **2. Historical-Data Readiness** | Production data remains restricted to 5 quarters (`2025-Q1` to `2026-Q1`) lacking regulatory timestamps. Evaluated periods prior to 2026-02-14 remain unready for live fundamental evaluation. | **NOT READY FOR PRODUCTION** |
| **3. Momentum Breakout Prototype** | Prototype functions as intended but demonstrates severe negative expectancy (-27.20% net return, 75.0% loss rate, -₹27,196 P&L) due to false breakouts in large-cap equities. | **REJECTED AS STANDALONE STRATEGY** |
| **4. Support Pullback Prototype** | Prototype achieves positive net P&L (+₹144.39, 3.71% max DD), but trade frequency ($N=25$) is too low for statistical significance. | **APPROVED FOR FURTHER RESEARCH ONLY** |
| **5. Hybrid Prototype Readiness** | Dual-setup arbitrator successfully routes signals without conflict, but overall performance is dragged down by breakout false expansions (-22.60% return). | **NOT READY FOR PRODUCTION** |
| **6. Comparative Research Readiness** | 4-way evaluation framework successfully proved comparative dynamics, cost sensitivity, and regime vulnerability across all 20,124 stock-sessions. | **APPROVED AS RESEARCH BENCHMARK** |
| **7. Production Integration & Live Trading** | The platform has not demonstrated a robust, statistically verifiable positive edge. No broker execution layer or real-time regulatory timestamp feeds exist. | **STRICTLY NOT APPROVED / BLOCKED** |

---

*Report authored by Senior Quantitative Research Engineer & Backend Architect.*  
*Artifact persisted at `docs/audit_artifacts/AUDIT-043_CONTROLLED_PROTOTYPE_AND_FINANCIAL_STAGING.md`.*

