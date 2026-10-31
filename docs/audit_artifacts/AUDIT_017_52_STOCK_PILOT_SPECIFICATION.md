# AUDIT-017: Controlled 52-Stock Backtest Specification

**Audit Identifier:** AUDIT-017-PILOT-SPEC  
**Execution Timestamp:** 2026-10-29 22:19 IST  
**Auditor:** Quantitative Trading System Auditor & Test Engineer  
**Status:** Pre-Execution Specification Approved

---

## 1. Backtest Universe & Scope

The controlled backtest encompasses the complete active production universe of 52 Indian equity tickers:

```text
ABB, ADANIENSOL, ADANIENT, ADANIPORTS, APOLLOHOSP, ASIANPAINT, AXISBANK, BAJAJ-AUTO, 
BAJAJFINSV, BAJFINANCE, BEL, BHARTIARTL, CIPLA, COALINDIA, DRREDDY, EICHERMOT, 
ETERNAL, GRASIM, HCLTECH, HDFCBANK, HDFCLIFE, HEROMOTOCO, HINDALCO, HINDUNILVR, 
ICICIBANK, INFY, ITC, JIOFIN, JSWSTEEL, KOTAKBANK, LT, M&M, MARUTI, MAXHEALTH, 
NESTLEIND, NTPC, ONGC, POWERGRID, RELIANCE, SBILIFE, SBIN, SHRIRAMFIN, SUNPHARMA, 
TATACONSUM, TATASTEEL, TCS, TECHM, TITAN, TMPV, TRENT, ULTRACEMCO, WIPRO
```

---

## 2. Evaluation Window & Data Coverage

- **Evaluation Window:** `2025-10-01` to `2026-03-31` (6 calendar months)
- **Trading Sessions:** 122 discrete trading days
- **Price Bar Coverage:** 122 daily OHLCV bars per stock $\times$ 52 stocks = **6,344 total stock-sessions** (100.0% coverage, 0 missing sessions)
- **Financial Statement Coverage:** 5 quarterly reports per company = **260 total records**
- **Point-in-Time Lag Policy:** 45-day reporting lag fallback applied to all 260 records where `publication_date IS NULL` (Q4 ending `2025-12-31` becomes eligible on `2026-02-14`)

---

## 3. Trading Strategy & Risk Gate Parameters

### 3.1 Signal Generation (Decision Engine V1)
- **Weights:** Technical (40%), Financial Health (35%), Momentum (25%)
- **BUY Threshold:** Composite Opportunity Score $\ge 70.0$
- **Point-in-Time Requirement:** Quarters filed after `evaluation_date` are strictly excluded. If $< 4$ quarterly EPS records exist at `evaluation_date`, valuation returns `INSUFFICIENT_DATA`, preventing unverified BUY recommendations.

### 3.2 Trade Quality Filters (Week 10 Gates)
- **Entry Zone Gate:** Candidate stock market price must reside within the support pullback envelope:
  $$\text{Support} \le P_{\text{current}} \le \text{Support} + 1.0 \times \text{ATR}_{14}$$
- **Asymmetric Risk Gate:** Projected reward to downside risk must satisfy:
  $$\text{Risk/Reward Ratio} = \frac{\text{Target} - P_{\text{entry}}}{P_{\text{entry}} - \text{Stop-Loss}} \ge 1.50$$
- **Capital Filter:** Sufficient unencumbered cash balance must exist to purchase at least 1 whole share.

---

## 4. Execution, Sizing & Cost Mechanics

- **Initial Portfolio Capital:** ₹100,000.00
- **Position Allocation Limit:** Maximum 20% of portfolio capital per position (₹20,000 max initial allocation)
- **Position Sizing:** Whole-share deterministic allocation:
  $$\text{Quantity} = \left\lfloor \frac{\min(\text{Cash Balance}, \text{Portfolio Capital} \times 0.20)}{P_{\text{entry}} \times (1 + \text{Slippage})} \right\rfloor$$
- **Position Limit:** Maximum 1 active position per ticker symbol simultaneously.
- **Slippage Model:** 0.05% applied adversely to entry and exit prices.
- **Statutory & Brokerage Transaction Costs (Indian Equities):**
  - Brokerage: 0.03% (or ₹20 cap)
  - Securities Transaction Tax (STT): 0.10% on Delivery (both Buy & Sell)
  - Exchange Turnover Charges: 0.00345% (NSE)
  - SEBI Turnover Charges: 0.0001%
  - Stamp Duty: 0.015% (Buy side only)
  - Goods & Services Tax (GST): 18.0% on (Brokerage + Exchange Turnover Charges)
- **Same-Bar Collision Rule:** `STOP_LOSS` priority (if both Stop-Loss and Target are breached on the same price bar, Stop-Loss execution takes precedence).
- **End-of-Period Policy:** Mark-to-Market (MTM) on closing price of `2026-03-31` for open positions.

---

## 5. Benchmark Methodology

- **Benchmark Universe:** Identical 52-stock production universe.
- **Weighting:** Equal weight ($\frac{1}{52}$ per stock) held from `2025-10-01` to `2026-03-31`.
- **Precomputed Baseline Returns:**
  - Close-to-Close: **-7.60%**
  - Open-to-Close: **-6.84%**
  - Best Stock: `SHRIRAMFIN` (+34.44%)
  - Worst Stock: `TMPV` (-58.77%)

