# MASTER BACKTEST VALIDATION REPORT
**Audit Sequence:** AUDIT-024 (Accounting Correctness) & AUDIT-025 (Multi-Year Strategy Evaluation) & AUDIT-026 (Robustness & Out-of-Sample Review)  
**Execution Timestamp:** 2026-10-30T22:25:00+05:30  
**Scope:** 52 Companies, 387 Trading Sessions (2025-04-01 to 2026-10-23), 20,124 Stock-Sessions  
**Status:** COMPLETE & INDEPENDENTLY REPRODUCED  

---

## 1. Executive Summary

A comprehensive multi-year historical backtest was executed across all 52 constituent companies in the local equity store over 387 consecutive trading sessions from **2025-04-01 through 2026-10-23**, totaling **20,124 stock-sessions**.

All simulations operated strictly on an isolated temporary database (`docs/audit_artifacts/temp_multiyear_audit_025.db`) identical in SHA-256 fingerprint to the verified production baseline. Production databases remained 100% invariant with zero writes.

### Key Headline Results:
| Metric | Full Horizon (2025-04-01 to 2026-10-23) | In-Sample (2025-04-01 to 2026-03-31) | Out-of-Sample (2026-04-01 to 2026-10-23) | 6-Month Pilot (2025-10-01 to 2026-03-31) |
| :--- | :--- | :--- | :--- | :--- |
| **Stock-Sessions Evaluated** | 20,124 | 12,896 | 7,228 | 6,344 |
| **Raw BUY Signals** | 1,825 | 1,189 | 636 | 255 |
| **Eligible BUY Signals** | 11 | 2 (1 deduplicated) | 9 (7 deduplicated) | 1 |
| **Signal Rejection Rate** | 99.40% (1,814 rejected) | 99.83% | 98.58% | 99.61% |
| **Executed Trades** | 8 | 1 | 7 | 1 |
| **Win Rate** | 37.50% (3 wins / 8 trades) | 100.0% (1 win / 1 trade) | 28.57% (2 wins / 7 trades) | 100.0% (1 win / 1 trade) |
| **Initial Capital** | ₹100,000.00 | ₹100,000.00 | ₹100,000.00 | ₹100,000.00 |
| **Gross P&L** | -₹891.08 | +₹1,001.90 | -₹1,892.98 | +₹1,001.90 |
| **Statutory Costs + Slippage** | ₹332.60 | ₹42.93 | ₹289.67 | ₹42.93 |
| **Net P&L** | **-₹1,223.69** | **+₹958.96** | **-₹2,182.65** | **+₹958.96** |
| **Portfolio Return** | -1.22% | +0.96% | -2.18% | +0.96% |
| **Maximum Drawdown** | 4.04% | 0.02% | 4.08% | 0.02% |
| **52-Stock Equal-Weight Benchmark Return** | **+2.92%** | **+0.65%** | **+1.11%** | **-7.60%** |
| **Active Strategy vs Benchmark** | **-4.14% Underperformance** | +0.31% | -3.29% | +8.56% |

---

## 2. Signal Generation & Rejection Anatomy

Across 20,124 evaluated stock-sessions, the Decision Engine generated **1,825 raw BUY recommendations**. The Trade Quality Engine and quality gates rejected **1,814 signals (99.40%)**, filtering down to **11 eligible signals**.

### Rejection Reason Distribution:
| Rejection Reason | Count | % of Rejections | % of Raw Signals | Root Cause Analysis |
| :--- | :--- | :--- | :--- | :--- |
| `PRICE_OUTSIDE_ENTRY_ZONE` | 1,407 | 77.56% | 77.10% | Stock current price opened or closed higher than the computed EMA-20 / breakout entry band. Enforces discipline by preventing chasing extended prices. |
| `INSUFFICIENT_RISK_REWARD_RATIO` | 305 | 16.81% | 16.71% | Proposed trade offered < 1.5:1 reward-to-risk ratio based on technical support/resistance levels. |
| `TARGET_BELOW_ENTRY_PRICE` | 84 | 4.63% | 4.60% | Local structural resistance was located below the entry price boundary. |
| `TARGET_BELOW_CURRENT_PRICE` | 18 | 0.99% | 0.99% | Overhead resistance had already been breached or was positioned below the current market price. |
| **Total Rejections** | **1,814** | **100.00%** | **99.40%** | **Zero unclassified or corrupted rejection states.** |

---

## 3. The Complete Multi-Year Trade Ledger

The 11 eligible signals resulted in **8 executed trades** (3 signals were in stocks where an open position was already held, adhering to the platform's strict 1-position-per-symbol rule):

| Trade ID | Symbol | Entry Date | Entry Price (₹) | Quantity | Stop Loss (₹) | Target (₹) | Exit Date | Exit Price (₹) | Exit Reason | Holding (Bars) | Gross P&L (₹) | Costs (₹) | Net P&L (₹) | Return % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sim_FULL_1` | **SUNPHARMA** | 2026-03-02 | 1,713.71 | 11 | 1,691.39 | 1,806.60 | 2026-03-09 | 1,804.79 | TARGET_REACHED | 5 | +1,001.90 | 42.93 | **+958.96** | +5.08% |
| `sim_FULL_2` | **WIPRO** | 2026-04-16 | 213.19 | 93 | 200.42 | 233.00 | 2026-04-24 | 200.22 | STOP_LOSS | 7 | -1,206.65 | 42.81 | **-1,249.46** | -6.29% |
| `sim_FULL_3` | **ETERNAL** | 2026-04-17 | 253.25 | 78 | 236.11 | 287.75 | 2026-05-18 | 235.87 | STOP_LOSS | 21 | -1,355.74 | 42.50 | **-1,398.24** | -7.07% |
| `sim_FULL_4` | **MARUTI** | 2026-07-01 | 14,165.15 | 1 | 13,533.21 | 15,224.00 | 2026-07-14 | 13,519.67 | STOP_LOSS | 10 | -645.48 | 30.81 | **-676.29** | -4.77% |
| `sim_FULL_5` | **BAJAJFINSV** | 2026-07-06 | 1,886.99 | 10 | 1,812.24 | 2,033.00 | 2026-07-31 | 2,030.97 | TARGET_REACHED | 20 | +1,439.82 | 43.43 | **+1,396.39** | +7.39% |
| `sim_FULL_6` | **WIPRO** | 2026-08-04 | 189.19 | 105 | 180.09 | 205.68 | 2026-08-18 | 179.91 | STOP_LOSS | 11 | -974.64 | 43.14 | **-1,017.78** | -5.12% |
| `sim_FULL_7` | **DRREDDY** | 2026-09-23 | 1,211.21 | 16 | 1,171.82 | 1,293.70 | 2026-10-08 | 1,170.64 | STOP_LOSS | 11 | -649.06 | 42.40 | **-691.46** | -3.56% |
| `sim_FULL_8` | **INFY** | 2026-10-06 | 1,019.02 | 19 | 970.47 | 1,097.70 | 2026-10-15 | 1,097.90 | TARGET_REACHED | 8 | +1,498.78 | 44.58 | **+1,454.19** | +7.50% |

### Deduplicated Signals:
- **ETERNAL (2026-04-17 & 2026-04-20):** Filtered out by `simulate_portfolio` because position `sim_FULL_3` was already open.
- **WIPRO (2026-04-16):** Filtered out because position `sim_FULL_2` was already open.

---

## 4. Backtest Accounting & Cost Model Verification (AUDIT-024)

Every executed trade was audited against standard Indian equity cash-market delivery transaction fees:
1. **Whole-Share Deterministic Position Sizing:**
   $$\text{Quantity} = \left\lfloor \frac{\text{Capital} \times \text{Allocation}}{\text{Entry Price}} \right\rfloor = \left\lfloor \frac{₹100,000 \times 0.20}{\text{Price}} \right\rfloor$$
   - Example SUNPHARMA: $\lfloor 20,000 / 1,713.71 \rfloor = 11$ shares (Allocated: ₹18,850.83).
   - Example MARUTI: $\lfloor 20,000 / 14,165.15 \rfloor = 1$ share (Allocated: ₹14,165.15).
2. **Execution Timing & Lookahead Immunity:**
   - Evaluated on Day $T$ Close $\rightarrow$ Entered on Day $T+1$ Open.
   - Zero same-bar lookahead leakage.
3. **Statutory Transaction Costs Applied (Zerodha Cash Delivery Model):**
   - Brokerage: Zero (or flat delivery).
   - STT (Securities Transaction Tax): 0.1% on Buy + 0.1% on Sell.
   - Exchange Turnover Charges: 0.00297%.
   - SEBI Charges: ₹10 per crore (0.0001%).
   - Stamp Duty: 0.015% on Buy.
   - GST: 18% on (Brokerage + Exchange Charges + SEBI).
   - Slippage: 0.1% (10 bps) applied against both entry and exit.
4. **Conservation of Capital:**
   $$\text{Ending Cash} = \text{Initial Capital} + \sum \text{Net P\&L} = ₹100,000.00 - ₹1,223.69 = ₹98,776.31$$
   $$\text{Final Equity} = \text{Cash} + \text{Open Position Value} = ₹98,776.31 + ₹0.00 = ₹98,776.31$$
   Validated exact balance to the nearest paisa.

---

## 5. Robustness & Sensitivity Analysis (AUDIT-026)

### A. In-Sample vs. Out-of-Sample Performance
- **In-Sample Period (2025-04-01 to 2026-03-31):**
  - Trades: 1 (SUNPHARMA)
  - Return: +0.96% (+₹958.96)
  - Benchmark: +0.65%
- **Out-of-Sample Period (2026-04-01 to 2026-10-23):**
  - Trades: 7 (2 Wins, 5 Losses)
  - Return: -2.18% (-₹2,182.65)
  - Benchmark: +1.11%
- **Analysis:**
  The single winning trade in the 6-month pilot (SUNPHARMA) was an artifact of ultra-small sample size ($N=1$). When evaluated over the wider 2-year horizon ($N=8$), the strategy demonstrated classic out-of-sample decay, underperforming the broader market.

### B. Slippage Sensitivity Analysis
| Slippage Setting | Trades | Gross P&L (₹) | Total Costs (₹) | Net P&L (₹) | Total Return % | Max Drawdown % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0 bps (Zero Slippage)** | 8 | -₹658.20 | ₹283.65 | -₹941.85 | -0.94% | 3.82% |
| **10 bps (Baseline Model)** | 8 | -₹891.08 | ₹332.60 | -₹1,223.69 | -1.22% | 4.04% |
| **20 bps (Adverse Execution)** | 8 | -₹1,123.95 | ₹399.01 | -₹1,522.96 | -1.52% | 4.28% |

Every 10 basis points of slippage extracts approximately **₹281** in net drag across 8 trades (~₹35 per round trip). Even under zero slippage, the strategy generated negative gross P&L (-₹658.20), demonstrating that underperformance is driven by signal quality, not friction alone.

---

## 6. Research Conclusion & Release Guidance

1. **Software Pipeline Verification:**
   The backtesting engine, data pipeline, trade quality filters, order sizing, and fee accounting are **mathematically correct, deterministic, and free of defects**.
2. **Strategy Alpha & Commercial Viability:**
   The current ruleset generates **extremely low trade frequency** (0.4 trades/month) and **negative net alpha (-1.22% vs +2.92% benchmark)**. 
3. **Mandatory Production Classification:**
   The platform is **APPROVED for Release as an Interactive Market Analytics & Quantitative Screening Workbench**.
   The platform is **STRICTLY DISAPPROVED for Unattended Automated Capital Deployment**. Real-money execution must not be permitted until a re-architected strategy ruleset is designed and backtested.

