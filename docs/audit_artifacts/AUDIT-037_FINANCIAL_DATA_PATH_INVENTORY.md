# AUDIT-037: Financial Data Path Inventory & Call Graph

**Audit ID:** AUDIT-037-PATH-INVENTORY  
**Scope:** Complete Codebase Financial Data Retrieval Paths  
**Status:** ALL PATHS AUDITED & CLASSIFIED  

---

## 1. Executive Summary

This inventory maps every file, module, class, and function across the codebase that interacts with quarterly financial data (`quarterly_results` table). Every code path has been examined for point-in-time safety, evaluation-date propagation, fallback lag enforcement, and lookahead vulnerability.

---

## 2. Complete Call Graph: Financial Data Flow

```
                                 ┌──────────────────────────────┐
                                 │     SQLite Database          │
                                 │ database/swing_trading.db    │
                                 │ (quarterly_results table)    │
                                 └──────────────┬───────────────┘
                                                │
                                                ▼
                                 ┌──────────────────────────────┐
                                 │ backend/data_pipeline/       │
                                 │ financial_service.py         │
                                 │ get_financial_data()         │
                                 └──────────────┬───────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 │                                                             │
                 ▼                                                             ▼
┌─────────────────────────────────┐                           ┌─────────────────────────────────┐
│ Point-in-Time Signal Pipeline   │                           │ Tabular Backtest Dataset Pipeline│
│ (Production / Simulation)       │                           │ (Research / Feature Store)      │
├─────────────────────────────────┤                           ├─────────────────────────────────┤
│ backend/logic/                  │                           │ backend/data_pipeline/          │
│ • roe_analyzer.py               │                           │ backtesting_dataset_service.py  │
│ • roce_analyzer.py              │                           │ build_backtesting_dataset()     │
│ • debt_equity_analyzer.py       │                           │               │                 │
│ • profit_margin_analyzer.py     │                           │               ▼                 │
│ • growth_analyzer.py            │                           │ _prepare_financial_data()       │
│ • valuation_analyzer.py         │                           │ (Enforces 45-day lag & verified)│
│               │                 │                           │               │                 │
│               ▼                 │                           │               ▼                 │
│ backend/engines/                │                           │ backend/data_pipeline/          │
│ financial_engine.py             │                           │ backtest_data_access_service.py │
│ analyze_financial_health()      │                           │ get_backtest_input()            │
│               │                 │                           └─────────────────────────────────┘
│               ▼                 │
│ backend/logic/                  │
│ signal_integration.py           │
│ run_signal_pipeline()           │
│               │                 │
│               ▼                 │
│ Trading Strategy Execution      │
│ (Live / Paper / Backtest)       │
└─────────────────────────────────┘
```

---

## 3. Detailed Path Classification Table

| Path / Function | File Location | Purpose | Evaluation Date Handling | Fallback Lag Handling | Safety Classification | Action / Recommendation |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `get_financial_data()` | `backend/data_pipeline/financial_service.py` | Core data engineering financial reader | Enforces `eval_ts` cutoff | Enforces 45d fallback lag; supports verified pub dates | **SAFE** | Canonical access layer; signed off. |
| `get_latest_financial_data()` | `backend/data_pipeline/financial_service.py` | Convenience single-record reader | Forwards `evaluation_date` | Delegates to `get_financial_data()` | **SAFE** | Canonical access layer; signed off. |
| `_prepare_financial_data()` | `backend/data_pipeline/backtesting_dataset_service.py` | Tabular financial record selector | Enforces `eval_ts` cutoff | Enforces 45d fallback lag; supports verified pub dates | **SAFE** | Remediated in AUDIT-037; signed off. |
| `build_backtesting_dataset()` | `backend/data_pipeline/backtesting_dataset_service.py` | Historical multi-factor dataset builder | Iterates evaluation dates | Passes `reporting_lag_days` to `_prepare_financial_data` | **SAFE** | Remediated in AUDIT-037; signed off. |
| `get_backtest_input()` | `backend/data_pipeline/backtest_data_access_service.py` | Single-date point-in-time observation | Forwards `evaluation_date` | Forwards `reporting_lag_days=45` | **SAFE** | Parameterized in AUDIT-037; signed off. |
| `get_backtest_inputs()` | `backend/data_pipeline/backtest_data_access_service.py` | Multi-stock point-in-time observations | Forwards `start_date`, `end_date` | Forwards `reporting_lag_days=45` | **SAFE** | Parameterized in AUDIT-037; signed off. |
| `analyze_roe()` | `backend/logic/roe_analyzer.py` | ROE trend & consistency | Forwards `evaluation_date` | Forwards `evaluation_date` to `get_financial_data` | **SAFE** | Point-in-time compliant. |
| `analyze_roce()` | `backend/logic/roce_analyzer.py` | ROCE trend & consistency | Forwards `evaluation_date` | Forwards `evaluation_date` to `get_financial_data` | **SAFE** | Point-in-time compliant. |
| `analyze_debt_equity()` | `backend/logic/debt_equity_analyzer.py` | Solvency & leverage | Forwards `evaluation_date` | Forwards `evaluation_date` to `get_financial_data` | **SAFE** | Point-in-time compliant. |
| `analyze_profit_margin()`| `backend/logic/profit_margin_analyzer.py`| Margin expansion & stability | Forwards `evaluation_date` | Forwards `evaluation_date` to `get_financial_data` | **SAFE** | Point-in-time compliant. |
| `analyze_growth()` | `backend/logic/growth_analyzer.py` | Revenue & profit growth | Forwards `evaluation_date` | Forwards `evaluation_date` to `get_financial_data` | **SAFE** | Point-in-time compliant. |
| `analyze_valuation()` | `backend/logic/valuation_analyzer.py` | Valuation & PE/PB ratios | Forwards `evaluation_date` | Forwards `evaluation_date` to `get_financial_data` | **SAFE** | Point-in-time compliant. |
| `analyze_financial_health()`| `backend/engines/financial_engine.py`| Composite financial score | Forwards `evaluation_date` | Propagates `evaluation_date` to all 6 analyzers | **SAFE** | Point-in-time compliant. |
| `run_signal_pipeline()` | `backend/logic/signal_integration.py` | Master strategy decision engine | Forwards `evaluation_date` | Passes `evaluation_date` to `financial_engine` | **SAFE** | Point-in-time compliant. |
| `financial_normalizer.py` | `backend/data_pipeline/financial_normalizer.py` | Data ingestion normalization | N/A (Ingestion ETL) | Writes raw quarter & metrics | **SAFE** | Write-only ingestion tool. |
| `financial_quality_report.py`| `backend/data_pipeline/financial_quality_report.py`| Database QA diagnostic tool | N/A (Static DB audit) | Reads all rows for null/completeness | **SAFE** | Read-only reporting tool. |
| `benchmark_performance.py`| `backend/data_pipeline/benchmark_performance.py`| Micro-benchmark tool | N/A (Micro-benchmark) | Benchmarks latency of raw and PIT queries | **SAFE** | Diagnostic utility. |

---

## 4. Key Architectural Findings

1. **Complete Separation of Ingestion vs Retrieval:**
   - Raw financial insertion (`financial_normalizer.py`, migrations) does not contain availability logic.
   - All retrieval is routed strictly through `get_financial_data()` or `_prepare_financial_data()`.
2. **Zero Direct SQL Bypasses in Trading Logic:**
   - No analyzer in `backend/logic/` or `backend/engines/` queries the `quarterly_results` table directly via SQL. Every component calls the service layer.
3. **Harmonized Eligibility Semantics:**
   - Following AUDIT-037, `backtesting_dataset_service.py` and `financial_service.py` share identical parsing (`parse_quarter_period_end`, `_normalize_eval_timestamp`, `_normalize_pub_timestamp`) and identical 45-day statutory fallback lag rules.

