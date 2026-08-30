# Week 4 — Annual Financial Contract

## A. Purpose
This document specifies the integration contract for annual financial data between the Data Engineering and Logic Engineering layers, implemented during Week 4 Monday and extended during Tuesday.

**Architectural Boundary:**
- **Data Engineer:** Responsible for fetching, persisting, and supplying the annual financial data payload to the Logic Engineering layer.
- **Logic Engineer:** Responsible ONLY for calculating financial trend metrics and analysis logic, assuming the input strictly follows this contract.
- The Logic Engineering layer does NOT fetch, store, or persist annual financial data.

## B. Annual Input Structure
The `analyze_annual_financial_health` function expects a `List[Dict[str, Any]]` where each dictionary is a standardized annual record.

```python
{
    "symbol": str,           # Required
    "period": str,           # Required (ISO format)
    "revenue": float | None, # Required key, value can be None
    "net_profit": float | None,
    "eps": float | None,
    "roe": float | None,
    "roce": float | None
}
```

## C. Period Format
The `period` field must use the standard **ISO YYYY-MM-DD** format representing the fiscal year-end date (e.g., `"2025-03-31"`).

## D. Required vs Optional Fields
All dictionary keys are **REQUIRED**. If a metric is missing or unavailable, the value must be explicitly set to `None`.

## E. Analyzer Output Structure
The analyzer returns a single dictionary representing the analysis state:
```python
{
    "symbol": "INFY",
    "status": "VALID",
    "records": 2,
    "latest_period": "2024-03-31",
    "latest_revenue": 1331.0,
    "revenue_yoy_growth": 10.0,
    "revenue_trend": "Improving",
    "revenue_cagr": 10.0,       # Tuesday Feature
}
```

## F. CAGR Calculation (Tuesday Feature)
The analyzer calculates Compound Annual Growth Rate (CAGR) for Revenue and Net Profit.
**Formula:** `CAGR = ((Ending Value / Starting Value) ^ (1 / Elapsed Years)) - 1`

- **Elapsed Years:** Calculated based on the precise day difference between the earliest and latest valid period divided by 365.25.
- **Missing Data:** Start and end values are dynamically resolved by picking the earliest and latest *available* data points. Missing periods are safely skipped.
- **Negative/Zero Start Value:** If the starting value is `<= 0`, CAGR is mathematically invalid and the result evaluates to `None`. Missing values are never fabricated or coerced to 0.

## G. Missing-Data Behavior
- Missing data (`None`) is safely skipped.
- Missing values are NEVER coerced to `0.0`.
- Missing fields yield an `"Insufficient Data"` trend for that specific field.

## H. Explicit Architecture Boundary
Annual financial data is supplied by the Data Engineer. This Logic Engineer layer does NOT fetch, store, or persist annual financial data.

**NOTE:** Other CAGR variations, red flags, scoring, and integrations are explicitly excluded from this Tuesday-only scope.

## I. Financial Engine Integration (Thursday)
The `analyze_financial_health` function now accepts an optional `annual_records` parameter.
When omitted or empty, the engine operates in its legacy quarterly-only mode, and `annual` and `red_flags` are returned as `None`.
When supplied, the engine injects two new keys to the root output dictionary without breaking backward compatibility:
```python
{
    "symbol": "INFY",
    "status": "VALID",
    "overall_score": 75.0,  # Legacy quarterly score (unaffected by annual)
    # ... other existing quarterly fields ...

    "annual": { ... },       # Populated by analyze_annual_financials
    "red_flags": { ... }     # Populated by detect_red_flags
}
```
A failure in the annual component gracefully defaults both `annual` and `red_flags` to `None` and preserves the quarterly evaluation.
