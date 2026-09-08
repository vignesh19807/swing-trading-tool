# Week 12 — Historical Backtesting & Evaluation Contract

## 1. Purpose
The Week 12 Historical Backtesting Engine enables point-in-time, causally correct historical evaluation and trade simulation for the Swing Trading Intelligence Platform. It verifies signal reliability across historical periods without look-ahead bias or future data leakage.

---

## 2. System Inputs
- **Stock Universe**: List of valid NSE stock symbols (e.g., `["TCS", "INFY", "RELIANCE"]`).
- **Date Range**: Evaluation `start_date` and `end_date` (YYYY-MM-DD format).
- **Market Data**: Daily OHLCV price bars sourced from `backend.data_pipeline.historical_data_service`.
- **Logic Engine Pipeline**: Unmodified Signal Engine, Decision Engine, Trade Quality Engine, and Data Engineer services.

---

## 3. Date & Temporal Isolation Rules
- **Explicit Evaluation Date**: Every historical signal evaluation MUST pass an explicit `evaluation_date=D`.
- **Temporal Boundary**: All Technical, Financial, Sector, and Decision calculations on date $D$ use data strictly $\le D$.
- **Post-Signal Simulation**: Market price bars for date $> D$ are inspected ONLY AFTER the signal for date $D$ has been generated. Future bars never influence historical signal generation.

---

## 4. Historical Signal Evaluation
- Generated via `backend.logic.signal_integration.run_signal_pipeline(symbol, evaluation_date=D)`.
- Reuses all existing approved rules:
  - Entry zone: `[support_level, support_level + (atr_14 * 0.50)]`.
  - Recommendation threshold: Recommendation must be `"BUY"`.
  - Risk/Reward ratio threshold: $\text{reward} / \text{risk} \ge 1.50$.
  - Stop loss & Target multipliers: Stop $= \text{support} - (\text{atr} \times 1.50)$, Target $= \text{resistance}$ or $\text{price} + (\text{atr} \times 2.00)$.
  - Trade Quality & Risk Context: Evaluates eligibility and attaches structured risk flags.

---

## 5. Trade Simulation Rules

### A. Entry Price Rule
- **Rule**: `NEXT_DAY_OPEN`.
- If a signal generated on date $D$ is valid (`signal_valid=True`) and eligible (`is_eligible=True`), the trade is entered on the first available trading bar $D+1$.
- Entry price $P_{\text{entry}} = \text{open}_{D+1}$.

### B. Exit Rules
For each subsequent bar $t \ge D+1$:
1. **Stop Loss**: Hit if $\text{low}_t \le \text{stop\_loss}$. Exit price = $\min(\text{open}_t, \text{stop\_loss})$ (accounts for gap-down opens). Exit reason = `"STOP_LOSS"`.
2. **Target Reached**: Hit if $\text{high}_t \ge \text{target}$. Exit price = $\max(\text{open}_t, \text{target})$ (accounts for gap-up opens). Exit reason = `"TARGET_REACHED"`.
3. **Same-Bar Collision Priority**: If BOTH $\text{low}_t \le \text{stop\_loss}$ AND $\text{high}_t \ge \text{target}$ occur on the exact same bar, **`STOP_LOSS` priority wins** (conservative risk management assumption). Exit price = $\min(\text{open}_t, \text{stop\_loss})$, Exit reason = `"STOP_LOSS"`.

### C. Open Trades & End of Backtest
- If neither Stop Loss nor Target is reached before market price history ends or backtest window closes, status is marked as `"OPEN"`, exit reason = `"END_OF_BACKTEST"`, with mark-to-market valuation at the final available close price.

---

## 6. Performance Metrics Formulas

1. **Total Trades**: Count of evaluated trades.
2. **Closed / Open / Invalid / Incomplete Trades**: Counts by explicit trade status.
3. **Win Rate**:
   $$\text{Win Rate \%} = \left( \frac{\text{Winning Trades}}{\text{Closed Trades}} \right) \times 100 \quad (\text{if Closed Trades} > 0 \text{ else } 0.0)$$
4. **Total P/L**:
   $$\text{Total P/L} = \sum (\text{Exit Price} - \text{Entry Price})$$
5. **Total Return %**:
   $$\text{Total Return \%} = \sum \left( \frac{\text{Exit Price} - \text{Entry Price}}{\text{Entry Price}} \right) \times 100$$
6. **Average Trade Return %**:
   $$\text{Avg Return \%} = \frac{\text{Total Return \%}}{\text{Closed Trades}}$$
7. **Profit Factor**:
   $$\text{Profit Factor} = \frac{\sum \text{Gross Profits}}{\sum |\text{Gross Losses}|}$$
8. **Max Drawdown %**: Peak-to-trough maximum decline in cumulative return series.

---

## 7. Look-Ahead Bias Leakage Protections
- Dedicated unit test `test_future_data_does_not_affect_past_signal` verifies that altering or adding future price bars ($D+1, D+2, \dots$) results in zero changes to the signal evaluated on date $D$.

---

## 8. Persistence Integration
- Reuses `backend.data_pipeline.backtest_result_service.store_backtest_results` without modifying SQLite schema.
- Records structured metadata keyed by `(run_id, symbol, evaluation_date)`.

---

## 9. Known Limitations & Assumptions
- **Slippage & Commission**: Excluded in V1 backtesting model per scope.
- **Reporting Period Availability**: Financial reporting periods use quarter end date as point-in-time boundary per Data Engineer contract.
- **Same-Bar Collision**: Conservative assumption prioritizing Stop Loss over Target.
