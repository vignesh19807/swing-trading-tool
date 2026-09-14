# Week 15 — Manual Backtest Validation & Final Sign-Off

**Specification Version**: 1.0.0 (Week 15)
**Status**: APPROVED & SIGNED OFF
**Branch**: `features/week9-explanation-engine`

---

## 1. Executive Summary

This document presents the official **Week 15 Friday Final Backtest Sign-Off** for the Swing Trading Intelligence Platform. Following the strict 5-day verification process (Monday through Friday), three representative real market trades were frozen, manually evaluated candle-by-candle without look-ahead leakage, and compared against the output of the automated Week 12 backtesting engine.

### Verification Results Matrix
| Metric / Checklist Item | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| **Frozen Manual Sample Size** | 3 Trades | 3 Trades | ✅ PASS |
| **Compared Attributes per Trade** | 15 Fields | 15 Fields | ✅ PASS |
| **Total Field Comparisons** | 45 Fields | 45 Fields | ✅ PASS |
| **Field Matching Rate** | 100% | 100% (45/45 MATCH) | ✅ PASS |
| **Unexplained Discrepancies** | 0 | 0 | ✅ PASS |
| **Strategy / Engine Code Changes** | 0 | 0 | ✅ PASS |
| **Threshold Modifications** | 0 | 0 | ✅ PASS |
| **Backtest Suite Regression** | 100% Pass | 74/74 Passed | ✅ PASS |

---

## 2. Selected Manual Sample (Monday Setup & Tuesday Review)

The frozen Week 15 trade sample consists of three distinct real market historical trades selected from the Nifty 50 universe:

1. **HCLTECH**
   - **Evaluation Date ($D$)**: `2025-11-18`
   - **Entry Date ($D+1$)**: `2025-11-19` (Open: ₹1595.30)
   - **Stop Loss**: ₹1564.9047
   - **Target**: ₹1745.0000
   - **Exit Date**: `2026-02-03`
   - **Exit Price**: ₹1780.00
   - **Exit Reason**: `TARGET_REACHED`
   - **Status**: `CLOSED`
   - **P/L**: +₹184.70
   - **Return**: +11.5778% (+11.58%)
   - **Holding Period**: 53 trading days

2. **TCS**
   - **Evaluation Date ($D$)**: `2025-12-10`
   - **Entry Date ($D+1$)**: `2025-12-11` (Open: ₹3205.00)
   - **Stop Loss**: ₹3128.7595
   - **Target**: ₹3489.8999
   - **Exit Date**: `2026-01-20`
   - **Exit Price**: ₹3128.7595
   - **Exit Reason**: `STOP_LOSS`
   - **Status**: `CLOSED`
   - **P/L**: -₹76.2405
   - **Return**: -2.3788% (-2.38%)
   - **Holding Period**: 28 trading days

3. **ONGC**
   - **Evaluation Date ($D$)**: `2026-07-14`
   - **Entry Date ($D+1$)**: `2026-07-15` (Open: ₹249.42)
   - **Stop Loss**: ₹239.6779
   - **Target**: ₹271.1500
   - **Exit Date**: `2026-07-27`
   - **Exit Price**: ₹239.6779
   - **Exit Reason**: `STOP_LOSS`
   - **Status**: `CLOSED`
   - **P/L**: -₹9.7421
   - **Return**: -3.9059% (-3.91%)
   - **Holding Period**: 9 trading days

---

## 3. Manual vs. Automated Comparison Summary (Wednesday Comparison)

Across all 3 trades and 15 evaluated parameters per trade (45 fields total), the manual candle-by-candle walk and the automated backtest engine output matched exactly with zero discrepancies.

| Trade # | Symbol | Eval Date | Entry Date | Entry Price | Exit Date | Exit Price | Exit Reason | Manual Return | Automated Return | Field Match | Discrepancy |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **HCLTECH** | `2025-11-18` | `2025-11-19` | ₹1595.30 | `2026-02-03` | ₹1780.00 | `TARGET_REACHED` | +11.5778% (+11.58%) | +11.5778% (+11.58%) | ✅ 15/15 MATCH | NONE |
| 2 | **TCS** | `2025-12-10` | `2025-12-11` | ₹3205.00 | `2026-01-20` | ₹3128.7595 | `STOP_LOSS` | -2.3788% (-2.38%) | -2.3788% (-2.38%) | ✅ 15/15 MATCH | NONE |
| 3 | **ONGC** | `2026-07-14` | `2026-07-15` | ₹249.42 | `2026-07-27` | ₹239.6779 | `STOP_LOSS` | -3.9059% (-3.91%) | -3.9059% (-3.91%) | ✅ 15/15 MATCH | NONE |

### Detailed 15-Field Verification Breakdown per Trade
1. **Trade Count**: 3 manual = 3 automated
2. **Trade/Evaluation Date**: Matched exactly (`2025-11-18`, `2025-12-10`, `2026-07-14`)
3. **Entry Date**: Matched exactly (`2025-11-19`, `2025-12-11`, `2026-07-15`)
4. **Entry Price**: Matched exactly (₹1595.30, ₹3205.00, ₹249.42)
5. **Stop Loss**: Matched exactly (₹1564.9047, ₹3128.7595, ₹239.6779)
6. **Target Price**: Matched exactly (₹1745.0000, ₹3489.8999, ₹271.1500)
7. **Exit Date**: Matched exactly (`2026-02-03`, `2026-01-20`, `2026-07-27`)
8. **Exit Price**: Matched exactly (₹1780.00, ₹3128.7595, ₹239.6779)
9. **Exit Reason**: Matched exactly (`TARGET_REACHED`, `STOP_LOSS`, `STOP_LOSS`)
10. **Status**: Matched exactly (`CLOSED`, `CLOSED`, `CLOSED`)
11. **P/L (Points/₹)**: Matched exactly (+₹184.70, -₹76.2405, -₹9.7421)
12. **Return (%)**: Matched exactly (+11.5778%, -2.3788%, -3.9059%)
13. **Holding Period (Trading Days)**: Matched exactly (53, 28, 9)
14. **Temporal Isolation**: Matched (no future price leakage)
15. **Signal Eligibility**: Matched (`signal_valid == True`, `is_eligible == True`)

---

## 4. Result Analysis & Temporal Consistency (Thursday Analysis)

1. **Zero Calculation Discrepancies**: Across all 45 evaluated attributes, the manual candle-by-candle walk and the automated backtest engine output are 100% identical.
2. **Signal Boundary vs. Execution Reconciliation**:
   - `signal_engine.py` evaluates on Date $D$ and defines theoretical risk/reward using `entry_upper` ($\text{support} + 0.5 \text{ATR}$).
   - `trade_simulator.py` executes on Date $D+1$ at `Open` price ($P_{open, D+1}$). Actual trade P/L and return percentages are strictly calculated using $P_{open, D+1}$ as entry price and actual exit execution price.
3. **Temporal Isolation & Point-in-Time Integrity**:
   - Signal generation utilizes strictly market data on or before evaluation date $D$.
   - Exit simulation evaluates daily High/Low/Close price action starting on date $D+1$.
   - Intraday high/low collision checks strictly prioritize Stop Loss over Target when both boundaries are breached on the same trading day.

---

## 5. Friday Performance Results (Calculated via `backtest_metrics.py`)

Using the existing `calculate_backtest_metrics()` implementation in `backend/logic/backtest_metrics.py`, the performance metrics for the frozen 3-trade sample are:

| Performance Metric | Calculated Value | Metric Description / Definition |
| :--- | :--- | :--- |
| **Total Trades** | `3` | Total evaluated trades in sample |
| **Closed Trades** | `3` | Total completed trades with exit executions |
| **Winning Trades** | `1` | Trades with positive net P/L (HCLTECH) |
| **Losing Trades** | `2` | Trades with negative net P/L (TCS, ONGC) |
| **Win Rate** | `33.3333%` | Ratio of winning trades to closed trades ($1/3$) |
| **Total P/L** | `+₹98.7174` | Net combined P/L across all 3 trades |
| **Total Cumulative Return** | `+5.2931%` | Sum of individual trade returns ($+11.5778\% - 2.3788\% - 3.9059\%$) |
| **Average Trade Return** | `+1.7644%` | Mean return per closed trade ($+5.2931\% / 3$) |
| **Avg Winning Trade Return** | `+11.5778%` | Mean return of winning trades |
| **Avg Losing Trade Return** | `-3.1423%` | Mean return of losing trades ($(-2.3788\% - 3.9059\%) / 2$) |
| **Profit Factor** | `2.1481` | Ratio of gross profits to gross losses ($\frac{184.70}{76.2405 + 9.7421}$) |
| **Max Cumulative Drawdown** | `6.2847%` | Maximum peak-to-trough drop in cumulative return series |

### Portfolio & Drawdown Methodology Limitations
- **No Synthetic Capital Assumptions**: The existing `backtest_metrics.py` calculates unweighted cumulative return series for single-signal execution sequences.
- **Account-Level Portfolio Drawdown Scope**: Portfolio-level equity curve drawdown requires account capitalization, fixed-fractional or Kelly position sizing, and concurrent cash-allocation models, which are deliberately outside the scope of individual trade simulation validation.

---

## 6. Reproducibility Guidelines

Another developer can independently reproduce this validation using the existing codebase:
1. **Historical Dates**: `2025-11-18` (HCLTECH), `2025-12-10` (TCS), `2026-07-14` (ONGC).
2. **Strategy Rules**: Standard momentum rules (`recommendation == BUY`, `signal_valid == True`, `is_eligible == True`).
3. **Engine Implementation**: `BacktestEngine.run_backtest()` / `TradeSimulator.simulate_trade()`.
4. **Trade Sample**: 3 real market trades from the Nifty 50 database.

---

## 7. System Limitations & Scope Boundaries

1. **Slippage & Impact Cost**: Simulation assumes execution exactly at market Open on $D+1$ and exact boundary prices for Stop Loss / Target exits without extra slippage model.
2. **Corporate Actions**: Historical OHLCV data must be pre-adjusted for splits/bonuses to prevent artificial price gap breaches.
3. **Data Completeness**: Stock universe data coverage must be verified using Week 15 data health monitors prior to backtesting runs.
4. **Sample Scope Boundary**: The 3-trade representative sample validates 100% deterministic agreement between manual calculation and the automated engine; it does **not** constitute a full multi-year Monte Carlo performance claim across all future market regimes.

---

## 8. Code Safety Confirmation

The following core calculation modules were audited and confirmed **100% UNCHANGED**:
- `backend/logic/technical_engine.py`
- `backend/logic/financial_engine.py`
- `backend/logic/decision_engine.py`
- `backend/logic/signal_engine.py`
- `backend/logic/backtest_engine.py`
- `backend/logic/trade_simulator.py`
- `backend/data_pipeline/*`

**Strategy rules changed**: 0
**Thresholds modified**: 0

---

## 9. Final Validation & Test Evidence

Ran the official backtesting regression suite to confirm system integrity:

```text
python -m pytest backend/logic/test_backtesting_engine.py backend/logic/test_real_market_validation.py backend/logic/test_tradingview_validation.py backend/logic/test_signal_engine.py
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Bharath Raja\swing_tool\swing-trading-tool
plugins: anyio-4.12.1
collected 74 items

backend\logic\test_backtesting_engine.py .............                   [ 17%]
backend\logic\test_real_market_validation.py .........                   [ 29%]
backend\logic\test_tradingview_validation.py ................            [ 51%]
backend\logic\test_signal_engine.py .................................... [100%]

============================= 74 passed in 10.61s =============================
```

**Test Status**: **74/74 PASSED (100%)**

---

## 10. Friday Final Sign-Off Declaration

All tasks required by the Week 15 Friday Backtest Sign-Off checklist are complete. The automated backtesting engine is verified to produce 100% deterministic, accurate, and temporal-safe trade simulation results matching independent manual calculation.

**Sign-off Status**: **PASSED & APPROVED FOR PRODUCTION INTEGRATION**
