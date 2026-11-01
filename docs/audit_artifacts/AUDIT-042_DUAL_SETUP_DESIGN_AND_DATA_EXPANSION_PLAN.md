# AUDIT-042: Dual-Setup Strategy Design and Historical Data Expansion Plan

**Project:** Swing Trading Intelligence Platform — Indian Equities  
**Repository:** `c:\Users\vigne\OneDrive\Desktop\projects\swing-trading-tool`  
**Current Baseline Commit:** `dc0555e39024ba075dc93da7d59896e8037a3be9`  
**Production Database Checksum:** `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8` (Invariant)  
**Date:** 2026-11-01  
**Audit Scope:** Strategy Architecture Design, Historical Fundamental Data Expansion, and Controlled Research Validation Framework  
**Status:** **DESIGN & RESEARCH PLAN APPROVED — ZERO CODE/DATABASE MODIFICATION ENFORCED**

---

## 1. Executive Summary & Audit Context

### 1.1 Context and Prior Audit Ratification
In **AUDIT-040** and **AUDIT-041**, rigorous forensic analysis was conducted on the multi-year backtesting pipeline spanning 20,124 stock-sessions (52 stocks across 387 trading sessions from 2025-04-01 to 2026-10-23). The analysis uncovered two structural root causes that explained why the existing trading system produced only 8 executed trades and a net return of -1.22% (-4.15% alpha vs. the +2.92% benchmark):

1. **`FND-015`: The 11-Month Financial Cold-Start Blackout**
   - The database contains exactly 5 quarters of financial results starting at `2025-Q1`.
   - `backend/engines/financial_engine.py` (line 351) strictly requires at least two sub-scores (`len(subscores) >= 2`) to produce a valid `financial_score`.
   - Valuation requires 4 quarters for TTM EPS calculation; Growth requires 5 quarters for YoY net profit growth.
   - Enforcing the 45-day statutory fallback lag meant that `2025-Q4` only became eligible on **2026-02-14**.
   - Consequently, for the first 217 trading sessions (11,284 stock-sessions), the financial engine returned `None` (`INSUFFICIENT_DATA`), completely freezing signal generation during the entire in-sample training horizon.
2. **`FND-016`: The Upstream-Downstream Paradigm Clash**
   - The upstream Decision Engine (`backend/engines/decision_engine.py`) operates as a **Momentum Breakout** model, assigning a 49% composite weight to RSI and MACD and requiring $\text{Opportunity Score} \ge 75.0$.
   - The downstream Signal Engine (`backend/logic/signal_engine.py`) enforces a **Deep Support Pullback** gate, requiring market price to sit within 0.5 ATR of support:
     $$\text{Price} \in [\text{Support Level}, \text{Support Level} + 0.50 \times \text{ATR}_{14}]$$
   - In **100.0% of the 1,407 rejected BUY candidates**, the market price was above the upper bound ($p_{50} = +2.68\%$). Breakout momentum inherently expands price away from historical swing support, creating a mathematical conflict that rejected 77.1% of all raw BUY signals.

### 1.2 Quantitative Funnel Baseline (Verified Invariant)
The full multi-year quantitative funnel is reproduced below:

```
[Total Stock-Sessions Evaluated]
             20,124  (52 stocks * 387 sessions)
               │
               ├── 11,284 Cold-Start Blackout (2025-04-01 to 2026-02-13; len(subscores) < 2)
               │
               ▼
[Active Stock-Sessions with Opportunity Score]
              8,840  (2026-02-14 to 2026-10-23; 170 sessions)
               │
               ├── 7,015 WATCH / HOLD / AVOID / INSUFFICIENT
               │
               ▼
[Raw BUY Candidates (Opp >= 75.0)]
              1,825  (100.0%)
               │
               ├── Rejected by Signal Engine Quality Gates: 1,814 (99.40%)
               │     ├── PRICE_OUTSIDE_ENTRY_ZONE:        1,407 (77.10%) [FND-016]
               │     ├── INSUFFICIENT_RISK_REWARD_RATIO:    305 (16.71%) [FND-017]
               │     ├── TARGET_BELOW_ENTRY_PRICE:           84  (4.60%) [FND-018]
               │     └── TARGET_BELOW_CURRENT_PRICE:         18  (0.99%) [FND-018]
               │
               ▼
[Eligible Trade Setups Passed to Portfolio Simulator]
                 11  (0.60% of Raw BUYs)
               │
               ├── Rejected by Portfolio Constraints: 3 (27.27%)
               │     └── ALREADY_IN_POSITION: 3 (WIPRO 2026-04-17, ETERNAL 2026-04-20 & 2026-04-21) [FND-019]
               │
               ▼
[Executed Trades]
                  8  (3 Wins, 5 Losses; 37.5% Win Rate; Net P&L: -₹1,223.69 / -1.22%)
```

### 1.3 Core Objectives of AUDIT-042
1. **Design a Dual-Setup Strategy Architecture** that formalizes distinct trading setups:
   - **Setup A: Momentum Breakout** (capturing trending momentum when price breaks resistance).
   - **Setup B: Support Pullback** (capturing oversold mean-reversion at confirmed support).
2. **Author an Ingestion & Provenance Plan** for pre-2025 financial data (2024-Q1 through 2024-Q4 for all 52 stocks) to eliminate the 11-month cold-start blackout without lookahead bias.
3. **Establish a Controlled Research Validation Plan** to test and benchmark the new architecture across in-sample and out-of-sample periods before any code is deployed to production.

---

## 2. Phase A: Existing Implementation Architecture & Code Audit

A systematic trace of the existing 7-stage evaluation pipeline reveals exactly where structural assumptions diverge:

```
[Stage 1: Financial Engine] ──(FND-015: Cold-Start Freeze)──┐
                                                           ▼
[Stage 2: Technical Engine] ──────────────────────────► [Stage 3: Decision Engine]
                                                           │ (Opp Score >= 75.0)
                                                           ▼
[Stage 4: Stop/Target Input Service] ─────────────────► [Stage 5: Signal Engine]
                                                           │ (FND-016: Pullback Gate)
                                                           ▼
                                                        [Stage 6: Trade Quality Engine]
                                                           │ (is_eligible == True)
                                                           ▼
                                                        [Stage 7: Portfolio Simulator]
                                                           │ (Concurrency & Cash Gates)
                                                           ▼
                                                        [Executed Trades Ledger]
```

### 2.1 Stage 1: Financial Health Aggregator (`backend/engines/financial_engine.py`)
- **Function:** `analyze_financial_health(symbol, evaluation_date=None, reporting_lag_days=45)`
- **Mechanism:** Evaluates 4 sub-analyzers: Profitability (ROE/ROCE), Valuation (TTM P/E), Growth (YoY Net Profit), and Solvency (Debt/Equity).
- **Failure Point (`line 351`):**
  ```python
  if len(subscores) < 2:
      return {
          "status": "INSUFFICIENT",
          "financial_score": None,
          "recommendation": "INSUFFICIENT_DATA"
      }
  ```
  Because the database only possesses 5 quarters starting at `2025-Q1`, Valuation requires 4 quarters and Growth requires 5 quarters. With a 45-day statutory filing lag, `2025-Q4` (ended 2025-12-31) becomes eligible only on `2026-02-14`. For all 217 sessions prior to this date, only 1 sub-score exists, yielding `financial_score = None`.

### 2.2 Stage 2: Technical Analysis Pipeline (`backend/engines/technical_engine.py`)
- **Function:** `run_technical_pipeline(df)`
- **Indicators:** Computes Wilder's 14-day RSI, EMA (20, 50, 200), MACD (12, 26, 9), 14-day ATR, and rolling swing pivot support/resistance zones.
- **Scoring:** Assigns up to 30 pts for RSI (rewards RSI > 60), 30 pts for MACD (rewards bullish crossovers), and 40 pts for EMAs (bullish stack EMA20 > EMA50 > EMA200).

### 2.3 Stage 3: Decision Engine (`backend/engines/decision_engine.py`)
- **Function:** `calculate_opportunity_score(symbol, evaluation_date=None)`
- **Weighting Model:**
  - Technical Score = 40%
  - Financial Score = 35%
  - Momentum Score = 25% (derived directly from RSI & MACD sub-scores)
- **Overlap & Character:** RSI and MACD account for **49%** of the composite Opportunity Score. The Decision Engine inherently rewards stocks displaying high upward velocity and price expansion. A stock scoring $\ge 75.0$ is almost invariably trading significantly above its recent swing lows.

### 2.4 Stage 4: Stop/Target Input Service (`backend/data_pipeline/stop_target_input_service.py`)
- **Function:** `get_stop_target_inputs(symbol, evaluation_date=None)`
- **Mechanism:** Selects the nearest support level strictly *below* current price (`level < current_price`) and nearest resistance level strictly *above* current price (`level > current_price`).

### 2.5 Stage 5: Signal Engine (`backend/logic/signal_engine.py`)
- **Function:** `calculate_entry_zone(current_price, atr_14, nearest_support, recommendation)`
- **Failure Point (`lines 103-120`):**
  ```python
  lower_bound = support_level
  upper_bound = support_level + (atr_14 * 0.5)
  if not (lower_bound <= current_price <= upper_bound):
      result["reason"] = "PRICE_OUTSIDE_ENTRY_ZONE"
      return result
  result["reason"] = "VALID_PULLBACK_ENTRY"
  ```
  The Signal Engine explicitly labels its output as a `VALID_PULLBACK_ENTRY`. It assumes that the stock has pulled back to within 0.5 ATR of support. However, because the Decision Engine filtered for high-momentum breakouts, the market price in 100% of rejected cases has already expanded well beyond this narrow zone.

### 2.6 Stage 6: Trade Quality Engine (`backend/logic/trade_quality_engine.py`)
- **Function:** `evaluate_trade_eligibility(signal_payload)`
- **Mechanism:** Acts as a deterministic gatekeeper. If `signal_valid == False`, it categorizes the rejection reason (`PRICE_OUTSIDE_ENTRY_ZONE`, `INSUFFICIENT_RISK_REWARD_RATIO`, etc.) and sets `is_eligible = False`.

### 2.7 Stage 7: Sequential Portfolio Simulator (`backend/logic/portfolio_simulator.py`)
- **Function:** `simulate_portfolio(market_data, signals_by_eval_date, config)`
- **Mechanism:** Executes eligible signals on session $T+1$ Open. Enforces whole-share integer sizing, ₹100,000 capital limit, 20% max allocation, max 5 concurrent positions, and single-position concurrency per ticker (`ALREADY_IN_POSITION`).

---

## 3. Phase B: Dual-Setup Strategy Architecture Specification

To permanently eliminate the paradigm clash (`FND-016`) without sacrificing risk discipline, the platform architecture must decouple into two distinct, peer-level trading setups:

```
                          [Market Data & Indicators]
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │       SETUP A:        │             │       SETUP B:        │
        │   Momentum Breakout   │             │   Support Pullback    │
        │                       │             │                       │
        │ • RSI: 55 - 75        │             │ • RSI: 30 - 48        │
        │ • MACD: Bullish Exp   │             │ • Macro: P > EMA200   │
        │ • Price > Resistance  │             │ • Price in Supp Zone  │
        │ • Vol > 1.2x SMA20(V) │             │ • Bullish Reversal    │
        └──────────┬────────────┘             └──────────┬────────────┘
                   │                                     │
                   ▼                                     ▼
        [Breakout Entry Zone]                 [Pullback Entry Zone]
        [Breakout Stop & Target]              [Pullback Stop & Target]
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      │
                                      ▼
                        [Setup Priority Arbitrator]
                                      │
                                      ▼
                        [Deterministic Final Signal]
                                      │
                                      ▼
                        [Portfolio Execution Engine]
```

### 3.1 Setup A: Momentum Breakout (`MOMENTUM_BREAKOUT_SETUP`)

#### 3.1.1 Market Hypothesis
Equities undergoing structural trend expansion break above established resistance levels with institutional volume. When momentum accelerates, buying near the breakout point with an volatility-based stop loss allows participation in explosive multi-day continuation moves.

#### 3.1.2 Qualification & Trigger Criteria
A stock qualifies for Setup A on evaluation session $T$ if and only if:
1. **Trend & Momentum Alignment:**
   - $\text{Price}_T > \text{EMA}_{20,T} > \text{EMA}_{50,T}$ (Bullish short/intermediate trend stack).
   - $55.0 \le \text{RSI}_{14,T} \le 75.0$ (Strong positive momentum, not excessively overbought).
   - $\text{MACD Histogram}_T > 0$ and $\text{MACD Line}_T > \text{Signal Line}_T$.
2. **Breakout Level Breach:**
   - $\text{Close}_T \ge \text{Resistance Level} - 0.10 \times \text{ATR}_{14,T}$ (At or clearing resistance).
   - Highest close in the trailing 20 trading sessions ($\text{Close}_T = \max_{i=0..19} \text{Close}_{T-i}$).
3. **Volume Expansion Confirmation:**
   - $\text{Volume}_T \ge 1.20 \times \text{SMA}_{20}(\text{Volume})_T$ (Institutional confirmation).

#### 3.1.3 Entry Zone Geometry
- **Reference Point:** $\text{Breakout Level} = \text{Resistance Zone High}$.
- **Lower Entry Bound:** $\text{Breakout Level}$.
- **Upper Entry Bound:** $\text{Breakout Level} + 0.50 \times \text{ATR}_{14,T}$.
- **Execution Mechanism:** If $\text{Close}_T$ or next-day $\text{Open}_{T+1} \in [\text{Lower Bound}, \text{Upper Bound}]$, entry is valid. If price opens $> \text{Upper Bound}$, entry is rejected (`PRICE_CHASED_BEYOND_BREAKOUT_ZONE`).

#### 3.1.4 Stop-Loss Formulation
- **Structural Floor:** Placed below the breakout level or the low of the breakout candle:
  $$\text{Stop Loss} = \min(\text{Low}_T, \text{Breakout Level}) - 0.75 \times \text{ATR}_{14,T}$$
- **Capital Protection Ceiling:** Maximum dollar risk per share capped at $1.50 \times \text{ATR}_{14,T}$.
- **Assertion:** $\text{Stop Loss} < \text{Entry Price}$ must hold strictly.

#### 3.1.5 Profit Target Formulation
- Because breakout trades by definition have no overhead resistance levels nearby, targets must use volatility expansion multiples:
  $$\text{Target} = \text{Entry Price} + \max(2.0 \times \text{ATR}_{14,T}, 2.0 \times \text{Risk})$$
- Ensures that every Breakout trade structurally satisfies the mandatory Risk/Reward threshold:
  $$\text{R:R} = \frac{\text{Target} - \text{Entry Price}}{\text{Entry Price} - \text{Stop Loss}} \ge 1.50$$

---

### 3.2 Setup B: Support Pullback (`SUPPORT_PULLBACK_SETUP`)

#### 3.2.1 Market Hypothesis
In a primary bull trend, temporary selling pressure causes healthy mean-reversion pullbacks toward key horizontal or moving average support zones. Entering when price stabilizes near support provides an asymmetric risk/reward entry with a tight invalidation stop.

#### 3.2.2 Qualification & Trigger Criteria
A stock qualifies for Setup B on evaluation session $T$ if and only if:
1. **Macro Trend Filter:**
   - $\text{Price}_T > \text{EMA}_{200,T}$ (Primary secular bull market filter).
   - $\text{EMA}_{50,T} > \text{EMA}_{200,T}$ (Long-term trend integrity).
2. **Pullback / Mean-Reversion Exhaustion:**
   - $30.0 \le \text{RSI}_{14,T} \le 48.0$ (Temporary oversold or neutral consolidation).
   - $\text{MACD Histogram}_T$ showing declining negative momentum ($\text{MACD Hist}_T > \text{MACD Hist}_{T-1}$).
3. **Support Proximity & Stabilization:**
   - $\text{Low}_T \le \text{Support Level} + 0.50 \times \text{ATR}_{14,T}$.
   - Reversal Confirmation: Bullish price action (e.g., $\text{Close}_T > \text{Open}_T$, hammer candle, or bullish engulfing).

#### 3.2.3 Entry Zone Geometry
- **Reference Point:** $\text{Support Level} = \text{Support Zone Low}$.
- **Lower Entry Bound:** $\text{Support Level}$.
- **Upper Entry Bound:** $\text{Support Level} + 0.50 \times \text{ATR}_{14,T}$.
- **Execution Mechanism:** $\text{Price}_T \in [\text{Lower Bound}, \text{Upper Bound}]$.

#### 3.2.4 Stop-Loss Formulation
- **Structural Floor:** Placed safely below the support zone:
  $$\text{Stop Loss} = \text{Support Level} - 1.00 \times \text{ATR}_{14,T}$$
- **Assertion:** $\text{Stop Loss} < \text{Support Level} < \text{Entry Price}$.

#### 3.2.5 Profit Target Formulation
- Target is pegged to the next overhead structural resistance zone:
  $$\text{Target} = \text{Resistance Zone Low}$$
- If no overhead resistance exists within reasonable range, fallback to:
  $$\text{Target} = \text{Entry Price} + 2.00 \times \text{ATR}_{14,T}$$
- **Mandatory Quality Gate:** If $(\text{Target} - \text{Entry}) / (\text{Entry} - \text{Stop}) < 1.50$, the setup is rejected for `INSUFFICIENT_RISK_REWARD_RATIO`.

---

## 4. Phase C: Shared Infrastructure vs. Setup-Specific Modules

To maintain architectural cleanliness, DRY principles, and full reproducibility, shared infrastructure must be strictly separated from setup-specific business logic:

| Functional Layer | Shared Platform Infrastructure | Setup-Specific Strategy Module |
| :--- | :--- | :--- |
| **Market Data Access** | Database querying, bar normalization, caching, missing data checks | None |
| **Point-in-Time Lag** | Statutory 45-day lag enforcement, publication date validation | None |
| **Indicator Engine** | Wilder's RSI, EMA (20/50/200), MACD, 14d ATR, swing pivots | Setup-specific parameter lookups |
| **Opportunity Scoring** | Base financial health analyzer, solvency checks | Setup-specific technical weighting |
| **Entry Validation** | Generic bounds checker (`lower <= P <= upper`) | Boundary formula calculation |
| **Exit Formulation** | Slippage calculation, statutory fee calculation, R:R calculation | Formula for Stop Loss and Target price |
| **Execution Simulator** | Whole-share sizing, ₹100k cash pool, Zerodha fees, Day T+1 Open | Setup type attribution tag on trade record |
| **Concurrency Rules** | `ALREADY_IN_POSITION`, `MAX_POSITIONS_REACHED` | Priority ranking during session conflict |

### 4.1 Priority Arbitrator / Conflict Resolution Engine
When a single stock simultaneously satisfies both Setup A and Setup B criteria on the same evaluation date (e.g., during a shallow consolidation breakout):

```python
def arbitrate_setup_conflict(setup_a_candidate, setup_b_candidate) -> Tuple[Dict, str]:
    """
    Deterministically arbitrate between Setup A and Setup B for the same stock-session.
    
    Arbitration Hierarchy:
    1. Highest Expected Risk-to-Reward Ratio (Max net reward per unit risk)
    2. Highest Setup Confidence / Opportunity Score
    3. Default Priority: SETUP_A_BREAKOUT (Directional expansion priority)
    """
    rr_a = setup_a_candidate.get("risk_reward_ratio", 0.0)
    rr_b = setup_b_candidate.get("risk_reward_ratio", 0.0)
    
    # Tier 1: Risk/Reward dominance (> 0.25 delta)
    if rr_a - rr_b > 0.25:
        return setup_a_candidate, "PRIORITY_RR_SUPERIOR_SETUP_A"
    if rr_b - rr_a > 0.25:
        return setup_b_candidate, "PRIORITY_RR_SUPERIOR_SETUP_B"
        
    # Tier 2: Composite Opportunity Score
    score_a = setup_a_candidate.get("opportunity_score", 0.0)
    score_b = setup_b_candidate.get("opportunity_score", 0.0)
    if score_a > score_b:
        return setup_a_candidate, "PRIORITY_SCORE_SETUP_A"
    if score_b > score_a:
        return setup_b_candidate, "PRIORITY_SCORE_SETUP_B"
        
    # Tier 3: Deterministic fallback to Breakout
    return setup_a_candidate, "PRIORITY_DEFAULT_BREAKOUT"
```

---

## 5. Phase D: Diagnostic Candidate Trace Schema & Observability

To prevent the black-box opacity that previously obscured signal starvation, every evaluated stock-session must emit an immutable candidate trace record.

### 5.1 Candidate Trace Schema Specification
```json
{
  "trace_id": "TRC-20260416-INFY-01",
  "evaluation_date": "2026-04-16",
  "symbol": "INFY",
  "market_data": {
    "close": 1520.50,
    "volume": 4520100,
    "volume_sma20": 3200000,
    "atr_14": 28.40,
    "rsi_14": 64.20,
    "macd_hist": 4.15
  },
  "setup_evaluations": {
    "setup_a_breakout": {
      "is_qualified": true,
      "breakout_level": 1515.00,
      "entry_zone": [1515.00, 1529.20],
      "stop_loss": 1493.70,
      "target": 1577.30,
      "risk_reward_ratio": 2.12,
      "rejection_reason": null
    },
    "setup_b_pullback": {
      "is_qualified": false,
      "support_level": 1440.00,
      "entry_zone": [1440.00, 1454.20],
      "stop_loss": 1411.60,
      "target": 1515.00,
      "risk_reward_ratio": 0.0,
      "rejection_reason": "PRICE_OUTSIDE_ENTRY_ZONE"
    }
  },
  "arbitration_result": {
    "selected_setup": "SETUP_A_BREAKOUT",
    "arbitration_reason": "SOLE_QUALIFIED_SETUP"
  },
  "signal_quality": {
    "is_eligible": true,
    "rejection_reason": null
  },
  "portfolio_decision": {
    "action": "ORDER_GENERATED",
    "allocated_capital": 20000.00,
    "target_shares": 13,
    "rejection_reason": null
  }
}
```

### 5.2 Observability Metrics and Exact Denominators
To ensure rigorous diagnostic tracking, reporting must define every metric mathematically:

1. **Evaluation Coverage Rate:**
   $$\text{Coverage Rate} = \frac{\text{Evaluated Sessions with Valid Financials}}{\text{Total Available Stock-Sessions}} = \frac{8,840}{20,124} = 43.93\% \quad (\text{Baseline})$$
   *(Target with 2024 Financial Ingestion: $100.0\%$)*
2. **Setup Qualification Rate:**
   $$\text{Setup A Qualification Rate} = \frac{\text{Raw Setup A Candidates}}{\text{Active Stock-Sessions}}$$
   $$\text{Setup B Qualification Rate} = \frac{\text{Raw Setup B Candidates}}{\text{Active Stock-Sessions}}$$
3. **Filter Rejection Rate:**
   $$\text{Rejection Rate}_S = \frac{\sum \text{Rejections for Setup } S}{\text{Raw Candidates for Setup } S}$$
4. **Execution Realization Rate:**
   $$\text{Realization Rate} = \frac{\text{Executed Trades}}{\text{Eligible Signals Passed to Portfolio}} = \frac{8}{11} = 72.73\% \quad (\text{Baseline})$$

---

## 6. Phase E: Historical Financial-Data Expansion Plan

### 6.1 Root Cause of Current In-Sample Blackout
The database `quarterly_results` table currently holds 260 rows across 5 quarters (`2025-Q1` through `2026-Q1`) for 52 stocks. All 260 records lack publication dates (`publication_date IS NULL`).
Under the statutory 45-day lag:
- `2025-Q1` (ended 2025-03-31) becomes eligible 2025-05-15.
- `2025-Q2` (ended 2025-06-30) becomes eligible 2025-08-14.
- `2025-Q3` (ended 2025-09-30) becomes eligible 2025-11-14.
- `2025-Q4` (ended 2025-12-31) becomes eligible **2026-02-14**.

Because `financial_engine.py` line 351 enforces $\ge 2$ sub-scores, and Valuation requires 4 quarters and Growth requires 5 quarters, **zero stocks produced an opportunity score between 2025-04-01 and 2026-02-13**. The entire In-Sample period was dead.

### 6.2 Data Ingestion Scope & Specification
To provide a clean, continuous, 4-quarter history on Day 1 of the backtest (2025-04-01), four historical quarters must be ingested:
- `2024-Q1` (period ending 2024-03-31; statutory eligibility 2024-05-15)
- `2024-Q2` (period ending 2024-06-30; statutory eligibility 2024-08-14)
- `2024-Q3` (period ending 2024-09-30; statutory eligibility 2024-11-14)
- `2024-Q4` (period ending 2024-12-31; statutory eligibility **2025-02-14**)

Total records to ingest: $52 \text{ companies} \times 4 \text{ quarters} = \mathbf{208 \text{ new records}}$.

### 6.3 Schema Mapping & Provenance Control
Every ingested record must conform exactly to the existing `quarterly_results` table schema:
```sql
CREATE TABLE quarterly_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    quarter TEXT NOT NULL,                -- '2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4'
    revenue REAL,
    net_profit REAL,
    eps REAL,
    operating_margin REAL,
    publication_date TEXT,               -- Exact BSE/NSE filing timestamp or NULL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id),
    UNIQUE (company_id, quarter)
);
```

#### Ingestion Rules & Guardrails:
1. **Deduplication:** Enforce `UNIQUE(company_id, quarter)`. Any duplicate row must fail the transaction.
2. **Point-in-Time Lag:** If verifiable BSE/NSE corporate filing announcement timestamps are available from official exchange feeds, store them in `publication_date`. If unavailable, set `publication_date = NULL`, ensuring the system falls back to the verified 45-day lag rule:
   $$\text{Eligibility Date} = \text{Quarter End Date} + 45 \text{ calendar days}$$
3. **No Lookahead Leakage:** With `2024-Q4` ending on 2024-12-31, its statutory eligibility date is 2025-02-14. On the very first backtest session (2025-04-01), all four 2024 quarters (`2024-Q1` through `2024-Q4`) are fully eligible and historical.
4. **Staging Isolation:** Ingestion must occur in a temporary staging database (`database/staging_financial_expansion.db`) first. The production database `database/swing_trading.db` must remain read-only and checksum-verified until formal release sign-off.

### 6.4 Expected Impact on Data Readiness
- **Activated Sessions:** All 217 previously dormant sessions become active.
- **Stock-Session Opportunity Evaluations:** Increases from 8,840 to **20,124** (a $+127.6\%$ increase in analyzable history).
- **Statistically Meaningful In-Sample Testing:** The in-sample horizon (2025-04-01 to 2026-03-31) expands from 30 active trading days to **247 full trading days**.

---

## 7. Phase F: Controlled Research Validation Framework

Before altering a single production file, a 4-way comparative backtest matrix must be executed in a dedicated research sandbox:

```
                                  [Research Framework]
                                           │
         ┌──────────────────┬──────────────┴─────┬──────────────────┐
         ▼                  ▼                    ▼                  ▼
    [Matrix 1:         [Matrix 2:           [Matrix 3:         [Matrix 4:
     Baseline           Standalone           Standalone         Dual-Setup
     Monolithic]        Breakout]            Pullback]          Hybrid]
         │                  │                    │                  │
         └──────────────────┼────────────────────┴──────────────────┘
                            ▼
              [Out-of-Sample Performance Verification]
                            │
              [Cost Sensitivity: 0, 10, 20 bps]
                            │
              [Statistical Significance Testing (t-test, p-value)]
```

### 7.1 The 4-Way Comparative Backtest Matrix
1. **Matrix 1: Baseline Architecture (Control)**
   - Existing monolithic Decision Engine (Opp $\ge 75$) + Pullback Entry Zone Gate ($\le 0.5$ ATR of Support).
   - Expected Result: 8 executed trades, -1.22% return, -4.15% alpha, 99.40% rejection rate.
2. **Matrix 2: Standalone Momentum Breakout**
   - Setup A logic only. Removes support pullback requirement; validates breakout level and volume expansion.
   - Purpose: Quantify the true alpha, trade frequency, and failure rate of breakout momentum in Indian equities.
3. **Matrix 3: Standalone Support Pullback**
   - Setup B logic only. Relaxes upstream momentum requirement (RSI 30-48, Price > EMA200); keeps deep pullback entry zone.
   - Purpose: Quantify the true alpha of mean-reversion pullbacks without upstream momentum starvation.
4. **Matrix 4: Dual-Setup Hybrid with Priority Arbitrator**
   - Both Setup A and Setup B active simultaneously, arbitrated via `arbitrate_setup_conflict`.
   - Purpose: Maximize portfolio capacity, diversify across trending and mean-reverting regimes, and eliminate single-strategy starvation.

### 7.2 Research Partitioning and Standards
- **In-Sample (IS) Training Horizon:** 2025-04-01 to 2026-03-31 (247 sessions).
- **Out-of-Sample (OOS) Validation Horizon:** 2026-04-01 to 2026-10-23 (140 sessions).
- **Initial Capital:** ₹100,000 cash.
- **Position Sizing:** Whole-share integer sizing, $20\%$ max allocation per position ($\le ₹20,000$).
- **Portfolio Limits:** Maximum 5 concurrent positions, single position per ticker (`ALREADY_IN_POSITION`).
- **Transaction Costs:** Full Zerodha equity delivery model (Brokerage ₹0, STT 0.1%, Exchange Trx 0.00297%, SEBI ₹10/Cr, Stamp Duty 0.015%, GST 18%).
- **Slippage Sensitivity:** 0 bps, 10 bps (institutional standard), and 20 bps.
- **Benchmark:** Nifty 52 Equal-Weight Buy-and-Hold (+2.92% over full period).

### 7.3 Statistical Evaluation Scorecard
Each model configuration must report the following scorecard:
- Total Trades ($N$)
- Win Rate ($W\%$)
- Profit Factor ($PF$)
- Net Cumulative Return ($\%$)
- Benchmark Relative Alpha ($\%$)
- Annualized Sharpe Ratio
- Sortino Ratio
- Maximum Peak-to-Trough Drawdown ($MDD\%$)
- Student's $t$-statistic and $p$-value testing $H_0: \mu_{\text{trade}} \le 0$
- In-Sample vs. Out-of-Sample Return Degradation Ratio:
  $$\text{Degradation} = 1 - \frac{\text{Annualized Return}_{\text{OOS}}}{\text{Annualized Return}_{\text{IS}}}$$

---

## 8. Phased Implementation Roadmap & Safety Guardrails

To ensure zero risk to existing production systems, rollout must proceed through four gated stages:

```
[Phase 1: Fundamental Data Expansion] ──► Validated in Staging DB
                 │
                 ▼
[Phase 2: Strategy Architecture Modularization] ──► Isolated in new modules
                 │
                 ▼
[Phase 3: Controlled Research Execution] ──► 4-Way Comparative Evaluation
                 │
                 ▼
[Phase 4: API & UI Observability Exposure] ──► Final Production Integration
```

### 8.1 Phase 1: Fundamental Data Expansion (Staging Verification)
1. Extract 2024 Q1-Q4 quarterly financials for the 52 companies.
2. Ingest into a cloned staging database (`database/staging_financial_expansion.db`).
3. Run automated data integrity checks:
   - 0 duplicate records.
   - 0 null values in `net_profit`, `revenue`, `eps`.
   - 100% compliance with 45-day lag eligibility.
4. Verify that running `financial_engine.py` across 2025-04-01 yields valid financial scores for 100% of companies.

### 8.2 Phase 2: Strategy Architecture Modularization
1. Author standalone strategy modules without modifying existing files:
   - `backend/logic/strategies/momentum_breakout.py`
   - `backend/logic/strategies/support_pullback.py`
   - `backend/logic/strategies/priority_arbitrator.py`
2. Implement unit test suites verifying entry/exit parameters, boundary sanity checks, and arbitration edge cases.
3. Keep `signal_engine.py` and `decision_engine.py` completely untouched as the baseline control.

### 8.3 Phase 3: Comparative Research Backtesting
1. Execute the 4-way backtest matrix using the expanded historical dataset.
2. Record all candidate traces, rejections, executed trades, and equity curves.
3. Compare performance against the baseline scorecard.
4. Formally determine if any configuration achieves statistically significant positive alpha ($p < 0.05$).

### 8.4 Phase 4: API & UI Surface Integration
1. Extend API signal payload to include `setup_type` (`"BREAKOUT"` | `"PULLBACK"`) and `setup_metadata`.
2. Update frontend UI to display setup tags, dynamic entry zone overlays, and rejection diagnostic tooltips.
3. Maintain backward compatibility with existing API clients.

---

## 9. Architectural Invariants and Safety Assertions

1. **Production Database Immutability:**
   - Database path: `database/swing_trading.db`
   - Mandatory SHA-256 Checksum: `1A2036FCC72AF59B3633B5C2A077C26DD45756B3360824F36E995E2E805A28A8`
   - File size: `9,068,544 bytes`
   - Status: **UNTOUCHED AND INVARIANT**.
2. **Strategy Codebase Immutability:**
   - Production decision rules, weights, and thresholds remain 100% unchanged.
   - No experimental parameters or threshold relaxations committed to production code.
3. **No Optimization Deception:**
   - No historical backfit claims. All performance metrics must undergo strict out-of-sample verification.

---

## 10. Audit Decisions and Sign-Off

Based on the forensic evidence, architectural analysis, and comprehensive research planning completed in AUDIT-042, the following formal audit decisions are rendered:

### 1. Architecture Design Readiness: **APPROVED / READY FOR PROTOTYPING**
The Dual-Setup Strategy Architecture successfully decouples Momentum Breakout and Support Pullback into independent, logically coherent modules. It completely resolves the mathematical paradigm clash (`FND-016`) while preserving strict structural risk controls ($R:R \ge 1.50$, volatility-based stops).

### 2. Financial-Data Expansion Readiness: **APPROVED / READY FOR CONTROLLED INGESTION**
The historical data expansion plan to ingest 208 quarterly statements (2024-Q1 through 2024-Q4) across the 52 companies is architecturally sound. It eliminates the 11-month financial cold-start freeze (`FND-015`) and activates all 247 in-sample trading sessions without lookahead bias. Ingestion is approved to proceed in an isolated staging environment.

### 3. Research Validation Readiness: **APPROVED / READY FOR BACKTESTING**
The 4-way comparative backtest matrix, in-sample/out-of-sample partitioning, Zerodha cost modeling, and statistical significance criteria provide a rigorous, institutional-grade evaluation framework to assess trading efficacy before production deployment.

### 4. Live Automated Trading Approval: **STRICTLY NOT APPROVED / BLOCKED**
Live capital deployment remains **STRICTLY BLOCKED**. The platform has not yet demonstrated a statistically verified positive trading edge in live or simulated out-of-sample markets. The current multi-year baseline remains negative (-1.22% return, -4.15% alpha, $N=8$). Automated broker execution layers and live exchange regulatory feeds remain unbuilt.

---

*Report authored by Quantitative Systems Auditor & Financial Data Architect.*  
*Artifact persisted at `docs/audit_artifacts/AUDIT-042_DUAL_SETUP_DESIGN_AND_DATA_EXPANSION_PLAN.md`.*

