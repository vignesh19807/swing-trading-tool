# AUDIT-009: Trading Pipeline & Signal Discrepancy Trace

## 1. Resolution of the AUDIT-007 Discrepancy

### Observation in AUDIT-007:
* In a 5-stock historical sample across 610 evaluated sessions (2025-10-01 to 2026-03-31), the multi-engine pipeline produced:
  * 127 raw `BUY` recommendations from the Decision Engine.
  * Exactly **0 eligible trade signals** from the Signal Engine.
  * Exactly **0 executed trades** in the portfolio backtest.

### Systematic Pipeline Trace:
We traced the progression of data across the pipeline stages:

```
1. Raw Historical Prices (daily_prices)
      │
2. Technical Engine (EMAs, RSI, MACD, ATR 14, Support/Resistance zones)
      │
3. Financial Engine (Quarterly health score under 45-day lag safety)
      │
4. Decision Engine (Opportunity Score composite: 40% Tech + 35% Fin + 25% Mom)
      │  Produces raw recommendations: 'BUY' (score ≥ 70), 'WATCH' (50-69), 'HOLD', 'AVOID'
      ▼
5. Signal Engine & Risk Gate (backend/logic/signal_integration.py & signal_engine.py)
      │  Evaluates structural entry criteria:
      │   a) Current price must lie inside Entry Zone: [Support, Support + 1.0% * ATR_14]
      │   b) Target (nearest resistance) must be strictly ABOVE entry price
      │   c) Risk/Reward ratio must meet minimum threshold (≥ 1.5)
      │   d) Stop-loss must be strictly BELOW entry price
      ▼
6. Portfolio Simulator (backend/logic/portfolio_simulator.py)
      │  Executes candidate only if is_eligible=True and signal_valid=True
      ▼
7. Trade Execution & Accounting
```

### Confirmed Finding:
The zero-trade outcome is **not a software defect**, but rather the intended strict behavior of the **Signal Engine Risk Gate**:
* When a stock receives a raw algorithmic score $\ge 70$, the Decision Engine flags it as `BUY`.
* However, the downstream Signal Engine verifies whether the stock is at an actionable entry price relative to support and resistance.
* Across the tested 610 historical sessions, whenever a `BUY` score occurred, the price had already broken out or pulled away beyond the conservative entry band $[Support, Support + 1.0\% \times ATR_{14}]$, triggering the rejection reason:
  `PRICE_OUTSIDE_ENTRY_ZONE`.
* In other instances with downward-sloping resistance channels, the nearest resistance was below the proposed entry price, triggering:
  `TARGET_BELOW_ENTRY_PRICE`.

---

## 2. Representative Pipeline Test Cases Verified

As part of AUDIT-005 and AUDIT-006, all core trade lifecycle states and edge cases were independently verified using controlled synthetic and historical inputs:

| Case | Scenario Tested | Handling & Output Verified | Status |
|---|---|---|:---:|
| **Case 1** | Eligible BUY Signal Execution | Next-day open entry, whole-share sizing, cash deducted, entry costs applied | **VERIFIED** |
| **Case 2** | Insufficient Data Rejection | Missing financial or technical indicators returns `recommendation: INSUFFICIENT_DATA`, `signal_valid: False` | **VERIFIED** |
| **Case 3** | Entry Rule Rejection | Price outside support zone returns `PRICE_OUTSIDE_ENTRY_ZONE`, disqualified | **VERIFIED** |
| **Case 4** | Portfolio Capacity Rejection | `MAX_POSITIONS_REACHED` triggers when active positions = 5; signal safely rejected | **VERIFIED** |
| **Case 5** | Same-Day Stop-Loss Exit | Stop loss breached on entry session closes position immediately, prevents lookahead | **VERIFIED** |
| **Case 6** | Target Reached Exit | High $\ge$ Target exits at `max(open, target)` with sell-side costs deducted | **VERIFIED** |
| **Case 7** | Stop/Target Collision | Same-bar collision enforces `STOP_LOSS_PRIORITY` (conservative assumption) | **VERIFIED** |
| **Case 8** | Open Position at End of Test | `MARK_TO_MARKET` policy marks to final close, calculates unrealized P/L separately | **VERIFIED** |
| **Case 9** | Zero-Trade Run | Simulator safely reports ₹100,000 cash, 0 trades, `None` for win rate/profit factor | **VERIFIED** |
| **Case 10** | Multi-Run Isolation | Distinct runs with unique IDs (`run_A`, `run_B`) never cross-contaminate trade records | **VERIFIED** |
| **Case 11** | Transactional Persistence | Verified multi-table storage and read-back across `backtest_runs` and `backtest_trades` | **VERIFIED** |

