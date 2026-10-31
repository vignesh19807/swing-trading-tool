# AUDIT-015: Controlled Pilot Backtest Specification

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Pilot Identification:** `PILOT_AUDIT_015_CONTROLLED`  
**Evaluation Scope:** 5 Benchmark Stocks across 4 Sectors  
**Evaluation Window:** 2025-10-01 to 2026-03-31 (122 trading days × 5 stocks = 610 stock-sessions)  
**Verification Date:** 2026-10-29  

---

## 1. Pilot Universe Selection Criteria

The pilot universe consists of 5 core benchmark equities selected according to strict, pre-defined institutional criteria:
1. **Sectoral Representation:** Diversification across 4 major pillars of the Indian economy:
   - `TCS`: Information Technology
   - `INFY`: Information Technology
   - `HDFCBANK`: Private Banking & Financial Services
   - `RELIANCE`: Energy, Petrochemicals & Telecom
   - `ITC`: Fast Moving Consumer Goods (FMCG)
2. **Liquidity & Market Depth:** All 5 are Nifty 50 constituents with high daily turnover, ensuring zero liquidity friction in real trading.
3. **Data Completeness:** All 5 stocks have complete daily OHLCV bars across the 2-year database history (at least 495 daily candles each).
4. **Baseline Comparability:** Aligns directly with the audited 127 BUY recommendations from AUDIT-011, AUDIT-013, and AUDIT-014.

---

## 2. Quantitative Strategy & Execution Rules

The pilot runs using the **unmodified production strategy rules** (`backend/logic/`):

### A. Signal Qualification & Opportunity Scoring:
- **Decision Engine Threshold:** Opportunity Score $\ge 70.0 \implies \text{BUY}$.
- **Component Weights:** Technical Score (40%), Financial Health Score (30%), Momentum Context (30%).

### B. Signal Eligibility & Defensive Risk Gates (`signal_engine.py`):
1. **Gate 1 — Entry Zone Screening:**
   $$\text{Entry High} = \text{Support Level} + 0.01 \times \text{ATR}_{14}$$
   $$\text{Entry Low} = \text{Support Level}$$
   Condition: $\text{Current Price} \in [\text{Entry Low}, \text{Entry High}]$. Rejection: `PRICE_OUTSIDE_ENTRY_ZONE`.
2. **Gate 2 — Exit Sanity Screening:**
   $$\text{Stop Loss} = \text{Support Level} - 1.5 \times \text{ATR}_{14}$$
   $$\text{Target Price} = \text{Resistance Level (or Swing High)}$$
   Condition: $\text{Target} > \text{Current Price}$ and $\text{Target} > \text{Entry Price}$. Rejections: `TARGET_BELOW_CURRENT_PRICE`, `TARGET_BELOW_ENTRY_PRICE`.
3. **Gate 3 — Risk-Reward Ratio Screening:**
   $$R:R = \frac{\text{Target} - \text{Entry}}{\text{Entry} - \text{Stop Loss}} \ge 1.5$$
   Condition: $R:R \ge 1.5$. Rejection: `INSUFFICIENT_RISK_REWARD_RATIO`.

---

## 3. Portfolio & Cost Model Parameters

- **Initial Portfolio Capital:** ₹100,000.00
- **Maximum Concurrent Positions:** 5
- **Maximum Capital per Position:** 20% (₹20,000.00 max per trade)
- **Position Sizing Rule:** Whole-share integer truncation:
  $$\text{Shares} = \left\lfloor \frac{0.20 \times \text{Available Equity}}{\text{Execution Price}} \right\rfloor$$
- **Execution Price Convention:** Next-Day Market Open following signal generation date.
- **Slippage Model:** 0.05% adverse price impact applied to both entry and exit:
  $$\text{Entry Price} = \text{Open} \times (1 + 0.0005)$$
  $$\text{Exit Price} = \text{Target/Stop/Close} \times (1 - 0.0005)$$
- **Regulatory & Statutory Transaction Friction:**
  - Brokerage: ₹0.00 (Zero delivery brokerage)
  - Securities Transaction Tax (STT): 0.1% on buy and 0.1% on sell turnover
  - Exchange Charges (NSE): 0.00297%
  - SEBI Turnover Charges: 0.0001%
  - Stamp Duty: 0.015% on buy turnover only
  - Goods & Services Tax (GST): 18% on (Brokerage + Exchange + SEBI charges)

---

## 4. Documented Input Data Range & Identified Limitations

1. **Input Range:** Daily prices from `2025-10-01` through `2026-03-31` (122 market dates, 610 stock-sessions).
2. **Financial Data Limitation:** All 5 stocks in the database currently have `NULL` publication dates; fundamental eligibility evaluates under the conservative SEBI LODR 45-day lag.
3. **Strict Compliance Rule:** No trading thresholds, entry tolerances, or risk-reward ratios will be relaxed to manufacture trades.

