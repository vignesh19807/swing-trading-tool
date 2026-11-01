# AUDIT-044: Support Pullback Validation and Backtest Integrity Review

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `https://github.com/vignesh19807/swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Path:** `database/swing_trading.db`  
**Production Database Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Invariant)  
**Staging Database Path:** `database/staging_financial_expansion.db`  
**Staging Database Checksum:** `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465` (Invariant)  
**Date:** 2026-11-01  
**Audit Scope:** Forensic Validation of Support Pullback Prototype, Execution Realism, Entry Timing & Lookahead Immunity, Gap-Handling, Stop/Target Disambiguation, Portfolio Accounting Reconciliation, and Robustness Analysis.  
**Status:** **AUDIT COMPLETED — SUPPORT PULLBACK SCIENTIFICALLY REPRODUCED — RESEARCH APPROVED WITH DOCUMENTED LIMITATIONS — PRODUCTION/LIVE TRADING BLOCKED**

---

## 1. Executive Summary & Mandatory Baseline Integrity

Before commencing evaluation, the repository state and database integrity were audited:
- **Git Branch & HEAD:** `main` at `dc0555e39024ba075dc93da7d59896e8037a3be9`.
- **Pre-existing Working Tree State:** Tracked file modifications preserved intact (`backtest_data_access_service.py`, `backtesting_dataset_service.py`, `financial_service.py`, `test_historical_financial_safety.py`, `MASTER_AUDIT_TRACKER.md`). Zero commits, zero pushes.
- **Production Database Verification:**
  - File: `database/swing_trading.db`
  - SHA-256 Checksum: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
  - File size: `9,068,544 bytes` | `PRAGMA integrity_check` = `ok`
- **Staging Database Verification:**
  - File: `database/staging_financial_expansion.db`
  - SHA-256 Checksum: `4B5A3479ABA5F5176843EF1033C026A543D54914DB68CD2169E1FF5552BED465`
  - File size: `5,410,816 bytes` | Status: Isolated clone.

---

## 2. Phase A — Exact Reproduction of AUDIT-043 Results

The four configurations from AUDIT-043 were re-evaluated across the exact multi-year historical dataset (20,124 stock-sessions across 52 stocks and 387 sessions from 2025-04-01 to 2026-10-23) using the identical simulation harness:
- **Harness Script:** `scratch/run_audit_043_comparison.py`
- **Simulation Engine:** `backend/logic/portfolio_simulator.py`
- **Cost Configuration:** `CostModelConfig(slippage_pct=0.0010)` (10 bps slippage) with full Zerodha equity delivery taxes.

### 2.1 Discrepancy Table: AUDIT-043 Reported vs. AUDIT-044 Reproduced

| Configuration | Metric | AUDIT-043 Reported | AUDIT-044 Reproduced | Discrepancy | Reproduction Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Config A: Baseline Control** | Executed Trades | 8 | 8 | 0 | **Independently Reproduced** |
| | Win Rate | 37.5% | 37.5% | 0.0% | **Independently Reproduced** |
| | Net P&L (₹) | -₹1,223.69 | -₹1,223.69 | ₹0.00 | **Independently Reproduced** |
| | Total Return | -1.22% | -1.22% | 0.00% | **Independently Reproduced** |
| | Max Drawdown | 4.04% | 4.04% | 0.00% | **Independently Reproduced** |
| **Config B: Momentum Breakout** | Signals Generated | 220 | 220 | 0 | **Independently Reproduced** |
| | Executed Trades | 132 | 132 | 0 | **Independently Reproduced** |
| | Win Rate | 25.0% | 25.0% | 0.0% | **Independently Reproduced** |
| | Net P&L (₹) | -₹27,196.97 | -₹27,196.97 | ₹0.00 | **Independently Reproduced** |
| | Total Return | -27.20% | -27.20% | 0.00% | **Independently Reproduced** |
| | Max Drawdown | 31.41% | 31.41% | 0.00% | **Independently Reproduced** |
| **Config C: Support Pullback** | Signals Generated | 42 | 42 | 0 | **Independently Reproduced** |
| | Executed Trades | 25 | 25 | 0 | **Independently Reproduced** |
| | Win Rate | 36.0% (9W / 16L) | 36.0% (9W / 16L) | 0.0% | **Independently Reproduced** |
| | Net P&L (₹) | +₹144.39 | +₹144.39 | ₹0.00 | **Independently Reproduced** |
| | Total Return | +0.14% | +0.14% | 0.00% | **Independently Reproduced** |
| | Max Drawdown | 3.71% | 3.71% | 0.00% | **Independently Reproduced** |
| | Profit Factor | 1.01 | 1.01 | 0.00 | **Independently Reproduced** |
| **Config D: Dual-Setup Hybrid** | Signals Generated | 262 | 262 | 0 | **Independently Reproduced** |
| | Executed Trades | 150 | 150 | 0 | **Independently Reproduced** |
| | Win Rate | 26.7% | 26.7% | 0.0% | **Independently Reproduced** |
| | Net P&L (₹) | -₹22,603.30 | -₹22,603.30 | ₹0.00 | **Independently Reproduced** |
| | Total Return | -22.60% | -22.60% | 0.00% | **Independently Reproduced** |
| | Max Drawdown | 28.96% | 28.96% | 0.00% | **Independently Reproduced** |

*Conclusion:* **100.0% of the metrics and trades reported in AUDIT-043 reproduce to exact machine precision.**

---

## 3. Phase B — Entry Timing & Lookahead Forensic Audit

A line-by-line inspection of the data pipeline and execution simulator was conducted:

### 3.1 Data Flow Sequence
```
Session T Close
  ├── 1. Daily Bar T completes (Open, High, Low, Close, Volume)
  ├── 2. Historical slice strictly truncated: df_hist = df_sym.iloc[:curr_idx + 1]
  ├── 3. Support/Resistance zones computed from trailing 120 bars ending at T
  ├── 4. Setup qualification evaluated using Bar T Close (RSI, MACD, Support proximity)
  ├── 5. Signal emitted timestamped with evaluation_date = Date(T)
Session T+1 Open
  ├── 6. Portfolio Simulator Step 1: Existing open positions evaluated for exit
  ├── 7. Portfolio Simulator Step 2: Candidates from Date(T) entered at Open(T+1)
  ├── 8. Slipped entry price: Open(T+1) * (1 + slippage_pct)
  ├── 9. Portfolio Simulator Step 2.5: Intraday Bar(T+1) evaluated for same-day exit
```

### 3.2 Lookahead Defect Checks
1. **Same-Candle Fill Lookahead:** **IMMUNE**. Signals emitted at Date $T$ are entered strictly on Session $T+1$ Open. The system never executes at the Close of Session $T$.
2. **Support/Resistance Future Leakage:** **IMMUNE**. In `run_audit_043_comparison.py`, `calculate_support_resistance` is fed `sub_hist = df_hist.iloc[-120:]`, where `df_hist` ends at `curr_idx`. No future bars ($T+1, T+2, \dots$) enter the pivot detection.
3. **Weekend and Holiday Gaps:** **VERIFIED**. Dates are filtered via actual NSE trading calendar records in `daily_prices`. When Date $T$ is Friday, Date $T+1$ is Monday.
4. **Point-in-Time Technical Warmup:** **VERIFIED**. Minimum 120-bar historical buffer is enforced before pivot clustering.

---

## 4. Phase C — Stop-Loss & Target Execution Realism

Inspection of [`backend/logic/portfolio_simulator.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/logic/portfolio_simulator.py#L63-L99) reveals the exact execution mechanisms:

### 4.1 Same-Bar Stop/Target Collision Rule
When a daily candle has $\text{Low} \le \text{Stop Loss}$ and $\text{High} \ge \text{Target}$ simultaneously:
```python
if hit_stop and hit_target:
    # SAME_BAR_COLLISION_RULE: STOP_LOSS wins (conservative assumption)
    raw_exit_p = min(open_p, stop_loss)
    exit_p = apply_slippage(raw_exit_p, is_buy=False, slippage_pct=slippage_pct)
    return (ExitReason.STOP_LOSS, exit_p)
```
- **Realism Assessment:** **HIGHLY CONSERVATIVE**. The simulator assumes the unfavorable outcome (the trade was stopped out before reaching the target).

### 4.2 Gap-Down and Gap-Up Execution Realism
- **Gap-Down Below Stop Loss ($\text{Open} < \text{Stop Loss}$):**
  - Code: `raw_exit_p = min(open_p, stop_loss)`
  - Exit price is filled at the opening price ($\text{Open}$ minus slippage), **not** at the synthetic stop-loss level. This accurately captures overnight gap risk without optimistic distortion.
- **Gap-Up Above Target ($\text{Open} > \text{Target}$):**
  - Code: `raw_exit_p = max(open_p, target)`
  - Exit price is filled at $\text{Open}$, capturing the genuine overnight gap premium.

### 4.3 Same-Day Concurrency & Order of Operations
In Support Pullback, `MAXHEALTH` recorded two trades on 2026-08-11:
- Trade 21: Entered 2026-08-10, Exited 2026-08-11 on Stop Loss.
- Trade 22: Entered 2026-08-11, Exited 2026-08-11 on Stop Loss.
- **Forensic Check:** On Session 2026-08-11, Trade 21 was closed in **Step 1** (exits processed first), returning capital to cash and removing `MAXHEALTH` from `open_positions`. In **Step 2**, the pending signal from 2026-08-10 was processed; because `MAXHEALTH` was no longer in `open_positions`, Trade 22 entered legally. In **Step 2.5**, Trade 22 hit its stop-loss on the same day. **Zero violation of concurrency or double-allocation occurred.**

---

## 5. Phase D — Portfolio Accounting & Transaction-Cost Reconciliation

Every executed trade was individually reconciled against reported summaries:

### 5.1 Mathematical Accounting Invariants
For all four backtested configurations, the following identities hold to exact float precision ($< 10^{-4}$):
1. $$\sum_{i=1}^N \text{Gross P\&L}_i = \text{Reported Gross P\&L}$$
2. $$\sum_{i=1}^N \text{Total Costs}_i = \text{Reported Total Costs}$$
3. $$\text{Reported Gross P\&L} - \text{Reported Total Costs} = \text{Reported Net P\&L}$$
4. $$\text{Initial Capital} (₹100,000) + \text{Reported Net P\&L} = \text{Final Cash} = \text{Final Equity}$$

### 5.2 Support Pullback Ledger Reconciliation
- $\sum \text{Gross P\&L} = +₹1,182.7492$ (Matches reported $+₹1,182.7492$)
- $\sum \text{Total Costs} = ₹1,038.3633$ (Matches reported $₹1,038.3633$)
- $\sum \text{Net P\&L} = +₹144.3859$ (Matches reported $+₹144.3859$)
- $\text{Final Cash} = ₹100,144.39$ (Matches reported $₹100,144.39$)
- $\text{Open Positions at Horizon Close} = 0$.

### 5.3 Cost Component Completeness
Implemented costs include:
- Brokerage: ₹0 (Zerodha delivery model)
- Securities Transaction Tax (STT): 0.1% on buy and sell
- Exchange Transaction Fee: 0.00297%
- SEBI Turnover Charge: ₹10 per crore (0.0001%)
- Stamp Duty: 0.015% on buy
- GST: 18% on (Brokerage + Exchange fees + SEBI fees)
- Execution Slippage: Symmetrically charged at 10 bps on entry and exit.
- *Omitted Costs:* Depository Participant (DP) charges (₹15.93 per sell trade) are currently omitted from the cost model. For 25 trades, DP charges would total $25 \times 15.93 = ₹398.25$. Deducting DP charges turns the net P&L from $+₹144.39$ to **-₹253.86**.

---

## 6. Phase E — In-Sample (IS) vs. Out-of-Sample (OOS) Partitioning

- **In-Sample Period:** 2025-04-01 to 2026-03-31 (247 trading sessions).
- **Out-of-Sample Period:** 2026-04-01 to 2026-10-23 (140 trading sessions).
- **Boundary-Crossing Trades:** Exactly **1 trade** crossed the boundary:
  - `HINDALCO` entered 2026-04-01 (the exact boundary day) and exited 2026-04-07 (+₹713.67). Because entry occurred on 2026-04-01, it is strictly categorized as Out-of-Sample.
- **IS/OOS Performance Breakdown:**
  - In-Sample: 13 trades, 30.8% win rate, Net P&L: **-₹1,278.52** (-1.28% return).
  - Out-of-Sample: 12 trades, 41.7% win rate, Net P&L: **+₹1,422.91** (+1.42% return).
  - Full Horizon Net P&L: $-₹1,278.52 + ₹1,422.91 = \mathbf{+₹144.39}$.

---

## 7. Phase F — Support Pullback Robustness & Fragility Analysis

Although Support Pullback achieved positive net returns (+₹144.39) and avoided the catastrophic drawdown of Breakout (-27.20%), deep forensic analysis reveals critical economic fragilities:

### 7.1 Extreme Single-Stock Profit Concentration
- **Total Strategy Net P&L:** $+₹144.39$.
- **`SHRIRAMFIN` Net P&L across 3 trades:** **+₹3,472.01** (Trade 15: +₹2,705.17, Trade 16: +₹1,593.05, Trade 18: -₹826.21).
- **Strategy Net P&L excluding `SHRIRAMFIN`:** **-₹3,327.62**.
- *Finding:* **100% of the strategy's net profitability is attributable to a single stock (`SHRIRAMFIN`).** Across the remaining 51 stocks, the strategy lost ₹3,327.62 across 22 trades. The positive return is an artifact of one outlier winner, not broad systematic alpha.

### 7.2 Calendar Quarter Instability
- `2025-Q2`: 1 trade, -₹860.37
- `2025-Q3`: 4 trades, +₹261.45
- `2025-Q4`: 3 trades, -₹721.89
- `2026-Q1`: 5 trades, +₹42.29
- `2026-Q2`: 7 trades, **+₹3,982.88** (Includes `SHRIRAMFIN` outlier wins)
- `2026-Q3`: 5 trades, **-₹2,559.98** (0 wins, 5 losses, 100% loss rate)
- *Finding:* In the most recent completed quarter (`2026-Q3`), the strategy suffered 5 consecutive losses totaling -₹2,559.98.

### 7.3 Slippage Sensitivity
Running identical Support Pullback signals across 0, 10, and 20 bps slippage:
- **0 bps Slippage:** 25 trades, Net P&L: **+₹1,114.81** (+1.11% return, 3.39% Max DD).
- **10 bps Slippage:** 25 trades, Net P&L: **+₹144.39** (+0.14% return, 3.71% Max DD).
- **20 bps Slippage:** 25 trades, Net P&L: **-₹740.22** (-0.74% return, 4.02% Max DD).
- *Finding:* The strategy is highly sensitive to transaction friction. A minor 10 bps increase in execution slippage completely erases all profitability.

---

## 8. Phase H — Dedicated Test Suite Execution

A dedicated regression and audit suite [`backend/tests/test_audit_044_pullback_validation.py`](file:///c:/Users/vigne/OneDrive/Desktop/projects/swing-trading-tool/backend/tests/test_audit_044_pullback_validation.py) was implemented, testing:
- Entry timing at $T+1$ Open.
- Conservative same-bar stop-loss priority.
- Opening gap execution realism.
- Mathematical ledger accounting reconciliation.
- `MAXHEALTH` concurrency verification.
- Database immutability.

### Test Results
- **Command:** `pytest backend/tests/test_audit_044* backend/tests/test_audit_043* backend/tests/test_audit_042* backend/tests/test_audit_041* backend/tests/test_audit_040* backend/tests/test_audit_037* -q`
- **Pass Count:** **72 passed, 0 failed, 50 warnings in 2.26s**.

---

## 9. Final Decision Categories

| Decision Category | Forensic Finding & Evaluation | Formal Audit Status |
| :--- | :--- | :--- |
| **A. AUDIT-043 Reproducibility** | All 4 configurations, 262 signals, 150 trades, gross/net P&L, and drawdowns reproduced to exact machine precision. | **PASS** |
| **B. Entry Timing & Lookahead Integrity** | Evaluated on Session $T$ Close; executed strictly on Session $T+1$ Open; support/resistance zones use strict trailing 120 bars without future leakage. | **PASS** |
| **C. Stop-Loss & Target Realism** | Enforces conservative same-bar collision rule (Stop-loss wins); fills gaps at actual Open prices rather than synthetic barrier levels. | **PASS** |
| **D. Portfolio Accounting Correctness** | Whole-share integer sizing verified; cash cannot be double-spent; trade ledger matches summary down to floating-point precision. | **PASS** |
| **E. Transaction-Cost Completeness** | Zerodha taxes and 10 bps slippage verified; however, ₹15.93 DP charge per sell leg is omitted (deducting DP charges yields -₹253.86 net P&L). | **PASS WITH LIMITATIONS** |
| **F. IS/OOS Methodology** | Date boundaries verified; 1 boundary trade properly categorized; zero OOS leakage into parameter selection. | **PASS** |
| **G. Support Pullback Research Readiness** | Strategy demonstrates low drawdown (3.71%) and avoids breakout traps, but is 100% dependent on one stock (`SHRIRAMFIN`) and fails under 20 bps slippage. | **PASS WITH LIMITATIONS (RESEARCH ONLY)** |
| **H. Production Integration Readiness** | Strategy lacks broad cross-sectional statistical edge; sample size ($N=25$) is too small; unready for production deployment. | **FAIL** |
| **I. Live-Trading Readiness** | Negative performance when DP charges included; high slippage sensitivity; no broker execution layer or real-time regulatory feeds. | **FAIL (STRICTLY BLOCKED)** |

---

## 10. Final Integrity Verification

1. **Production Database SHA-256 Checksum:**
   - Path: `database/swing_trading.db`
   - SHA-256: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
   - Comparison: **100% Identical to starting baseline hash.**
2. **Production Codebase:**
   - Zero production engine files modified.
   - Zero Git commits or pushes executed.
   - Pre-existing working-tree changes preserved.

---

*Report authored by Senior Quantitative Research Engineer & Backtesting Auditor.*  
*Artifact persisted at `docs/audit_artifacts/AUDIT-044_SUPPORT_PULLBACK_VALIDATION_AND_BACKTEST_INTEGRITY.md`.*

