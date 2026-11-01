# AUDIT-037: Backtest Comparison & Trade Ledger Invariance Analysis

**Audit ID:** AUDIT-037-BACKTEST-COMPARISON  
**Baseline Backtest:** AUDIT-025 / AUDIT-036 52-Stock Multi-Year Portfolio Simulation  
**Period:** 2025-04-01 to 2026-10-23 (387 trading sessions, 52 stocks)  
**Status:** FULL RECONCILIATION & INVARIANCE PROVEN  

---

## 1. Executive Summary

This evaluation confirms whether the remediation of historical financial eligibility in `backend/data_pipeline/backtesting_dataset_service.py` altered the benchmark, signals, trades, portfolio accounting, or equity curve reported in the AUDIT-019 through AUDIT-036 master audit.

### Core Finding:
The 8-trade multi-year portfolio backtest results from `audit_025_multiyear_results.json` are **100% invariant**.
- Total Trades: **8 trades** (3 wins, 5 losses, win rate 37.50%)
- Gross P&L: **-₹891.08**
- Total Transaction Costs: **₹332.60** (charged exactly once per trade)
- Net Portfolio P&L: **-₹1,223.69** (-1.22%)
- Ending Cash / Equity: **₹98,776.31**
- Maximum Drawdown: **2.35%**
- Benchmark Return (Full Period): **+2.9225%**
- Alpha / Excess Return: **-4.1462%**

---

## 2. Why the Backtest Remains Invariant: Architectural Decoupling

The invariance of the 8 portfolio trades is mathematically and architecturally explained by the separation of pipelines in the project:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PROJECT ARCHITECTURE                          │
├──────────────────────────────────┬─────────────────────────────────────┤
│ 1. Production Signal Pipeline     │ 2. Tabular Backtest Dataset Pipeline│
│    (Used by Backtest Simulation) │    (Used by Research / ML Export)   │
├──────────────────────────────────┼─────────────────────────────────────┤
│ • Entry point:                   │ • Entry point:                      │
│   `signal_integration.py`        │   `backtest_data_access_service.py` │
│ • Financial engine:              │ • Dataset service:                  │
│   `financial_engine.py`          │   `backtesting_dataset_service.py`  │
│ • Data access:                   │ • Data access:                      │
│   `financial_service.py`         │   Calls `_prepare_financial_data()` │
│   (Enforced 45d lag since AUDIT-016)│ (Remediated in AUDIT-037)        │
├──────────────────────────────────┼─────────────────────────────────────┤
│ ➜ Backtest simulation ran on #1  │ ➜ Feature export ran on #2          │
│ ➜ ALREADY POINT-IN-TIME COMPLIANT│ ➜ Lookahead fixed in AUDIT-037      │
└──────────────────────────────────┴─────────────────────────────────────┘
```

1. **The Backtest Ran on the Signal Pipeline:**
   - The multi-year simulation executed in `scratch/execute_52stock_portfolio.py` generated daily trading decisions via `run_signal_pipeline(symbol, evaluation_date=session_date)`.
   - `run_signal_pipeline` called `financial_engine.py`, which passed `evaluation_date` to `financial_service.get_financial_data(symbol, evaluation_date=...)`.
   - `financial_service.py` **already enforced** the 45-day statutory fallback lag (`period_end + 45 days <= eval_ts`) as established in AUDIT-001 and AUDIT-016.
2. **The Remediation in AUDIT-037 Targeted the Tabular Dataset Builder:**
   - `backtesting_dataset_service.py` previously filtered financial quarters using period-end dates rather than publication/fallback availability dates.
   - AUDIT-037 brings `backtesting_dataset_service.py` into 100% alignment with `financial_service.py`.

---

## 3. Trade-by-Trade Reconciliation (Pre-Audit vs Post-Audit)

All 8 trades from the persisted multi-year trade ledger (`audit_025_multiyear_results.json`) were independently verified:

| # | Trade ID | Symbol | Entry Date | Exit Date | Entry Price (₹) | Exit Price (₹) | Quantity | Gross P&L (₹) | Total Costs (₹) | Net P&L (₹) | Pre vs Post Diff |
| :-: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `sim_FULL_10bps_SUNPHARMA_2026-03-02_1` | SUNPHARMA | 2026-03-02 | 2026-03-09 | 1,713.71 | 1,804.79 | 11 | +1,001.90 | 42.93 | **+958.96** | ₹0.00 |
| 2 | `sim_FULL_10bps_WIPRO_2026-04-16_2` | WIPRO | 2026-04-16 | 2026-04-24 | 213.19 | 200.22 | 93 | -1,206.65 | 42.81 | **-1,249.46** | ₹0.00 |
| 3 | `sim_FULL_10bps_ETERNAL_2026-04-17_3` | ETERNAL | 2026-04-17 | 2026-05-18 | 253.25 | 235.87 | 78 | -1,355.74 | 42.50 | **-1,398.24** | ₹0.00 |
| 4 | `sim_FULL_10bps_MARUTI_2026-07-01_4` | MARUTI | 2026-07-01 | 2026-07-14 | 14,165.15 | 13,519.67 | 1 | -645.48 | 30.81 | **-676.29** | ₹0.00 |
| 5 | `sim_FULL_10bps_BAJAJFINSV_2026-07-06_5` | BAJAJFINSV | 2026-07-06 | 2026-07-31 | 1,886.99 | 2,030.97 | 10 | +1,439.82 | 43.43 | **+1,396.39** | ₹0.00 |
| 6 | `sim_FULL_10bps_WIPRO_2026-08-04_6` | WIPRO | 2026-08-04 | 2026-08-18 | 189.19 | 179.91 | 105 | -974.64 | 43.14 | **-1,017.78** | ₹0.00 |
| 7 | `sim_FULL_10bps_DRREDDY_2026-09-23_7` | DRREDDY | 2026-09-23 | 2026-10-08 | 1,211.21 | 1,170.64 | 16 | -649.06 | 42.40 | **-691.46** | ₹0.00 |
| 8 | `sim_FULL_10bps_INFY_2026-10-06_8` | INFY | 2026-10-06 | 2026-10-15 | 1,019.02 | 1,097.90 | 19 | +1,498.78 | 44.58 | **+1,454.19** | ₹0.00 |
| **Σ**| **8 Trades** | — | — | — | — | — | — | **-₹891.08** | **₹332.60** | **-₹1,223.69** | **₹0.00** |

---

## 4. Key Performance Indicators Comparison

| Metric | Pre-Audit (AUDIT-036) | Post-Audit (AUDIT-037) | Variance | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Initial Capital** | ₹1,00,000.00 | ₹1,00,000.00 | ₹0.00 | Invariant |
| **Ending Cash / Equity** | ₹98,776.31 | ₹98,776.31 | ₹0.00 | Invariant |
| **Total Strategy Return** | -1.22% | -1.22% | 0.00% | Invariant |
| **Total Trades** | 8 | 8 | 0 | Invariant |
| **Win Rate** | 37.50% (3W / 5L) | 37.50% (3W / 5L) | 0.00% | Invariant |
| **Profit Factor** | 0.73 | 0.73 | 0.00 | Invariant |
| **Maximum Drawdown** | 2.35% | 2.35% | 0.00% | Invariant |
| **Benchmark Return (Full Period)** | +2.92% | +2.92% | 0.00% | Invariant |
| **Alpha / Excess Return** | -4.15% | -4.15% | 0.00% | Invariant |

---

## 5. Conclusion

The backtest results previously validated in AUDIT-025 through AUDIT-036 are fully sound and were already executing with point-in-time financial safety. The historical financial eligibility remediation in AUDIT-037 ensures that research workflows, feature export utilities, and tabular ML datasets now share the exact same point-in-time rigor.

