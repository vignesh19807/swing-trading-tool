# AUDIT-016: Historical Financial Data Isolation & Point-in-Time Findings

**Audit Phase:** Phase 2 — Financial Data Call Path Tracing & Isolation Implementation  
**Execution Timestamp:** 2026-10-29T21:15:00+05:30  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Call Path & Lookahead Risk Analysis

Prior to AUDIT-016, an architectural asymmetry existed between market price evaluation and fundamental analysis:

### 1.1 Pre-Audit Call Path Hierarchy
```
evaluate_signals / run_backtest
  │
  ├── get_stock_data(symbol, end_date=evaluation_date)  <-- STRICTLY CUTOFF (Point-in-Time Safe)
  │
  └── analyze_financial_health(symbol, evaluation_date=evaluation_date)
        │
        ├── analyze_volatility(symbol, evaluation_date)   <-- Point-in-Time Safe
        ├── analyze_valuation(symbol, evaluation_date)    <-- Leaked: Price safe, but fin_data unconstrained
        │
        ├── analyze_roe(symbol)                          <-- NO evaluation_date (ALL Quarters Evaluated)
        ├── analyze_roce(symbol)                         <-- NO evaluation_date (ALL Quarters Evaluated)
        ├── analyze_debt_equity(symbol)                  <-- NO evaluation_date (ALL Quarters Evaluated)
        ├── analyze_profit_margin(symbol)                <-- NO evaluation_date (ALL Quarters Evaluated)
        └── analyze_growth(symbol)                       <-- NO evaluation_date (ALL Quarters Evaluated)
              │
              └── get_financial_data(symbol)             <-- Unrestricted SQL: SELECT ... ORDER BY quarter ASC
```

### 1.2 Nature of the Defect
1. **Asymmetric Parameterization:** While `analyze_financial_health` in `backend/engines/financial_engine.py` accepted `evaluation_date: Optional[str] = None`, it invoked `analyze_roe`, `analyze_roce`, `analyze_debt_equity`, `analyze_profit_margin`, and `analyze_growth` without passing `evaluation_date`.
2. **Unrestricted SQL Retrieval:** In `backend/data_pipeline/financial_service.py`, `get_financial_data(symbol)` executed an unrestricted query against `quarterly_results` joined on `companies`. Every available quarter in the database was returned, regardless of the historical backtest date.
3. **Partial Isolation in Valuation:** `analyze_valuation` accepted `evaluation_date`, but only passed it to `get_stock_data(symbol, end_date=evaluation_date)`. It retrieved quarterly EPS observations via `get_financial_data(symbol)` without date gating.

---

## 2. Implementation of Point-in-Time Eligibility

### 2.1 Standardized Temporal Eligibility Mechanics
In `backend/data_pipeline/financial_service.py`, `get_financial_data(symbol, evaluation_date=None, reporting_lag_days=45)` was enhanced to enforce strict point-in-time eligibility:

1. **Normalized Date Parsing:**
   `_normalize_eval_timestamp` parses `evaluation_date` with end-of-day semantics (`23:59:59.999999`) for date strings (`YYYY-MM-DD`) and converts timezone-aware ISO strings to timezone-naive UTC timestamps.
2. **Verified Filing Date Precedence:**
   If `quarterly_results.publication_date` is non-null and valid, the record is eligible if and only if:
   $$\text{publication\_timestamp} \le \text{evaluation\_timestamp}$$
   Status marked: `VERIFIED_POINT_IN_TIME`.
3. **Conservative Regulatory Lag Fallback:**
   If `publication_date` is `NULL` or empty, the record's earliest public availability is approximated using SEBI LODR Regulation 33:
   $$\text{period\_end} + \text{reporting\_lag\_days (default: 45)} \le \text{evaluation\_timestamp}$$
   Status marked: `PERIOD_ELIGIBLE_FALLBACK_LAG`.
   Future quarters exceeding this threshold are strictly excluded.
4. **No Eligible Records Handling:**
   If all records in the database fall after the cutoff date, `get_financial_data` returns an empty DataFrame with the required `FINANCIAL_COLUMNS` schema, setting `.attrs["data_eligibility_status"] = "NO_ELIGIBLE_RECORDS"`.
5. **Latest Snapshot Preservation:**
   When `evaluation_date` is `None`, all records are returned without filtering, preserving 100% backward compatibility for live screening workflows (`overall_status = "LATEST_CURRENT"`).

---

## 3. Sub-Analyzer and Engine Propagation

The `evaluation_date: Optional[str] = None` parameter was propagated through all layers:

1. **`backend/logic/roe_analyzer.py` (`analyze_roe`):**
   Calls `get_financial_data(symbol, evaluation_date=evaluation_date)`. Returns `evaluation_date` and `data_eligibility_status`.
2. **`backend/logic/roce_analyzer.py` (`analyze_roce`):**
   Calls `get_financial_data(symbol, evaluation_date=evaluation_date)`. Returns `evaluation_date` and `data_eligibility_status`.
3. **`backend/logic/debt_equity_analyzer.py` (`analyze_debt_equity`):**
   Calls `get_financial_data(symbol, evaluation_date=evaluation_date)`. Returns `evaluation_date` and `data_eligibility_status`.
4. **`backend/logic/profit_margin_analyzer.py` (`analyze_profit_margin`):**
   Calls `get_financial_data(symbol, evaluation_date=evaluation_date)`. Returns `evaluation_date` and `data_eligibility_status`.
5. **`backend/logic/growth_analyzer.py` (`analyze_growth`):**
   Calls `get_financial_data(symbol, evaluation_date=evaluation_date)`. Returns `evaluation_date` and `data_eligibility_status`.
6. **`backend/logic/valuation_analyzer.py` (`analyze_valuation`):**
   Calls `get_financial_data(symbol, evaluation_date=evaluation_date)` for EPS filtering in addition to price filtering.
7. **`backend/engines/financial_engine.py` (`analyze_financial_health`):**
   Passes `evaluation_date=evaluation_date` to all 7 underlying logic analyzers.
8. **`backend/logic/fundamental_analyzer.py` (Facade):**
   Provides a clean unified module re-exporting all 5 fundamental analyzers.

---

## 4. Critical Distinctions and Transparency

> [!IMPORTANT]
> **Distinction Between Verified Filing and Fallback Lag:**
> - In `database/swing_trading.db`, all 260 quarterly rows have `NULL` publication dates.
> - Consequently, all historical evaluations currently produce `data_eligibility_status = "PERIOD_ELIGIBLE_FALLBACK_LAG"`.
> - **The 45-day fallback does NOT prove actual publication timing.** It is a regulatory modeling heuristic that prevents obvious future quarter leakage (e.g. reading Q3 results before Q3 ends).
> - Full point-in-time verification requires actual filing disclosures to be scraped and populated into `quarterly_results.publication_date`.

